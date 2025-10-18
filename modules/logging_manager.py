"""Centralized logging configuration for ebook-tools."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

MODULE_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = MODULE_DIR.parent.resolve()
LOG_DIR = SCRIPT_DIR / "log"
LOG_FILE = LOG_DIR / "app.log"
DEFAULT_LOG_LEVEL = logging.INFO

_logger: Optional[logging.Logger] = None


def setup_logging(log_level: int = DEFAULT_LOG_LEVEL) -> logging.Logger:
    """Configure application-wide logging with a rotating file handler."""
    global _logger

    if _logger is not None:
        configure_logging_level(log_level=log_level)
        return _logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ebook_tools")
    logger.setLevel(log_level)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False

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


# Initialize logger on import to maintain existing behaviour
logger = get_logger()
