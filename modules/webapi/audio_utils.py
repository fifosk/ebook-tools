"""Shared utilities for resolving audio synthesis settings."""

from __future__ import annotations

from typing import Any, Mapping

from modules.language_constants import LANGUAGE_CODES

_LANGUAGE_CODE_ALIASES: dict[str, str] = {
    "amh": "am",
    "ara": "ar",
    "ben": "bn",
    "bos": "bs",
    "bul": "bg",
    "ces": "cs",
    "chi": "zh-cn",
    "chs": "zh-cn",
    "cht": "zh-tw",
    "cmn": "zh-cn",
    "cze": "cs",
    "dan": "da",
    "deu": "de",
    "dut": "nl",
    "ell": "el",
    "eng": "en",
    "est": "et",
    "fas": "fa",
    "fin": "fi",
    "fre": "fr",
    "fra": "fr",
    "ger": "de",
    "gre": "el",
    "heb": "he",
    "hin": "hi",
    "hrv": "hr",
    "hun": "hu",
    "ind": "id",
    "ita": "it",
    "jpn": "ja",
    "kor": "ko",
    "lav": "lv",
    "lit": "lt",
    "may": "ms",
    "msa": "ms",
    "nor": "no",
    "pes": "fa",
    "per": "fa",
    "pol": "pl",
    "por": "pt",
    "por-br": "pt-br",
    "ptbr": "pt-br",
    "pus": "ps",
    "ron": "ro",
    "rum": "ro",
    "rus": "ru",
    "slo": "sk",
    "slk": "sk",
    "slv": "sl",
    "spa": "es",
    "srp": "sr",
    "swe": "sv",
    "tam": "ta",
    "tel": "te",
    "tha": "th",
    "tur": "tr",
    "ukr": "uk",
    "vie": "vi",
    "zho": "zh-cn",
}


def normalize_language_code(candidate: str) -> str:
    """Return a normalized language code, applying common ISO-639 aliases."""

    trimmed = (candidate or "").strip()
    if not trimmed:
        return ""
    normalized = trimmed.lower().replace("_", "-")
    mapped = _LANGUAGE_CODE_ALIASES.get(normalized)
    return mapped or normalized


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
        mapped = LANGUAGE_CODES.get(requested.strip()) if isinstance(requested, str) else None
        if mapped:
            return normalize_language_code(mapped)
        if isinstance(requested, str) and looks_like_lang_code(requested):
            return normalize_language_code(requested)
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
                    return normalize_language_code(code)
                mapped = LANGUAGE_CODES.get(stripped)
                if mapped:
                    return normalize_language_code(mapped)
                if looks_like_lang_code(stripped):
                    return normalize_language_code(stripped)

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
