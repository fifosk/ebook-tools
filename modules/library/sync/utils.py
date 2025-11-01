"""Shared helpers for library synchronization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Mapping, Optional, Type

from conf.sync_config import SANITIZE_PATTERN

LibraryStatus = Literal["finished", "paused"]

def has_generated_media(payload: Mapping[str, Any]) -> bool:
    """Return True when ``payload`` describes at least one generated media file."""

    files_section = payload.get("files")
    if isinstance(files_section, list):
        for entry in files_section:
            if isinstance(entry, Mapping) and entry:
                return True
    elif isinstance(files_section, Mapping):
        for entry in files_section.values():
            if isinstance(entry, Mapping) and entry:
                return True
            if isinstance(entry, str) and entry.strip():
                return True

    chunks_section = payload.get("chunks")
    if isinstance(chunks_section, list):
        for chunk in chunks_section:
            if not isinstance(chunk, Mapping):
                continue
            if any(
                chunk.get(key)
                for key in ("chunk_id", "range_fragment")
            ) or any(
                chunk.get(key) is not None
                for key in ("start_sentence", "end_sentence")
            ):
                return True
            files = chunk.get("files")
            if isinstance(files, list):
                for entry in files:
                    if isinstance(entry, Mapping) and entry:
                        return True
            elif isinstance(files, Mapping):
                for entry in files.values():
                    if isinstance(entry, Mapping) and entry:
                        return True
                    if isinstance(entry, str) and entry.strip():
                        return True
    return False


def current_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(timezone.utc).isoformat()


def normalize_status(status: Any, *, error_cls: Type[Exception]) -> "LibraryStatus":
    """Normalize a status string to one of the supported library states."""

    candidate = str(status or "").strip().lower()
    if candidate in {"completed", "finished", "success"}:
        return "finished"
    if candidate == "paused":
        return "paused"
    raise error_cls(f"Unsupported library status '{status}'")


def compact_filters(filters: Dict[str, Optional[str]]) -> Dict[str, str]:
    """Return a copy of ``filters`` excluding falsy values."""

    return {key: value for key, value in filters.items() if value}


def sanitize_segment(value: Any, placeholder: str) -> str:
    """Normalize ``value`` for use in filenames and URLs."""

    token = str(value or "").strip()
    if not token:
        token = placeholder
    sanitized = SANITIZE_PATTERN.sub("_", token)
    sanitized = sanitized.strip("._ ")
    return sanitized or placeholder


def coerce_int(value: Any) -> Optional[int]:
    """Coerce ``value`` to an integer if possible."""

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number


def to_string(value: Any) -> Optional[str]:
    """Return a trimmed string or ``None`` for ``value``."""

    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if value is None:
        return None
    return str(value)


__all__ = [
    "LibraryStatus",
    "compact_filters",
    "coerce_int",
    "current_timestamp",
    "has_generated_media",
    "normalize_status",
    "sanitize_segment",
    "to_string",
]
