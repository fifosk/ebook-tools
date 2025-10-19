#!/usr/bin/env python3
"""Lightweight entry point for the ebook tools pipeline."""

from __future__ import annotations

import io
import os
import select
import sys
import threading
import time
from typing import Optional

from modules import config_manager
from modules import logging_manager as log_mgr
from modules.adapters.cli.menu import run_pipeline as _run_pipeline
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
    def _request_shutdown(reason: str) -> None:
        """Signal that the pipeline should stop and log the triggering reason."""

        if not pipeline_stop.is_set():
            logger.info("Shutdown requested via %s; stopping pipeline...", reason)
        pipeline_stop.set()

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

    input_thread: Optional[threading.Thread] = None

    def _input_listener() -> None:
        """Watch stdin for a 'q' command to trigger shutdown."""

        try:
            stdin = sys.stdin
        except Exception:  # pragma: no cover - defensive guard
            return

        if stdin is None:
            return

        # ``isatty`` may be unavailable (e.g. when running under some IDEs).
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
                logger.info("Press 'q' then Enter at any time to stop the pipeline gracefully.")
        except Exception:
            pass
        input_thread = threading.Thread(
            target=_input_listener,
            name="ShutdownListener",
            daemon=True,
        )
        input_thread.start()

    try:
        result = _run_pipeline(progress_tracker=tracker, stop_event=pipeline_stop)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by Ctrl+C; shutting down...")
        _request_shutdown("Ctrl+C")
        result = None
    finally:
        tracker.mark_finished()
        monitor_stop.set()
        monitor_thread.join(timeout=1.0)
        if input_thread is not None:
            pipeline_stop.set()
            input_thread.join(timeout=1.0)
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
        try:
            config_manager.cleanup_environment()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to clean up temporary workspace: %s", exc)

    return result


if __name__ == "__main__":
    run_pipeline()
