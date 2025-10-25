"""Unified orchestration helpers for CLI entry points."""

from __future__ import annotations

import io
import os
import select
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Sequence

try:  # pragma: no cover - dependency fallback for minimal environments
    from .. import config_manager
except ModuleNotFoundError:  # pragma: no cover - fallback when optional deps missing
    config_manager = None  # type: ignore[assignment]
from .. import logging_manager as log_mgr
from ..progress_tracker import ProgressTracker
from ..services.pipeline_service import PipelineResponse
from .args import parse_cli_args, parse_legacy_args
from .user_commands import SessionRequirementError, ensure_active_session, execute_user_command
from .pipeline_runner import run_pipeline_from_args
from .progress import CLIProgressLogger

logger = log_mgr.get_logger()


def _create_tracker(report_interval: float) -> ProgressTracker:
    return ProgressTracker(report_interval=report_interval)


def _start_shutdown_listener(
    *,
    tracker: ProgressTracker,
    stop_event: threading.Event,
) -> tuple[
    Optional[threading.Thread],
    threading.Event,
    threading.Event,
    Callable[[str], None],
]:
    shutdown_requested = threading.Event()
    acknowledge = threading.Event()

    def _request_shutdown(reason: str) -> None:
        if shutdown_requested.is_set():
            return
        shutdown_requested.set()
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
        stop_event.set()

    def _input_listener() -> None:
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

        while not stop_event.is_set():
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

        acknowledge.set()

    if hasattr(sys.stdin, "readline"):
        try:
            if sys.stdin.isatty():
                log_mgr.console_info(
                    "Press 'q' then Enter at any time to stop the pipeline gracefully.",
                    logger_obj=logger,
                )
        except Exception:
            pass
        listener = threading.Thread(
            target=_input_listener,
            name="ShutdownListener",
            daemon=True,
        )
        listener.start()
        return listener, shutdown_requested, acknowledge, _request_shutdown

    return None, shutdown_requested, acknowledge, _request_shutdown


def _cleanup_runtime_context() -> None:
    if config_manager is None:
        return
    try:
        context = config_manager.get_runtime_context(None)
        if context is not None:
            config_manager.cleanup_environment(context)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Failed to clean up temporary workspace: %s", exc)


def _run_pipeline(
    args,
    *,
    tracker: ProgressTracker,
    stop_event: threading.Event,
    progress_logger: CLIProgressLogger,
    request_shutdown: Callable[[str], None],
) -> Optional[PipelineResponse]:
    log_mgr.console_info(
        "Pipeline starting (CLI mode).",
        logger_obj=logger,
    )
    tracker.publish_start({"message": "Pipeline starting (CLI mode).", "source": "cli"})

    response: Optional[PipelineResponse]
    try:
        response = run_pipeline_from_args(
            args,
            progress_tracker=tracker,
            stop_event=stop_event,
        )
    except KeyboardInterrupt as exc:
        log_mgr.console_warning(
            "Pipeline interrupted by Ctrl+C; shutting down...",
            logger_obj=logger,
        )
        request_shutdown("Ctrl+C")
        tracker.record_error(exc, {"stage": "cli"})
        response = None
    finally:
        tracker.mark_finished(reason="CLI shutdown complete")
        progress_logger.close()
        _cleanup_runtime_context()

    return response


def run_cli(argv: Optional[Sequence[str]] = None, *, report_interval: float = 5.0) -> int:
    """Primary console script entry point."""

    args = parse_cli_args(argv)
    command = getattr(args, "command", "run") or "run"

    if command == "user":
        return execute_user_command(args)

    if command in {"run", "interactive"}:
        user_store_override = getattr(args, "user_store", None)
        session_file_override = getattr(args, "session_file", None)
        active_session_override = getattr(args, "active_session_file", None)
        try:
            ensure_active_session(
                user_store_path=Path(user_store_override).expanduser()
                if user_store_override
                else None,
                session_file=Path(session_file_override).expanduser()
                if session_file_override
                else None,
                active_session_path=Path(active_session_override).expanduser()
                if active_session_override
                else None,
            )
        except SessionRequirementError as exc:
            log_mgr.console_error(str(exc), logger_obj=logger)
            return 2

    tracker = _create_tracker(report_interval)
    stop_event = threading.Event()
    progress_logger = CLIProgressLogger(tracker, logger_obj=logger)
    listener, shutdown_requested, acknowledge, request_shutdown = _start_shutdown_listener(
        tracker=tracker, stop_event=stop_event
    )

    try:
        response = _run_pipeline(
            args,
            tracker=tracker,
            stop_event=stop_event,
            progress_logger=progress_logger,
            request_shutdown=request_shutdown,
        )
    finally:
        stop_event.set()
        if listener is not None:
            acknowledge.wait(timeout=1.0)
            listener.join(timeout=1.0)
        tracker.close()

    if command == "run" and response is None and not shutdown_requested.is_set():
        return 1
    return 0


def run_legacy_pipeline(
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
    report_interval: float = 5.0,
) -> Optional[PipelineResponse]:
    """Retain backwards compatible behaviour for ``modules.ebook_tools``."""

    args = parse_legacy_args()
    tracker = progress_tracker or _create_tracker(report_interval)
    owns_tracker = progress_tracker is None
    event = stop_event or threading.Event()
    progress_logger = CLIProgressLogger(tracker, logger_obj=logger)

    listener, _, acknowledge, request_shutdown = _start_shutdown_listener(
        tracker=tracker, stop_event=event
    )

    try:
        response = _run_pipeline(
            args,
            tracker=tracker,
            stop_event=event,
            progress_logger=progress_logger,
            request_shutdown=request_shutdown,
        )
    finally:
        event.set()
        if listener is not None:
            acknowledge.wait(timeout=1.0)
            listener.join(timeout=1.0)
        if owns_tracker:
            tracker.close()

    return response


__all__ = ["run_cli", "run_legacy_pipeline"]
