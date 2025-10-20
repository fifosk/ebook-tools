"""Utilities for resolving configuration and runtime file system paths."""
from __future__ import annotations

import errno
import os
import shutil
from pathlib import Path
from typing import Optional

from modules import logging_manager

from .constants import SCRIPT_DIR

logger = logging_manager.get_logger()


def _cleanup_directory_path(path: Path) -> None:
    """Remove broken symlinks or non-directories along ``path`` and its parents."""

    for candidate in (path, *path.parents):
        if candidate == candidate.parent:
            break

        try:
            if candidate.is_symlink():
                if candidate.exists():
                    continue
                candidate.unlink()
                continue

            if candidate.exists() and not candidate.is_dir():
                if candidate.is_file() or candidate.is_symlink():
                    candidate.unlink()
                else:
                    shutil.rmtree(candidate)
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.debug("Unable to prepare path %s: %s", candidate, exc)


def resolve_directory(path_value, default_relative: Path) -> Path:
    """Resolve a directory path relative to the script directory and ensure it exists."""

    def _normalize(candidate: Path) -> Path:
        expanded = Path(os.path.expanduser(str(candidate)))
        if expanded.is_absolute():
            return expanded
        return SCRIPT_DIR / expanded

    base_value = path_value if path_value not in [None, ""] else default_relative
    base_path = _normalize(Path(base_value))
    fallback_path = _normalize(default_relative)

    attempts = []
    seen = set()

    for candidate in (base_path, fallback_path):
        if candidate not in seen:
            attempts.append(candidate)
            seen.add(candidate)

    last_error: Optional[Exception] = None

    for index, attempt in enumerate(attempts):
        _cleanup_directory_path(attempt)

        try:
            attempt.mkdir(parents=True, exist_ok=True)
            return attempt
        except PermissionError as exc:
            last_error = exc
        except OSError as exc:
            last_error = exc
            if attempt.exists() and attempt.is_dir():
                return attempt
            if getattr(exc, "errno", None) not in {errno.EPERM, errno.EACCES, errno.EROFS}:
                raise

        if index < len(attempts) - 1:
            logger.warning(
                "Unable to prepare directory %s (%s); falling back to %s",
                attempt,
                last_error,
                attempts[index + 1],
            )

    if last_error:
        raise last_error

    return attempts[-1]


def resolve_file_path(path_value, base_dir=None) -> Optional[Path]:
    """Resolve a potentially relative file path relative to a base directory."""

    if not path_value:
        return None
    file_path = Path(os.path.expanduser(str(path_value)))
    if file_path.is_absolute():
        return file_path
    if base_dir:
        base = Path(base_dir)
        if file_path.parts and base.name == file_path.parts[0]:
            file_path = (SCRIPT_DIR / file_path).resolve()
        else:
            file_path = (base / file_path).resolve()
    else:
        file_path = (SCRIPT_DIR / file_path).resolve()
    return file_path


__all__ = ["resolve_directory", "resolve_file_path"]
