"""Text normalization helpers for subtitle processing."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Sequence

_WHITESPACE_PATTERN = re.compile(r"\s+")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_ASS_TAG_PATTERN = re.compile(r"\{[^}]*\}")
_ASS_INLINE_BREAKS = ("\\h", "\\N", "\\n")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value or "")
    normalized = html.unescape(normalized)
    normalized = _ASS_TAG_PATTERN.sub(" ", normalized)
    normalized = _HTML_TAG_PATTERN.sub(" ", normalized)
    for marker in _ASS_INLINE_BREAKS:
        normalized = normalized.replace(marker, " ")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip()


def _normalize_rendered_lines(lines: Sequence[str]) -> str:
    if not lines:
        return ""
    joined = "\n".join(lines)
    without_ass = _ASS_TAG_PATTERN.sub(" ", joined)
    without_html = _HTML_TAG_PATTERN.sub(" ", without_ass)
    normalized = html.unescape(without_html)
    for marker in _ASS_INLINE_BREAKS:
        normalized = normalized.replace(marker, " ")
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized.strip().casefold()


def _format_timecode_label(total_seconds: float) -> str:
    total = max(0, int(round(total_seconds)))
    minutes_total, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes_total, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes_total:02d}:{seconds:02d}"


__all__ = [
    "_ASS_TAG_PATTERN",
    "_HTML_TAG_PATTERN",
    "_WHITESPACE_PATTERN",
    "_format_timecode_label",
    "_normalize_rendered_lines",
    "_normalize_text",
]
