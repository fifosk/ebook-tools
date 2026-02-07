"""Helpers for reporting pipeline progress via the CLI."""

from __future__ import annotations

import functools
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import psutil

from .. import logging_manager as log_mgr
from ..progress_tracker import ProgressEvent, ProgressTracker

logger = log_mgr.get_logger()


def _format_duration(seconds: Optional[float]) -> str:
    """Return ``seconds`` formatted as ``HH:MM:SS``."""

    if seconds is None or seconds < 0:
        return "--:--:--"
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass(frozen=True)
class SystemMetricsSnapshot:
    """Aggregate of process level resource statistics."""

    cpu_percent: float
    memory_percent: float
    memory_rss: int
    read_rate: Optional[float]
    write_rate: Optional[float]
    timestamp: float


class SystemMetricsSampler:
    """Background sampler that periodically captures process metrics."""

    def __init__(self, *, interval: float = 10.0) -> None:
        self._interval = max(1.0, float(interval))
        self._process = psutil.Process()
        # Prime cpu_percent to avoid returning 0.0 on the first measurement.
        self._process.cpu_percent(None)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._metrics: Optional[SystemMetricsSnapshot] = None
        self._last_read: Optional[int] = None
        self._last_write: Optional[int] = None
        self._last_timestamp: float = time.time()
        self._thread = threading.Thread(
            target=self._run,
            name="SystemMetricsSampler",
            daemon=True,
        )
        # Capture an initial snapshot so early progress updates include metrics.
        self._capture_snapshot()
        self._thread.start()

    def close(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=self._interval)

    def snapshot(self) -> Optional[SystemMetricsSnapshot]:
        snapshot = self._metrics
        if snapshot is not None:
            return snapshot
        return self._capture_snapshot()

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._capture_snapshot()

    def _capture_snapshot(self) -> Optional[SystemMetricsSnapshot]:
        timestamp = time.time()
        try:
            cpu_percent = self._process.cpu_percent(None)
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
        except (psutil.Error, OSError):
            return None
        try:
            io_counters = self._process.io_counters()
        except (psutil.Error, OSError, AttributeError):
            io_counters = None

        read_rate: Optional[float] = None
        write_rate: Optional[float] = None

        with self._lock:
            if io_counters is not None:
                elapsed = max(timestamp - self._last_timestamp, 1e-3)
                if self._last_read is not None:
                    read_rate = max(
                        0.0, (io_counters.read_bytes - self._last_read) / elapsed
                    )
                if self._last_write is not None:
                    write_rate = max(
                        0.0, (io_counters.write_bytes - self._last_write) / elapsed
                    )
                self._last_read = io_counters.read_bytes
                self._last_write = io_counters.write_bytes
            self._last_timestamp = timestamp

            metrics = SystemMetricsSnapshot(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_rss=memory_info.rss,
                read_rate=read_rate,
                write_rate=write_rate,
                timestamp=timestamp,
            )
            self._metrics = metrics

        return metrics


class CLIProgressLogger:
    """Adapter that maps :class:`ProgressEvent` updates to CLI log output."""

    def __init__(
        self,
        tracker: ProgressTracker,
        *,
        logger_obj,
        metrics_sampler: Optional[SystemMetricsSampler] = None,
    ) -> None:
        self._tracker = tracker
        self._console_info = functools.partial(
            log_mgr.console_info, logger_obj=logger_obj
        )
        self._console_error = functools.partial(
            log_mgr.console_error, logger_obj=logger_obj
        )
        self._unsubscribe: Optional[Callable[[], None]] = tracker.register_observer(
            self._handle_event
        )
        self._last_log = 0.0
        self._progress_logged = False
        self._complete_logged = False
        self._metrics_sampler = metrics_sampler or SystemMetricsSampler()

    def close(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        if self._metrics_sampler is not None:
            self._metrics_sampler.close()
            self._metrics_sampler = None

    def _handle_event(self, event: ProgressEvent) -> None:
        metadata = dict(event.metadata)
        snapshot = event.snapshot
        total = snapshot.total

        if event.event_type == "start":
            message = metadata.get("message")
            if message:
                self._console_info(str(message))
            elif total:
                self._console_info("Tracking %s blocks...", total)
            else:
                self._console_info("Pipeline started.")
            return

        if event.event_type == "progress":
            if metadata.get("stage") == "translation":
                return
            if metadata.get("total_updated") and total:
                self._console_info("Updated total blocks to %s.", total)
                return
            if total is None or total == 0:
                return
            now = event.timestamp
            should_log = (
                not self._progress_logged
                or now - self._last_log >= self._tracker.report_interval
                or snapshot.completed >= total
            )
            if not should_log:
                return
            self._progress_logged = True
            self._last_log = now
            eta_str = _format_duration(snapshot.eta)
            elapsed_str = _format_duration(snapshot.elapsed)
            metrics = self._collect_metrics()
            if metrics is None:
                self._console_info(
                    "Progress: %s/%s blocks processed (%.2f blocks/s, ETA %s, Elapsed %s)",
                    snapshot.completed,
                    total,
                    snapshot.speed,
                    eta_str,
                    elapsed_str,
                )
            else:
                self._console_info(
                    (
                        "Progress: %s/%s blocks processed (%.2f blocks/s, ETA %s, Elapsed %s)"
                        " | CPU %.1f%% | Memory %s (%.1f%%) | IO %s/s read, %s/s write"
                    ),
                    snapshot.completed,
                    total,
                    snapshot.speed,
                    eta_str,
                    elapsed_str,
                    metrics.cpu_percent,
                    self._format_bytes(metrics.memory_rss),
                    metrics.memory_percent,
                    self._format_rate(metrics.read_rate),
                    self._format_rate(metrics.write_rate),
                )
            return

        if event.event_type == "complete":
            if self._complete_logged:
                return
            self._complete_logged = True
            forced = bool(metadata.get("forced"))
            reason = metadata.get("reason")
            if forced and reason:
                self._console_info("Pipeline finished early (%s).", reason)
            elif forced:
                self._console_info("Pipeline finished early.")
            else:
                self._console_info("Processing complete.")
            if total and total > 0:
                self._console_info(
                    "Final progress: %s/%s blocks processed in %s (avg %.2f blocks/s)",
                    snapshot.completed,
                    total,
                    _format_duration(snapshot.elapsed),
                    snapshot.speed,
                )
            return

        if event.event_type == "error":
            error_obj = event.error or metadata.get("message")
            if error_obj:
                self._console_error("Pipeline error reported: %s", error_obj)
            else:
                self._console_error("Pipeline error reported.")

    def _collect_metrics(self) -> Optional[SystemMetricsSnapshot]:
        if self._metrics_sampler is None:
            return None
        return self._metrics_sampler.snapshot()

    @staticmethod
    def _format_bytes(value: int) -> str:
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        size = float(value)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} {units[-1]}"

    @staticmethod
    def _format_rate(value: Optional[float]) -> str:
        if value is None:
            return "--"
        units = ["B", "KiB", "MiB", "GiB", "TiB"]
        rate = float(value)
        for unit in units:
            if rate < 1024.0 or unit == units[-1]:
                return f"{rate:.1f} {unit}"
            rate /= 1024.0
        return f"{rate:.1f} {units[-1]}"


__all__ = [
    "CLIProgressLogger",
    "SystemMetricsSampler",
    "SystemMetricsSnapshot",
]
