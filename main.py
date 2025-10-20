#!/usr/bin/env python3
"""Lightweight entry point for the ebook tools pipeline."""

from __future__ import annotations

import functools
import io
import os
import select
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import psutil

from modules import config_manager
from modules import logging_manager as log_mgr
from modules.ebook_tools import run_pipeline as _run_pipeline
from modules.services.pipeline_service import PipelineResponse
from modules.progress_tracker import ProgressEvent, ProgressTracker

logger = log_mgr.get_logger()

__all__ = ["run_pipeline"]


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


class _SystemMetricsSampler:
    """Background sampler that periodically captures process metrics."""

    def __init__(self, *, interval: float = 10.0) -> None:
        self._interval = max(1.0, float(interval))
        self._process = psutil.Process(os.getpid())
        # Prime cpu_percent to avoid returning 0.0 on the first measurement.
        self._process.cpu_percent(None)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._metrics: Optional[SystemMetricsSnapshot] = None
        self._thread = threading.Thread(
            target=self._run,
            name="SystemMetricsSampler",
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=self._interval)

    def snapshot(self) -> Optional[SystemMetricsSnapshot]:
        with self._lock:
            return self._metrics

    def _run(self) -> None:
        last_read: Optional[int] = None
        last_write: Optional[int] = None
        last_timestamp = time.time()
        while not self._stop_event.wait(self._interval):
            timestamp = time.time()
            try:
                cpu_percent = self._process.cpu_percent(None)
                memory_info = self._process.memory_info()
                memory_percent = self._process.memory_percent()
                io_counters = self._process.io_counters()
            except (psutil.Error, OSError, AttributeError):
                continue

            read_rate: Optional[float] = None
            write_rate: Optional[float] = None
            if io_counters is not None:
                elapsed = max(timestamp - last_timestamp, 1e-3)
                if last_read is not None:
                    read_rate = max(
                        0.0, (io_counters.read_bytes - last_read) / elapsed
                    )
                if last_write is not None:
                    write_rate = max(
                        0.0, (io_counters.write_bytes - last_write) / elapsed
                    )
                last_read = io_counters.read_bytes
                last_write = io_counters.write_bytes
                last_timestamp = timestamp

            metrics = SystemMetricsSnapshot(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_rss=memory_info.rss,
                read_rate=read_rate,
                write_rate=write_rate,
                timestamp=timestamp,
            )
            with self._lock:
                self._metrics = metrics


class _CLIProgressLogger:
    """Adapter that maps :class:`ProgressEvent` updates to CLI log output."""

    def __init__(
        self,
        tracker: ProgressTracker,
        *,
        logger_obj,
        metrics_sampler: Optional[_SystemMetricsSampler] = None,
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
        self._metrics_sampler = metrics_sampler or _SystemMetricsSampler()

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


def run_pipeline(report_interval: float = 5.0) -> Optional[PipelineResponse]:
    """Execute the ebook processing pipeline with live progress reporting."""

    tracker = ProgressTracker(report_interval=report_interval)
    pipeline_stop = threading.Event()
    progress_logger = _CLIProgressLogger(tracker, logger_obj=logger)

    def _request_shutdown(reason: str) -> None:
        """Signal that the pipeline should stop and log the triggering reason."""

        if not pipeline_stop.is_set():
            log_mgr.console_info(
                "Shutdown requested via %s; stopping pipeline...",
                reason,
                logger_obj=logger,
            )
            tracker.publish_progress(
                {
                    "stage": "shutdown",
                    "message": f"Shutdown requested via {reason}",
                }
            )
        pipeline_stop.set()

    input_thread: Optional[threading.Thread] = None

    def _input_listener() -> None:
        """Watch stdin for a 'q' command to trigger shutdown."""

        try:
            stdin = sys.stdin
        except Exception:  # pragma: no cover - defensive guard
            return

        if stdin is None:
            return

        try:
            interactive = stdin.isatty()
        except Exception:
            interactive = False

        if not interactive:
            return

        try:
            fileno = stdin.fileno()
        except (AttributeError, io.UnsupportedOperation):
            fileno = None

        while not pipeline_stop.is_set():
            if os.environ.get("EBOOK_MENU_ACTIVE") == "1":
                time.sleep(0.1)
                continue

            if fileno is not None:
                try:
                    ready, _, _ = select.select([stdin], [], [], 0.1)
                except (OSError, ValueError):
                    fileno = None
                    continue
                if not ready:
                    continue
                if os.environ.get("EBOOK_MENU_ACTIVE") == "1":
                    continue

            try:
                line = stdin.readline()
            except (EOFError, io.UnsupportedOperation):
                break
            except Exception:  # pragma: no cover - defensive guard
                break
            if not line:
                break
            if line.strip().lower() == "q":
                _request_shutdown("'q' command")
                break

    if hasattr(sys.stdin, "readline"):
        try:
            if sys.stdin.isatty():
                log_mgr.console_info(
                    "Press 'q' then Enter at any time to stop the pipeline gracefully.",
                    logger_obj=logger,
                )
        except Exception:
            pass
        input_thread = threading.Thread(
            target=_input_listener,
            name="ShutdownListener",
            daemon=True,
        )
        input_thread.start()

    log_mgr.console_info(
        "Pipeline starting (CLI mode).",
        logger_obj=logger,
    )
    tracker.publish_start({"message": "Pipeline starting (CLI mode).", "source": "cli"})

    try:
        response = _run_pipeline(progress_tracker=tracker, stop_event=pipeline_stop)
    except KeyboardInterrupt as exc:
        log_mgr.console_warning(
            "Pipeline interrupted by Ctrl+C; shutting down...",
            logger_obj=logger,
        )
        _request_shutdown("Ctrl+C")
        tracker.record_error(exc, {"stage": "cli"})
        response = None
    finally:
        tracker.mark_finished(reason="CLI shutdown complete")
        if input_thread is not None:
            pipeline_stop.set()
            input_thread.join(timeout=1.0)
        progress_logger.close()
        try:
            context = config_manager.get_runtime_context(None)
            if context is not None:
                config_manager.cleanup_environment(context)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to clean up temporary workspace: %s", exc)

    return response


if __name__ == "__main__":
    run_pipeline()
