"""Helpers for parsing LLM translation responses and identifying placeholders."""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple

import regex

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

_LATIN_PATTERN = regex.compile(r"\p{Latin}")
_NON_LATIN_LETTER_PATTERN = regex.compile(r"(?!\p{Latin})\p{L}")
_INLINE_TRANSLIT_SPLIT = regex.compile(r"\s+(\p{Latin})")


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

    def _is_latin_heavy(value: str) -> bool:
        latin_count = len(_LATIN_PATTERN.findall(value))
        non_latin_count = len(_NON_LATIN_LETTER_PATTERN.findall(value))
        return latin_count > 0 and latin_count >= non_latin_count

    def _split_inline_transliteration(value: str) -> Tuple[str, str]:
        """
        Heuristic: split a single-line response that contains both non-Latin
        translation text and a trailing Latin transliteration.
        """

        match = _INLINE_TRANSLIT_SPLIT.search(value)
        if not match:
            return value, ""
        split_index = match.start(1)
        left = value[:split_index].rstrip(" ,;:、。.!?")
        right = value[split_index:].strip()
        if not left or not right:
            return value, ""
        if (
            _NON_LATIN_LETTER_PATTERN.search(left)
            and _LATIN_PATTERN.search(right)
            and _is_latin_heavy(right)
        ):
            return left.strip(), right
        return value, ""

    raw_lines = list(_iter_response_lines(text))
    if not raw_lines:
        return "", ""

    translation_parts = []
    transliteration_parts = []

    for idx, raw_line in enumerate(raw_lines):
        cleaned_line = _strip_known_prefix(raw_line, _TRANSLATION_PREFIXES if idx == 0 else _TRANSLITERATION_PREFIXES)
        if idx == 0:
            translation_parts.append(cleaned_line)
            continue
        if _is_latin_heavy(cleaned_line):
            transliteration_parts.append(_strip_known_prefix(cleaned_line, _TRANSLITERATION_PREFIXES))
        else:
            translation_parts.append(cleaned_line)

    translation_text = " ".join(part for part in translation_parts if part).strip()
    transliteration_text = " ".join(part for part in transliteration_parts if part).strip()
    if not transliteration_text:
        translation_text, transliteration_text = _split_inline_transliteration(translation_text)
    return translation_text, transliteration_text


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
