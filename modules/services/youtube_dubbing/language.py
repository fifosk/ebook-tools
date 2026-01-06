from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional

from modules import language_policies
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.subtitles.language import _target_uses_non_latin_script
from modules.llm_client import create_client
from modules.transliteration import TransliterationService

from .common import _LANGUAGE_TOKEN_PATTERN, logger

_RTL_SCRIPT_PATTERN = re.compile(r"[\u0590-\u08FF]")
_RTL_LANGUAGE_HINTS = {
    "arabic",
    "ar",
    "farsi",
    "fa",
    "hebrew",
    "he",
    "iw",
    "persian",
    "ps",
    "pashto",
    "ur",
    "urdu",
}


def _language_uses_non_latin(label: Optional[str]) -> bool:
    """Return True when the language hint expects non-Latin script output."""

    normalized = (label or "").strip()
    if not normalized:
        return False
    if language_policies.is_non_latin_language_hint(normalized):
        return True
    return _target_uses_non_latin_script(normalized)


def _is_rtl_language(label: Optional[str]) -> bool:
    """Return True when the provided language label hints at an RTL script."""

    normalized = (label or "").strip().lower().replace("_", "-")
    if not normalized:
        return False
    if normalized in _RTL_LANGUAGE_HINTS:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized) if token]
    return any(token in _RTL_LANGUAGE_HINTS for token in tokens)


def _normalize_rtl_word_order(text: str, language: Optional[str], *, force: bool = False) -> str:
    """
    Return ``text`` with RTL words ordered left-to-right for display while
    preserving in-word character order.
    """

    if not text or not _is_rtl_language(language):
        return text
    if not force and not _RTL_SCRIPT_PATTERN.search(text):
        return text
    tokens = [segment for segment in text.split() if segment]
    if len(tokens) <= 1:
        return text
    return " ".join(reversed(tokens))


def _transliterate_text(
    transliterator: TransliterationService,
    text: str,
    language: str,
    *,
    transliteration_mode: Optional[str] = None,
    llm_model: Optional[str] = None,
) -> str:
    """Return plain transliteration text from the service result."""

    resolved_mode = (transliteration_mode or "").strip().lower().replace("_", "-")
    python_only = resolved_mode in {"python", "python-module", "module", "local-module"}
    if llm_model and not python_only:
        with create_client(model=llm_model) as client:
            result = transliterator.transliterate(
                text,
                language,
                client=client,
                mode=transliteration_mode,
            )
    else:
        result = transliterator.transliterate(
            text,
            language,
            mode=transliteration_mode,
        )
    if hasattr(result, "text"):
        try:
            return str(getattr(result, "text") or "")
        except Exception:
            return ""
    if isinstance(result, str):
        return result
    return ""


def _normalize_language_hint(raw: Optional[str]) -> Optional[str]:
    """Return a sanitized language tag suitable for filenames."""

    if not raw:
        return None
    token = raw.strip().replace(" ", "-").lower()
    token = re.sub(r"[^a-z0-9_-]+", "", token)
    if not token:
        return None
    if len(token) > 16:
        token = token[:16]
    return token


def _find_language_token(path: Path) -> Optional[str]:
    stem_parts = path.stem.split(".")
    if len(stem_parts) < 2:
        return None
    candidate = stem_parts[-1].strip()
    if not candidate:
        return None
    if _LANGUAGE_TOKEN_PATTERN.match(candidate):
        return candidate
    return None


def _resolve_language_code(label: Optional[str]) -> str:
    if not label:
        return "en"
    normalized = label.strip()
    if not normalized:
        return "en"
    for name, code in LANGUAGE_CODES.items():
        if normalized.casefold() == name.casefold():
            return code
    return normalized


def _normalize_to_display(text: str) -> str:
    try:
        return unicodedata.normalize("NFKC", text)
    except Exception:
        return text


__all__ = [
    "_RTL_LANGUAGE_HINTS",
    "_RTL_SCRIPT_PATTERN",
    "_find_language_token",
    "_is_rtl_language",
    "_language_uses_non_latin",
    "_normalize_language_hint",
    "_normalize_rtl_word_order",
    "_normalize_to_display",
    "_resolve_language_code",
    "_transliterate_text",
    "logger",
]
