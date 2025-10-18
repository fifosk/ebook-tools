"""Translation engine utilities for ebook-tools."""

from __future__ import annotations

from typing import Optional

from modules import llm_client
from modules import logging_manager as log_mgr
from modules import prompt_templates

logger = log_mgr.logger


def set_model(model: Optional[str]) -> None:
    """Configure the Ollama model used for translation requests."""

    llm_client.set_model(model)


def get_model() -> str:
    """Return the currently configured Ollama model."""

    return llm_client.get_model()


def set_debug(enabled: bool) -> None:
    """Toggle verbose debug logging for translation requests."""

    llm_client.set_debug(bool(enabled))


def is_debug_enabled() -> bool:
    """Return whether debug logging is enabled for translation operations."""

    return llm_client.is_debug_enabled()


def _valid_translation(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return "please provide the text" not in lowered


def translate_sentence_simple(
    sentence: str,
    input_language: str,
    target_language: str,
    include_transliteration: bool = False,
) -> str:
    """Translate a sentence using the configured Ollama model."""

    wrapped_sentence = f"<<<{sentence}>>>"
    system_prompt = prompt_templates.make_translation_prompt(
        input_language,
        target_language,
        include_transliteration=include_transliteration,
    )

    payload = prompt_templates.make_sentence_payload(
        wrapped_sentence,
        model=get_model(),
        stream=True,
        system_prompt=system_prompt,
    )

    response = llm_client.send_chat_request(
        payload,
        max_attempts=3,
        timeout=90,
        validator=_valid_translation,
        backoff_seconds=1.0,
    )

    if response.text:
        return response.text.strip()

    if is_debug_enabled() and response.error:
        logger.debug("Translation failed: %s", response.error)

    return "N/A"


def transliterate_sentence(translated_sentence: str, target_language: str) -> str:
    """Return a romanised version of ``translated_sentence`` when possible."""

    lang = target_language.lower()
    try:
        if lang == "arabic":
            from camel_tools.transliteration import Transliterator

            transliterator = Transliterator("buckwalter")
            return transliterator.transliterate(translated_sentence)
        if lang == "chinese":
            import pypinyin

            pinyin_list = pypinyin.lazy_pinyin(translated_sentence)
            return " ".join(pinyin_list)
        if lang == "japanese":
            import pykakasi

            kks = pykakasi.kakasi()
            result = kks.convert(translated_sentence)
            return " ".join(item["hepburn"] for item in result)
    except Exception as exc:  # pragma: no cover - best-effort helper
        if is_debug_enabled():
            logger.debug("Non-LLM transliteration error for %s: %s", target_language, exc)

    system_prompt = prompt_templates.make_transliteration_prompt(target_language)
    payload = prompt_templates.make_sentence_payload(
        translated_sentence,
        model=get_model(),
        stream=False,
        system_prompt=system_prompt,
    )

    response = llm_client.send_chat_request(payload, max_attempts=2, timeout=60)
    if response.text:
        return response.text.strip()

    if is_debug_enabled() and response.error:
        logger.debug("LLM transliteration failed: %s", response.error)

    return ""
