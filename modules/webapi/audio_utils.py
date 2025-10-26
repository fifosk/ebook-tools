"""Shared utilities for resolving audio synthesis settings."""

from __future__ import annotations

from typing import Any, Mapping

from modules.core.rendering.constants import LANGUAGE_CODES


def as_mapping(payload: Any) -> Mapping[str, Any]:
    """Return ``payload`` as a mapping when possible, otherwise an empty dict."""

    if isinstance(payload, Mapping):
        return payload
    return {}


def looks_like_lang_code(candidate: str) -> bool:
    """Return ``True`` when ``candidate`` resembles a language code."""

    stripped = candidate.strip()
    if not stripped:
        return False
    normalized = stripped.replace("-", "_")
    if len(normalized) > 16:
        return False
    return all(part.isalpha() for part in normalized.split("_"))


def resolve_language(requested: str | None, config: Mapping[str, Any]) -> str:
    """Resolve the language code used for synthesis based on ``config``."""

    if requested:
        return requested

    language_codes = {}
    raw_codes = as_mapping(config.get("language_codes"))
    if raw_codes:
        language_codes = {
            str(key): str(value)
            for key, value in raw_codes.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    preferred_language = config.get("input_language")
    if isinstance(preferred_language, str):
        stripped = preferred_language.strip()
        if stripped:
            code = language_codes.get(stripped)
            if code:
                return code
            mapped = LANGUAGE_CODES.get(stripped)
            if mapped:
                return mapped
            if looks_like_lang_code(stripped):
                return stripped

    return "en"


def resolve_voice(requested: str | None, config: Mapping[str, Any]) -> str:
    """Resolve the voice identifier for synthesis using ``config`` defaults."""

    if requested:
        return requested

    selected_voice = config.get("selected_voice")
    if isinstance(selected_voice, str) and selected_voice.strip():
        return selected_voice.strip()
    return "gTTS"


def resolve_speed(requested: int | None, config: Mapping[str, Any]) -> int:
    """Resolve the speaking speed (words per minute) for synthesis."""

    if requested is not None:
        return requested

    value = config.get("macos_reading_speed")
    try:
        speed = int(value)
    except (TypeError, ValueError):
        return 150
    return speed if speed > 0 else 150


__all__ = [
    "as_mapping",
    "looks_like_lang_code",
    "resolve_language",
    "resolve_speed",
    "resolve_voice",
]
