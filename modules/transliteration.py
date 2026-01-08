"""Language-specific transliteration utilities."""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Optional

from modules import config_manager as cfg
from modules import fallbacks
from modules import logging_manager as log_mgr, prompt_templates, text_normalization as text_norm
from modules import llm_client_manager
from modules.llm_client import LLMClient
from modules.retry_annotations import format_retry_failure, is_failure_annotation

logger = log_mgr.logger

_TRANSLITERATION_ATTEMPTS = 3
_TRANSLITERATION_RETRY_DELAY_SECONDS = 0.5
_PYTHON_ONLY_MODES = {
    "python",
    "python-module",
    "python_module",
    "module",
    "local-module",
    "local_module",
}
_LANGUAGE_ALIASES = {
    "arabic": {"arabic", "ar"},
    "chinese": {
        "chinese",
        "zh",
        "zh-cn",
        "zh-tw",
        "chinese (simplified)",
        "chinese (traditional)",
    },
    "hebrew": {"hebrew", "he", "iw"},
    "hindi": {"hindi", "hi"},
    "japanese": {"japanese", "ja"},
    "korean": {"korean", "ko"},
}
_LOCAL_MODULE_LABELS = {
    "arabic": "camel_tools.buckwalter",
    "chinese": "pypinyin",
    "hebrew": "hebrew_keymap",
    "hindi": "indic_transliteration",
    "japanese": "pykakasi",
    "korean": "hangul-romanize",
}
_HEBREW_TRANSLITERATION_MAP = {
    "א": "'",
    "ב": "b",
    "ג": "g",
    "ד": "d",
    "ה": "h",
    "ו": "v",
    "ז": "z",
    "ח": "kh",
    "ט": "t",
    "י": "y",
    "כ": "k",
    "ך": "k",
    "ל": "l",
    "מ": "m",
    "ם": "m",
    "נ": "n",
    "ן": "n",
    "ס": "s",
    "ע": "`",
    "פ": "p",
    "ף": "p",
    "צ": "ts",
    "ץ": "ts",
    "ק": "k",
    "ר": "r",
    "ש": "sh",
    "ת": "t",
}


def _is_timeout_error(reason: Optional[str]) -> bool:
    if not reason:
        return False
    lowered = reason.lower()
    return "timeout" in lowered or "timed out" in lowered


@dataclass(slots=True)
class TransliterationResult:
    """Container returned by :class:`TransliterationService`."""

    text: str
    used_llm: bool


class TransliterationService:
    """Best-effort transliteration handler with local fallbacks and LLM support."""

    def transliterate(
        self,
        sentence: str,
        target_language: str,
        *,
        client: Optional[LLMClient] = None,
        mode: Optional[str] = None,
        progress_tracker=None,
    ) -> TransliterationResult:
        lang = _normalize_language_hint(target_language)
        mode_label = (mode or "").strip().lower()
        python_only = mode_label in _PYTHON_ONLY_MODES
        fallback_model = fallbacks.get_llm_fallback_model(progress_tracker)
        fallback_active = bool(fallback_model)
        fallback_client = (
            fallbacks.get_fallback_llm_client(fallback_model) if fallback_model else None
        )

        def _run_llm(resolved_client: LLMClient) -> tuple[TransliterationResult, Optional[str], float]:
            system_prompt = prompt_templates.make_transliteration_prompt(target_language)
            payload = prompt_templates.make_sentence_payload(
                sentence,
                model=resolved_client.model,
                stream=False,
                system_prompt=system_prompt,
            )
            last_error: Optional[str] = None
            start_time = time.perf_counter()
            for attempt in range(1, _TRANSLITERATION_ATTEMPTS + 1):
                response = resolved_client.send_chat_request(
                    payload, max_attempts=2, timeout=cfg.get_translation_llm_timeout_seconds()
                )
                if response.text:
                    candidate = response.text.strip()
                    if not text_norm.is_placeholder_value(candidate):
                        elapsed = time.perf_counter() - start_time
                        return TransliterationResult(candidate, used_llm=True), None, elapsed
                    last_error = "Placeholder transliteration response"
                else:
                    last_error = response.error or "Empty transliteration response"
                if progress_tracker is not None and last_error:
                    progress_tracker.record_retry("transliteration", last_error)
                if attempt < _TRANSLITERATION_ATTEMPTS:
                    time.sleep(_TRANSLITERATION_RETRY_DELAY_SECONDS)
            if resolved_client.debug_enabled and last_error:
                logger.debug("LLM transliteration failed: %s", last_error)
            elapsed = time.perf_counter() - start_time
            failure_reason = last_error or "no response from LLM"
            failure_text = format_retry_failure(
                "transliteration",
                _TRANSLITERATION_ATTEMPTS,
                reason=failure_reason,
            )
            return TransliterationResult(failure_text, used_llm=False), failure_reason, elapsed

        with llm_client_manager.client_scope(fallback_client or client) as resolved_client:
            current_model = resolved_client.model
            try:
                local_text = _transliterate_with_python(sentence, lang)
                if local_text:
                    return TransliterationResult(local_text, used_llm=False)
            except Exception as exc:  # pragma: no cover - best-effort helper
                if resolved_client.debug_enabled:
                    logger.debug(
                        "Non-LLM transliteration error for %s: %s", target_language, exc
                    )
            if python_only:
                failure_text = format_retry_failure(
                    "transliteration",
                    _TRANSLITERATION_ATTEMPTS,
                    reason="Python transliteration unavailable for language",
                )
                return TransliterationResult(failure_text, used_llm=False)

            result, last_error, elapsed = _run_llm(resolved_client)

        if not fallback_active:
            timeout_seconds = cfg.get_translation_llm_timeout_seconds()
            if timeout_seconds > 0 and elapsed > timeout_seconds:
                reason = f"LLM response exceeded {timeout_seconds:.0f}s ({elapsed:.1f}s)"
                fallbacks.record_translation_fallback(
                    progress_tracker,
                    trigger="llm_timeout",
                    reason=reason,
                    source_provider="llm",
                    fallback_model=cfg.get_translation_fallback_model(),
                    scope="transliteration",
                    elapsed_seconds=elapsed,
                )
            if is_failure_annotation(result.text):
                reason = last_error or "LLM transliteration failed"
                trigger = "llm_timeout" if _is_timeout_error(reason) else "llm_error"
                detail = fallbacks.record_translation_fallback(
                    progress_tracker,
                    trigger=trigger,
                    reason=reason,
                    source_provider="llm",
                    fallback_model=cfg.get_translation_fallback_model(),
                    scope="transliteration",
                )
                model_override = (detail or {}).get("fallback_model") if detail else None
                if model_override and current_model.strip().lower() != model_override.strip().lower():
                    fallback_client = fallbacks.get_fallback_llm_client(model_override)
                    with llm_client_manager.client_scope(fallback_client) as fallback_resolved:
                        result, _error, _elapsed = _run_llm(fallback_resolved)

        return result


_default_transliterator = TransliterationService()


def get_transliterator() -> TransliterationService:
    """Return the process-wide default :class:`TransliterationService`."""

    return _default_transliterator


def resolve_local_transliteration_module(target_language: str) -> Optional[str]:
    """Return the python-module transliteration label for ``target_language`` when supported."""

    candidates = _language_candidates(target_language)
    if not candidates:
        return None
    for key, aliases in _LANGUAGE_ALIASES.items():
        if candidates.intersection(aliases):
            return _LOCAL_MODULE_LABELS.get(key)
    return None


def _normalize_language_hint(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("_", "-")
    normalized = re.sub(r"\(.*?\)", "", normalized)
    normalized = re.sub(r"[^\w-]+", " ", normalized)
    return " ".join(normalized.split())


def _language_candidates(value: str) -> set[str]:
    normalized = _normalize_language_hint(value)
    if not normalized:
        return set()
    candidates = {normalized}
    if " " in normalized:
        candidates.add(normalized.split()[0])
    if "-" in normalized:
        candidates.add(normalized.split("-")[0])
    return {candidate for candidate in candidates if candidate}


def _strip_combining_marks(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.combining(ch) == 0)


def _transliterate_hebrew(text: str) -> str:
    stripped = _strip_combining_marks(text)
    return "".join(_HEBREW_TRANSLITERATION_MAP.get(ch, ch) for ch in stripped)


def _transliterate_with_python(sentence: str, lang: str) -> str:
    candidates = _language_candidates(lang)
    if not candidates:
        return ""
    for key, aliases in _LANGUAGE_ALIASES.items():
        if not candidates.intersection(aliases):
            continue
        if key == "arabic":
            from camel_tools.transliteration import Transliterator

            transliterator = Transliterator("buckwalter")
            return transliterator.transliterate(sentence)
        if key == "chinese":
            import pypinyin

            pinyin_list = pypinyin.lazy_pinyin(sentence)
            return " ".join(pinyin_list)
        if key == "hebrew":
            return _transliterate_hebrew(sentence)
        if key == "hindi":
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate

            return transliterate(sentence, sanscript.DEVANAGARI, sanscript.ITRANS)
        if key == "japanese":
            import pykakasi

            kks = pykakasi.kakasi()
            result = kks.convert(sentence)
            return " ".join(item["hepburn"] for item in result)
        if key == "korean":
            from hangul_romanize import Transliter
            from hangul_romanize.rule import academic

            transliterator = Transliter(academic)
            return transliterator.translit(sentence)
    return ""
