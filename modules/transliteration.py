"""Language-specific transliteration utilities."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from modules import logging_manager as log_mgr, prompt_templates, text_normalization as text_norm
from modules import llm_client_manager
from modules.llm_client import LLMClient
from modules.retry_annotations import format_retry_failure

logger = log_mgr.logger

_TRANSLITERATION_ATTEMPTS = 3
_TRANSLITERATION_RETRY_DELAY_SECONDS = 0.5
_PYTHON_ONLY_MODES = {"python", "python_module", "module", "local_module"}
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
    "japanese": {"japanese", "ja"},
}
_LOCAL_MODULE_LABELS = {
    "arabic": "camel_tools.buckwalter",
    "chinese": "pypinyin",
    "japanese": "pykakasi",
}


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
        with llm_client_manager.client_scope(client) as resolved_client:
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

            system_prompt = prompt_templates.make_transliteration_prompt(target_language)
            payload = prompt_templates.make_sentence_payload(
                sentence,
                model=resolved_client.model,
                stream=False,
                system_prompt=system_prompt,
            )

            last_error: Optional[str] = None
            for attempt in range(1, _TRANSLITERATION_ATTEMPTS + 1):
                response = resolved_client.send_chat_request(
                    payload, max_attempts=2, timeout=60
                )
                if response.text:
                    candidate = response.text.strip()
                    if not text_norm.is_placeholder_value(candidate):
                        return TransliterationResult(candidate, used_llm=True)
                    last_error = "Placeholder transliteration response"
                else:
                    last_error = response.error or "Empty transliteration response"
                if progress_tracker is not None and last_error:
                    progress_tracker.record_retry("transliteration", last_error)
                if attempt < _TRANSLITERATION_ATTEMPTS:
                    time.sleep(_TRANSLITERATION_RETRY_DELAY_SECONDS)
            if resolved_client.debug_enabled and last_error:
                logger.debug("LLM transliteration failed: %s", last_error)

        failure_reason = last_error or "no response from LLM"
        failure_text = format_retry_failure(
            "transliteration",
            _TRANSLITERATION_ATTEMPTS,
            reason=failure_reason,
        )
        return TransliterationResult(failure_text, used_llm=False)


_default_transliterator = TransliterationService()


def get_transliterator() -> TransliterationService:
    """Return the process-wide default :class:`TransliterationService`."""

    return _default_transliterator


def resolve_local_transliteration_module(target_language: str) -> Optional[str]:
    """Return the python-module transliteration label for ``target_language`` when supported."""

    lang = _normalize_language_hint(target_language)
    for key, aliases in _LANGUAGE_ALIASES.items():
        if lang in aliases:
            return _LOCAL_MODULE_LABELS.get(key)
    return None


def _normalize_language_hint(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("_", "-")
    return normalized


def _transliterate_with_python(sentence: str, lang: str) -> str:
    for key, aliases in _LANGUAGE_ALIASES.items():
        if lang not in aliases:
            continue
        if key == "arabic":
            from camel_tools.transliteration import Transliterator

            transliterator = Transliterator("buckwalter")
            return transliterator.transliterate(sentence)
        if key == "chinese":
            import pypinyin

            pinyin_list = pypinyin.lazy_pinyin(sentence)
            return " ".join(pinyin_list)
        if key == "japanese":
            import pykakasi

            kks = pykakasi.kakasi()
            result = kks.convert(sentence)
            return " ".join(item["hepburn"] for item in result)
    return ""
