"""Small value-normalization helpers for acquisition discovery."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def string_sequence(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        normalized = string_value(value)
        return (normalized,) if normalized else ()
    if not isinstance(value, Sequence) or isinstance(value, bytes):
        return ()
    entries: list[str] = []
    for item in value:
        normalized = string_value(item)
        if normalized:
            entries.append(normalized)
    return tuple(entries)


def int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def safe_identifier(value: str) -> str:
    raw_value = value.strip()
    parsed = urlsplit(raw_value)
    if parsed.scheme and parsed.netloc:
        raw_value = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    sanitized = re.sub(r"[^A-Za-z0-9_.:-]+", "-", raw_value)
    return sanitized.strip("-")[:160] or "result"
