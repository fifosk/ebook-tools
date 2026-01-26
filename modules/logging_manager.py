"""Centralized logging configuration for ebook-tools."""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Iterator, Optional

MODULE_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = MODULE_DIR.parent.resolve()
LOG_DIR = SCRIPT_DIR / "log"
LOG_FILE = LOG_DIR / "app.log"
DEFAULT_LOG_LEVEL = logging.INFO

_logger: Optional[logging.Logger] = None
_log_context: contextvars.ContextVar[Dict[str, object]] = contextvars.ContextVar(
    "ebook_tools_log_context", default={}
)


class JSONLogFormatter(logging.Formatter):
    """Render log records as structured JSON strings."""

    DEFAULT_FIELDS: tuple[str, ...] = (
        "correlation_id",
        "job_id",
        "event",
        "stage",
        "duration_ms",
        "status",
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        message = record.getMessage()
        payload: Dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "pid": record.process,
            "thread": record.threadName,
        }

        for attr in self.DEFAULT_FIELDS:
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value

        extra_attributes = _extract_extra_attributes(record)
        if extra_attributes:
            payload["extra"] = extra_attributes

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def _extract_extra_attributes(record: logging.LogRecord) -> Dict[str, object]:
    reserved: set[str] = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
    }
    extra: Dict[str, object] = {}
    for key, value in record.__dict__.items():
        if key in reserved or key in JSONLogFormatter.DEFAULT_FIELDS:
            continue
        extra[key] = value
    return extra


class LogContextFilter(logging.Filter):
    """Inject values from context variables into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        context = _log_context.get()
        for key, value in context.items():
            setattr(record, key, value)
        return True


class ConsoleSuppressionFilter(logging.Filter):
    """Prevent selected log records from being emitted to the console."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        return not getattr(record, "console_suppress", False)


# Global flag for quiet mode - suppresses INFO console output
_console_quiet_mode: bool = False


class ConsoleQuietFilter(logging.Filter):
    """In quiet mode, only allow WARNING and above to console."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        if not _console_quiet_mode:
            return True
        # In quiet mode, suppress INFO and DEBUG unless marked as important
        if record.levelno >= logging.WARNING:
            return True
        # Allow records explicitly marked as console_important
        return getattr(record, "console_important", False)


def set_console_quiet_mode(enabled: bool) -> None:
    """Enable or disable quiet mode for console output.

    When enabled, INFO and DEBUG level messages are suppressed from console
    (but still written to log files). Warnings and errors are always shown.
    """
    global _console_quiet_mode
    _console_quiet_mode = enabled


def is_console_quiet_mode() -> bool:
    """Return whether quiet mode is currently enabled."""
    return _console_quiet_mode


def _configure_handlers(logger: logging.Logger) -> None:
    formatter = JSONLogFormatter()

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(ConsoleSuppressionFilter())
    stream_handler.addFilter(ConsoleQuietFilter())

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def setup_logging(log_level: int = DEFAULT_LOG_LEVEL) -> logging.Logger:
    """Configure application-wide logging with a rotating file handler."""
    global _logger

    if _logger is not None:
        configure_logging_level(log_level=log_level)
        return _logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ebook_tools")
    logger.setLevel(log_level)
    logger.propagate = False
    logger.addFilter(LogContextFilter())
    _configure_handlers(logger)

    _logger = logger
    configure_logging_level(log_level=log_level)
    return logger


def get_logger() -> logging.Logger:
    """Return the configured logger instance, initializing if necessary."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def configure_logging_level(debug_enabled: bool = False, log_level: Optional[int] = None) -> int:
    """Adjust the global logger level based on debug preference or explicit level."""
    logger = get_logger()
    if log_level is not None:
        level = log_level
    else:
        level = logging.DEBUG if debug_enabled else DEFAULT_LOG_LEVEL
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
    return level


def get_log_context() -> Dict[str, object]:
    """Return the active structured logging context."""

    return dict(_log_context.get())


def push_log_context(**values: object) -> contextvars.Token[Dict[str, object]]:
    """Merge ``values`` into the structured logging context and return a token."""

    current = dict(_log_context.get())
    for key, value in list(values.items()):
        if value is None:
            values.pop(key, None)
    current.update(values)
    return _log_context.set(current)


def pop_log_context(token: contextvars.Token[Dict[str, object]]) -> None:
    """Restore the logging context from ``token``."""

    _log_context.reset(token)


@contextlib.contextmanager
def log_context(**values: object) -> Iterator[None]:
    """Context manager that temporarily enriches log context with ``values``."""

    token = push_log_context(**values)
    try:
        yield
    finally:
        pop_log_context(token)


def clear_log_context() -> None:
    """Clear all structured logging context values."""

    _log_context.set({})


def ensure_correlation_context(*, correlation_id: Optional[str], job_id: Optional[str] = None) -> None:
    """Populate correlation and job identifiers when not already present."""

    context = _log_context.get()
    updates: Dict[str, object] = {}
    if "correlation_id" not in context and correlation_id is not None:
        updates["correlation_id"] = correlation_id
    if "job_id" not in context and job_id is not None:
        updates["job_id"] = job_id
    if updates:
        push_log_context(**updates)


def _format_console_message(message: object, args: tuple[object, ...]) -> str:
    if not args:
        return str(message)
    try:
        return str(message) % args
    except Exception:
        return " ".join([str(message), *map(str, args)])


def console_log(
    level: int,
    message: object,
    *args: object,
    logger_obj: Optional[logging.Logger] = None,
    stderr: bool = False,
    **kwargs: object,
) -> None:
    """Log ``message`` while emitting a plain-text console echo."""

    logger_instance = logger_obj or get_logger()
    formatted = _format_console_message(message, args)
    with log_context(console_suppress=True):
        logger_instance.log(level, message, *args, **kwargs)
    stream = sys.stderr if stderr else sys.stdout
    print(formatted, file=stream, flush=True)


def console_info(
    message: object,
    *args: object,
    logger_obj: Optional[logging.Logger] = None,
    **kwargs: object,
) -> None:
    """Emit an ``INFO`` log record while printing to the console."""

    console_log(logging.INFO, message, *args, logger_obj=logger_obj, **kwargs)


def console_warning(
    message: object,
    *args: object,
    logger_obj: Optional[logging.Logger] = None,
    **kwargs: object,
) -> None:
    """Emit a ``WARNING`` log record while printing to the console."""

    console_log(logging.WARNING, message, *args, logger_obj=logger_obj, **kwargs)


def console_error(
    message: object,
    *args: object,
    logger_obj: Optional[logging.Logger] = None,
    **kwargs: object,
) -> None:
    """Emit an ``ERROR`` log record while printing to the console."""

    console_log(
        logging.ERROR,
        message,
        *args,
        logger_obj=logger_obj,
        stderr=True,
        **kwargs,
    )


# Initialize logger on import to maintain existing behaviour
logger = get_logger()
