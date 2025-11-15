"""Helpers for parsing LLM translation responses and identifying placeholders."""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple

_TRANSLATION_PREFIXES: Tuple[str, ...] = (
    "translation:",
    "translated:",
    "translated text:",
    "result:",
    "output:",
)
_TRANSLITERATION_PREFIXES: Tuple[str, ...] = (
    "transliteration:",
    "romanization:",
    "romanisation:",
    "pronunciation:",
)
_PLACEHOLDER_VALUES: Tuple[str, ...] = (
    "",
    "n/a",
    "n / a",
    "n.a",
    "n.a.",
    "not available",
    "not applicable",
    "translation unavailable",
    "no translation",
    "no translation provided",
    "no output",
    "none",
    "null",
    "-",
    "--",
)
_BLOCKED_PHRASES: Tuple[str, ...] = ("please provide the text",)


def _strip_known_prefix(value: str, prefixes: Sequence[str]) -> str:
    lowered = value.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return value[len(prefix) :].strip()
    return value.strip()


def _iter_response_lines(text: str) -> Iterable[str]:
    if not text:
        return []
    normalized = text.replace("\r\n", "\n").split("\n")
    return (line.strip() for line in normalized if line.strip())


def split_translation_and_transliteration(text: str) -> Tuple[str, str]:
    """Return the translation line plus any transliteration content."""

    translation_line = ""
    transliteration_parts = []
    for line in _iter_response_lines(text):
        if not translation_line:
            translation_line = _strip_known_prefix(line, _TRANSLATION_PREFIXES)
            continue
        transliteration_parts.append(_strip_known_prefix(line, _TRANSLITERATION_PREFIXES))
    transliteration_text = " ".join(part for part in transliteration_parts if part).strip()
    return translation_line.strip(), transliteration_text


def extract_primary_translation(text: str) -> str:
    """Return the first non-empty translation line."""

    translation, _ = split_translation_and_transliteration(text)
    return translation


def is_placeholder_value(text: str) -> bool:
    """Return True when ``text`` is effectively empty or a known placeholder."""

    candidate = text.strip().lower()
    if not candidate:
        return True
    return candidate in _PLACEHOLDER_VALUES


def is_placeholder_translation(text: str) -> bool:
    """Return True when the translation payload lacks useful content."""

    candidate = extract_primary_translation(text).strip().lower()
    if not candidate:
        return True
    if candidate in _PLACEHOLDER_VALUES:
        return True
    return any(blocked in candidate for blocked in _BLOCKED_PHRASES)


__all__ = [
    "extract_primary_translation",
    "is_placeholder_translation",
    "is_placeholder_value",
    "split_translation_and_transliteration",
]
