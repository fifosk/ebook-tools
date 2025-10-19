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
from typing import Callable, Optional

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


class _CLIProgressLogger:
    """Adapter that maps :class:`ProgressEvent` updates to CLI log output."""

    def __init__(self, tracker: ProgressTracker, *, logger_obj) -> None:
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

    def close(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

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
            self._console_info(
                "Progress: %s/%s blocks processed (%.2f blocks/s, ETA %s, Elapsed %s)",
                snapshot.completed,
                total,
                snapshot.speed,
                eta_str,
                elapsed_str,
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
