"""Language-specific transliteration utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from modules import logging_manager as log_mgr, prompt_templates
from modules import llm_client_manager
from modules.llm_client import LLMClient

logger = log_mgr.logger


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
    ) -> TransliterationResult:
        lang = target_language.lower()
        with llm_client_manager.client_scope(client) as resolved_client:
            try:
                if lang == "arabic":
                    from camel_tools.transliteration import Transliterator

                    transliterator = Transliterator("buckwalter")
                    return TransliterationResult(
                        transliterator.transliterate(sentence), used_llm=False
                    )
                if lang == "chinese":
                    import pypinyin

                    pinyin_list = pypinyin.lazy_pinyin(sentence)
                    return TransliterationResult(" ".join(pinyin_list), used_llm=False)
                if lang == "japanese":
                    import pykakasi

                    kks = pykakasi.kakasi()
                    result = kks.convert(sentence)
                    return TransliterationResult(
                        " ".join(item["hepburn"] for item in result), used_llm=False
                    )
            except Exception as exc:  # pragma: no cover - best-effort helper
                if resolved_client.debug_enabled:
                    logger.debug(
                        "Non-LLM transliteration error for %s: %s", target_language, exc
                    )

            system_prompt = prompt_templates.make_transliteration_prompt(target_language)
            payload = prompt_templates.make_sentence_payload(
                sentence,
                model=resolved_client.model,
                stream=False,
                system_prompt=system_prompt,
            )

            response = resolved_client.send_chat_request(
                payload, max_attempts=2, timeout=60
            )
            if response.text:
                return TransliterationResult(response.text.strip(), used_llm=True)

            if resolved_client.debug_enabled and response.error:
                logger.debug("LLM transliteration failed: %s", response.error)

        return TransliterationResult("", used_llm=False)


_default_transliterator = TransliterationService()


def get_transliterator() -> TransliterationService:
    """Return the process-wide default :class:`TransliterationService`."""

    return _default_transliterator
