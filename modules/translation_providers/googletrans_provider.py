"""Google Translate provider implementation.

This module handles all Google Translate-specific functionality including:
- Health checking for googletrans library
- Language code resolution and normalization
- Translation execution with retry logic
"""

from __future__ import annotations

import threading
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker

from modules import logging_manager as log_mgr, text_normalization as text_norm
from modules.language_constants import LANGUAGE_CODES
from modules.retry_annotations import format_retry_failure
import regex

logger = log_mgr.logger

# Constants
_TRANSLATION_RESPONSE_ATTEMPTS = 5
_TRANSLATION_RETRY_DELAY_SECONDS = 1.0

_GOOGLETRANS_PROVIDER_ALIASES = {
    "google",
    "googletrans",
    "googletranslate",
    "google-translate",
    "gtranslate",
    "gtrans",
}

_GOOGLETRANS_PSEUDO_SUFFIXES = {
    "orig",
    "original",
    "auto",
    "autogen",
    "auto-generated",
    "generated",
}

_LANG_CODE_PATTERN = regex.compile(r"^[a-z]{2,3}([_-][a-z0-9]{2,4})?$", regex.IGNORECASE)

# Thread-local storage for translator instances
_GOOGLETRANS_LOCAL = threading.local()

# Health check state (shared across threads)
_GOOGLETRANS_HEALTH_LOCK = threading.Lock()
_GOOGLETRANS_HEALTH_STATE = {
    "checked": False,
    "ok": False,
    "reason": None,
}


def check_googletrans_health() -> tuple[bool, Optional[str]]:
    """Check if googletrans library is available and functional.

    Returns:
        Tuple of (is_healthy, error_reason)
    """
    with _GOOGLETRANS_HEALTH_LOCK:
        if _GOOGLETRANS_HEALTH_STATE["checked"]:
            return _GOOGLETRANS_HEALTH_STATE["ok"], _GOOGLETRANS_HEALTH_STATE["reason"]

        reason: Optional[str] = None
        try:
            import httpcore  # noqa: F401
        except Exception as exc:
            reason = f"httpcore import failed: {exc}"
        else:
            if not hasattr(httpcore, "SyncHTTPTransport"):
                reason = "httpcore.SyncHTTPTransport missing"

        if reason is None:
            try:
                from googletrans import Translator

                Translator()
            except Exception as exc:
                reason = f"googletrans init failed: {exc}"

        ok = reason is None
        _GOOGLETRANS_HEALTH_STATE["checked"] = True
        _GOOGLETRANS_HEALTH_STATE["ok"] = ok
        _GOOGLETRANS_HEALTH_STATE["reason"] = reason
        if not ok:
            logger.warning("Googletrans health check failed: %s", reason)
        return ok, reason


def normalize_translation_provider(value: Optional[str]) -> str:
    """Normalize translation provider name to canonical form.

    Args:
        value: Provider name (e.g., "google", "googletrans", "llm")

    Returns:
        Normalized provider name: "googletrans" or "llm"
    """
    if not value:
        return "llm"
    normalized = value.strip().lower()
    if normalized in _GOOGLETRANS_PROVIDER_ALIASES:
        return "googletrans"
    if normalized in {"llm", "ollama", "default"}:
        return "llm"
    return "llm"


def _strip_googletrans_pseudo_suffix(value: str) -> str:
    """Strip pseudo suffixes like '-orig', '-auto' from language codes."""
    if "-" not in value:
        return value
    parts = value.split("-")
    if parts[-1] in _GOOGLETRANS_PSEUDO_SUFFIXES:
        return "-".join(parts[:-1])
    return value


def resolve_googletrans_language(
    value: Optional[str], *, fallback: Optional[str]
) -> Optional[str]:
    """Resolve language code/name to googletrans-compatible code.

    Handles language code normalization, pseudo-suffix stripping, and
    language name to code conversion.

    Args:
        value: Language code or name
        fallback: Fallback value if resolution fails

    Returns:
        Googletrans language code or fallback
    """
    if value is None:
        return fallback
    cleaned = value.strip()
    if not cleaned:
        return fallback
    normalized = cleaned.replace("_", "-").strip().lower()
    if not normalized:
        return fallback
    normalized = _strip_googletrans_pseudo_suffix(normalized)

    try:
        from googletrans import LANGUAGES as googletrans_languages
    except Exception:
        googletrans_languages = None

    def _coerce_googletrans_code(candidate: str) -> Optional[str]:
        candidate = _strip_googletrans_pseudo_suffix(candidate.replace("_", "-").strip().lower())
        if not googletrans_languages:
            return candidate
        if candidate in googletrans_languages:
            return candidate
        if "-" in candidate:
            base, suffix = candidate.split("-", 1)
            if base in googletrans_languages:
                return base
            if base == "zh":
                if suffix in {"hans", "cn", "sg", "my"}:
                    return "zh-cn"
                if suffix in {"hant", "tw", "hk", "mo"}:
                    return "zh-tw"
        return None

    if _LANG_CODE_PATTERN.match(normalized):
        resolved = _coerce_googletrans_code(normalized)
        return resolved or fallback
    for name, code in LANGUAGE_CODES.items():
        if normalized == name.strip().lower():
            resolved = _coerce_googletrans_code(code)
            return resolved or fallback
    if googletrans_languages:
        for code, name in googletrans_languages.items():
            if normalized == name.strip().lower():
                return code.lower()
        return fallback
    return fallback or normalized


def _get_googletrans_translator():
    """Get thread-local googletrans Translator instance."""
    translator = getattr(_GOOGLETRANS_LOCAL, "translator", None)
    if translator is None:
        from googletrans import Translator

        translator = Translator()
        if hasattr(translator, "raise_exception") and not hasattr(translator, "raise_Exception"):
            setattr(translator, "raise_Exception", translator.raise_exception)
        _GOOGLETRANS_LOCAL.translator = translator
    return translator


def translate_with_googletrans(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> tuple[str, Optional[str]]:
    """Translate text using Google Translate.

    Args:
        sentence: Text to translate
        input_language: Source language code/name
        target_language: Target language code/name
        progress_tracker: Optional progress tracker for retry recording

    Returns:
        Tuple of (translation_result, error_message)
        If successful, error_message is None
        If failed, translation_result contains failure annotation
    """
    health_ok, health_reason = check_googletrans_health()
    if not health_ok:
        failure_reason = f"googletrans health check failed: {health_reason}"
        if progress_tracker is not None:
            progress_tracker.record_retry("translation", failure_reason)
        return (
            format_retry_failure(
                "translation",
                _TRANSLATION_RESPONSE_ATTEMPTS,
                reason=failure_reason,
            ),
            failure_reason,
        )

    last_error: Optional[str] = None
    src_code = resolve_googletrans_language(input_language, fallback="auto") or "auto"
    dest_code = resolve_googletrans_language(target_language, fallback=None)
    if not dest_code:
        failure_reason = f"Unsupported googletrans language: {target_language}"
        if progress_tracker is not None:
            progress_tracker.record_retry("translation", failure_reason)
        return (
            format_retry_failure(
                "translation",
                _TRANSLATION_RESPONSE_ATTEMPTS,
                reason=failure_reason,
            ),
            failure_reason,
        )

    for attempt in range(1, _TRANSLATION_RESPONSE_ATTEMPTS + 1):
        try:
            translator = _get_googletrans_translator()
            result = translator.translate(sentence, src=src_code, dest=dest_code)
            candidate = text_norm.collapse_whitespace((result.text or "").strip())
            if candidate and not text_norm.is_placeholder_translation(candidate):
                return candidate, None
            last_error = "Empty translation response"
        except Exception as exc:  # pragma: no cover - network/remote errors
            last_error = str(exc) or "Google Translate request failed"
        if progress_tracker is not None and last_error:
            progress_tracker.record_retry("translation", last_error)
        if attempt < _TRANSLATION_RESPONSE_ATTEMPTS:
            time.sleep(_TRANSLATION_RETRY_DELAY_SECONDS)

    failure_reason = last_error or "Google Translate error"
    return (
        format_retry_failure(
            "translation",
            _TRANSLATION_RESPONSE_ATTEMPTS,
            reason=failure_reason,
        ),
        failure_reason,
    )
