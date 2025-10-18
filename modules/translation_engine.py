"""Translation engine utilities for ebook-tools.

This module encapsulates translation and transliteration helpers that rely on
Ollama.  The functions here are intentionally side-effect free apart from the
HTTP calls they perform so that the main program can focus on orchestration.
"""

from __future__ import annotations

import json
import time
from typing import Optional

import requests

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

logger = log_mgr.logger

_DEFAULT_MODEL = cfg.DEFAULT_MODEL
_ollama_model = _DEFAULT_MODEL
_debug_enabled = False


def set_model(model: Optional[str]) -> None:
    """Configure the Ollama model used for translation requests."""
    global _ollama_model
    _ollama_model = model or _DEFAULT_MODEL


def get_model() -> str:
    """Return the currently configured Ollama model."""
    return _ollama_model


def set_debug(enabled: bool) -> None:
    """Toggle verbose debug logging for translation requests."""
    global _debug_enabled
    _debug_enabled = bool(enabled)


def is_debug_enabled() -> bool:
    """Return whether debug logging is enabled for translation operations."""
    return _debug_enabled


def translate_sentence_simple(
    sentence: str,
    input_language: str,
    target_language: str,
    include_transliteration: bool = False,
) -> str:
    """Translate a sentence using the configured Ollama model.

    The request streams partial responses which are concatenated before being
    returned.  A small retry loop is used to improve resilience when Ollama is
    temporarily unavailable.
    """

    wrapped_sentence = f"<<<{sentence}>>>"

    prompt = (
        f"Translate the following text from {input_language} to {target_language}.\n"
        "The text to be translated is enclosed between <<< and >>>.\n"
        "Provide ONLY the translated text on a SINGLE LINE without commentary or markers."
    )

    payload = {
        "model": _ollama_model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": wrapped_sentence},
        ],
        "stream": True,
    }

    for attempt in range(3):
        try:
            if _debug_enabled:
                logger.debug("Sending translation request (attempt %s)...", attempt + 1)
                logger.debug("Payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

            response = requests.post(
                cfg.OLLAMA_API_URL, json=payload, stream=True, timeout=90
            )
            if response.status_code != 200:
                if _debug_enabled:
                    logger.debug("HTTP %s: %s", response.status_code, response.text[:300])
                continue

            full_text = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = data.get("message", {}).get("content", "")
                if msg:
                    full_text += msg

            full_text = full_text.strip()

            if _debug_enabled:
                logger.debug("Raw translation result: %r", full_text)

            if not full_text or "please provide the text" in full_text.lower():
                if _debug_enabled:
                    logger.debug("Empty or invalid translation, retrying...")
                time.sleep(1)
                continue

            return full_text

        except requests.exceptions.RequestException as exc:  # pragma: no cover - network
            if _debug_enabled:
                logger.debug("Request error: %s", exc)
            time.sleep(1)
            continue
        except Exception as exc:  # pragma: no cover - defensive
            if _debug_enabled:
                logger.debug("Unexpected error: %s", exc)
            time.sleep(1)
            continue

    return "N/A"


def transliterate_sentence(translated_sentence: str, target_language: str) -> str:
    """Return a romanised version of ``translated_sentence`` when possible.

    Dedicated packages are used for supported languages; when they are not
    available we fall back to the Ollama model to request a transliteration.
    """

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
        if _debug_enabled:
            logger.debug("Non-LLM transliteration error for %s: %s", target_language, exc)

    prompt = (
        f"Transliterate the following sentence in {target_language} for English pronounciation.\n"
        "Provide ONLY the transliteration on a SINGLE LINE without ANY additional text or commentary."
    )
    payload = {
        "model": _ollama_model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": translated_sentence},
        ],
        "stream": False,
    }
    try:
        if _debug_enabled:
            logger.debug("Sending transliteration request via LLM fallback...")
            logger.debug("Payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))
        response = requests.post(cfg.OLLAMA_API_URL, json=payload)
        if response.status_code == 200:
            result = response.json().get("message", {}).get("content", "")
            return result.strip()
        if _debug_enabled:
            logger.debug(
                "LLM fallback transliteration error: %s - %s",
                response.status_code,
                response.text,
            )
    except Exception as exc:  # pragma: no cover - network
        if _debug_enabled:
            logger.debug("Exception during LLM fallback transliteration: %s", exc)
    return ""
