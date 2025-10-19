"""Translation engine utilities for ebook-tools."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from queue import Full, Queue
import threading
import time
from typing import List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker

from modules import config_manager as cfg
from modules import llm_client
from modules import logging_manager as log_mgr
from modules import prompt_templates

logger = log_mgr.logger


@dataclass(slots=True)
class TranslationTask:
    """Unit of work produced by the translation pipeline."""

    index: int
    sentence_number: int
    sentence: str
    target_language: str
    translation: str


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


def _normalize_target_sequence(
    target_language: str | Sequence[str],
    sentence_count: int,
) -> List[str]:
    if isinstance(target_language, str):
        return [target_language] * sentence_count
    if not target_language:
        return [""] * sentence_count
    if len(target_language) == 1 and sentence_count > 1:
        return list(target_language) * sentence_count
    if len(target_language) != sentence_count:
        raise ValueError("target_language sequence length must match sentences")
    return list(target_language)


def translate_batch(
    sentences: Sequence[str],
    input_language: str,
    target_language: str | Sequence[str],
    *,
    include_transliteration: bool = False,
    max_workers: Optional[int] = None,
) -> List[str]:
    """Translate ``sentences`` concurrently while preserving order."""

    if not sentences:
        return []

    targets = _normalize_target_sequence(target_language, len(sentences))
    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences)))

    results: List[str] = ["" for _ in sentences]

    def _translate(index: int, sentence: str, target: str) -> str:
        return translate_sentence_simple(
            sentence,
            input_language,
            target,
            include_transliteration=include_transliteration,
        )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(_translate, idx, sentence, target): idx
            for idx, (sentence, target) in enumerate(zip(sentences, targets))
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Translation failed for sentence %s: %s", idx, exc)
                results[idx] = "N/A"

    return results


def start_translation_pipeline(
    sentences: Sequence[str],
    input_language: str,
    target_language: Sequence[str],
    *,
    start_sentence: int,
    output_queue: Queue[Optional[TranslationTask]],
    consumer_count: int,
    stop_event: Optional[threading.Event] = None,
    max_workers: Optional[int] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> threading.Thread:
    """Spawn a background producer thread that streams translations into ``output_queue``."""

    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences) or 1))

    active_context = cfg.get_runtime_context(None)

    def _producer() -> None:
        if active_context is not None:
            cfg.set_runtime_context(active_context)

        if not sentences:
            for _ in range(max(1, consumer_count)):
                output_queue.put(None)
            return

        futures_map: dict = {}

        def _translate(index: int, sentence: str, target: str) -> str:
            start = time.perf_counter()
            try:
                translated = translate_sentence_simple(
                    sentence,
                    input_language,
                    target,
                )
            finally:
                elapsed = time.perf_counter() - start
                logger.debug(
                    "Producer translated sentence %s in %.3fs", start_sentence + index, elapsed
                )
            return translated

        try:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures_map = {
                    executor.submit(_translate, idx, sentence, target): idx
                    for idx, (sentence, target) in enumerate(zip(sentences, target_language))
                }
                for future in as_completed(futures_map):
                    if stop_event and stop_event.is_set():
                        break
                    idx = futures_map[future]
                    sentence_number = start_sentence + idx
                    sentence = sentences[idx]
                    target = target_language[idx]
                    try:
                        translation = future.result()
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.error(
                            "Translation failed for sentence %s: %s", sentence_number, exc
                        )
                        translation = "N/A"
                    task = TranslationTask(
                        index=idx,
                        sentence_number=sentence_number,
                        sentence=sentence,
                        target_language=target,
                        translation=translation,
                    )
                    if progress_tracker:
                        progress_tracker.record_translation_completion(
                            task.index, task.sentence_number
                        )
                    while True:
                        if stop_event and stop_event.is_set():
                            break
                        try:
                            output_queue.put(task, timeout=0.1)
                            break
                        except Full:
                            continue
                    if stop_event and stop_event.is_set():
                        break
        finally:
            for _ in range(max(1, consumer_count)):
                output_queue.put(None)
            if active_context is not None:
                cfg.clear_runtime_context()

    thread = threading.Thread(target=_producer, name="TranslationProducer", daemon=True)
    thread.start()
    return thread
