#!/usr/bin/env python3
"""Lightweight entry point for the ebook tools pipeline."""

from __future__ import annotations

import threading
from typing import Optional

from modules import logging_manager as log_mgr
from modules.ebook_tools import run_pipeline as _run_pipeline
from modules.progress_tracker import ProgressTracker

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


def run_pipeline(report_interval: float = 5.0):
    """Execute the ebook processing pipeline with live progress reporting."""

    tracker = ProgressTracker(report_interval=report_interval)
    monitor_stop = threading.Event()
    pipeline_stop = threading.Event()

    def _monitor() -> None:
        while not monitor_stop.wait(tracker.report_interval):
            snapshot = tracker.snapshot()
            total = snapshot.total
            if tracker.is_complete() and (total is None or total == 0):
                break
            if total is None or total == 0:
                continue
            eta_str = _format_duration(snapshot.eta)
            elapsed_str = _format_duration(snapshot.elapsed)
            logger.info(
                "Progress: %s/%s blocks processed (%.2f blocks/s, ETA %s, Elapsed %s)",
                snapshot.completed,
                total,
                snapshot.speed,
                eta_str,
                elapsed_str,
            )
            if tracker.is_complete():
                break

    monitor_thread = threading.Thread(target=_monitor, name="ProgressMonitor", daemon=True)
    monitor_thread.start()

    try:
        result = _run_pipeline(progress_tracker=tracker, stop_event=pipeline_stop)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user request. Cleaning up...")
        pipeline_stop.set()
        result = None
    finally:
        tracker.mark_finished()
        monitor_stop.set()
        monitor_thread.join(timeout=1.0)
        final_snapshot = tracker.snapshot()
        total = final_snapshot.total
        if total is not None and total > 0:
            logger.info(
                "Final progress: %s/%s blocks processed in %s (avg %.2f blocks/s)",
                final_snapshot.completed,
                total,
                _format_duration(final_snapshot.elapsed),
                final_snapshot.speed,
            )

    return result


if __name__ == "__main__":
    run_pipeline()
