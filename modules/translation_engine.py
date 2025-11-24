"""Translation engine utilities for ebook-tools."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
from queue import Full, Queue
import threading
import time
from typing import Iterable, Iterator, List, Optional, Sequence, TYPE_CHECKING

import regex

if TYPE_CHECKING:
    from concurrent.futures import Future
    from modules.progress_tracker import ProgressTracker

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules import observability, prompt_templates
from modules import llm_client_manager
from modules import text_normalization as text_norm
from modules.text import split_highlight_tokens
from modules.retry_annotations import format_retry_failure, is_failure_annotation
from modules.llm_client import LLMClient
from modules.transliteration import TransliterationService, get_transliterator

logger = log_mgr.logger

_TRANSLATION_RESPONSE_ATTEMPTS = 5
_TRANSLATION_RETRY_DELAY_SECONDS = 1.0
_LLM_REQUEST_ATTEMPTS = 4
_SEGMENTATION_LANGS = {
    # Thai family
    "thai",
    "th",
    # Khmer / Cambodian
    "khmer",
    "km",
    "cambodian",
    # Burmese / Myanmar
    "burmese",
    "myanmar",
    "my",
    # Japanese
    "japanese",
    "ja",
    "日本語",
    # Korean (should already have spaces, but enforce retries if omitted)
    "korean",
    "ko",
    # Chinese (added cautiously; can be removed if character-level is preferred)
    "chinese",
    "zh",
    "zh-cn",
    "zh-tw",
}
_NON_LATIN_TARGET_HINTS = {
    "arabic",
    "armenian",
    "bengali",
    "bulgarian",
    "chinese",
    "cyrillic",
    "georgian",
    "greek",
    "gujarati",
    "hebrew",
    "hindi",
    "japanese",
    "kannada",
    "korean",
    "malayalam",
    "marathi",
    "punjabi",
    "russian",
    "serbian",
    "sinhala",
    "tamil",
    "telugu",
    "thai",
    "ukrainian",
    "urdu",
}
_LATIN_LETTER_PATTERN = regex.compile(r"\p{Latin}")
_NON_LATIN_LETTER_PATTERN = regex.compile(r"(?!\p{Latin})\p{L}")


class ThreadWorkerPool:
    """Threaded worker pool implementation for translation tasks."""

    mode = "thread"

    def __init__(self, *, max_workers: Optional[int] = None) -> None:
        self.max_workers = max(1, max_workers or cfg.get_thread_count())
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._shutdown = False
        observability.worker_pool_event(
            "created", mode=self.mode, max_workers=self.max_workers
        )

    def _ensure_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            )
            observability.worker_pool_event(
                "executor_initialized", mode=self.mode, max_workers=self.max_workers
            )
        return self._executor

    def submit(self, func, *args, **kwargs) -> Future:
        observability.record_metric(
            "worker_pool.tasks_submitted",
            1.0,
            {"mode": self.mode, "max_workers": self.max_workers},
        )
        return self._ensure_executor().submit(func, *args, **kwargs)

    def iter_completed(self, futures: Iterable[Future]) -> Iterator[Future]:
        return concurrent.futures.as_completed(futures)

    def shutdown(self, wait: bool = True) -> None:
        if self._shutdown:
            return
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
        self._shutdown = True
        observability.worker_pool_event(
            "shutdown", mode=self.mode, max_workers=self.max_workers
        )

    def __enter__(self) -> "ThreadWorkerPool":  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        self.shutdown()


class AsyncWorkerPool:
    """Asynchronous worker pool backed by an event loop."""

    mode = "async"

    def __init__(
        self,
        *,
        max_workers: Optional[int] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self.max_workers = max(1, max_workers or cfg.get_thread_count())
        self._loop = loop or asyncio.get_event_loop()
        self._shutdown = False
        observability.worker_pool_event(
            "created", mode=self.mode, max_workers=self.max_workers
        )

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def submit(self, func, *args, **kwargs) -> asyncio.Future:
        result = func(*args, **kwargs)
        observability.record_metric(
            "worker_pool.tasks_submitted",
            1.0,
            {"mode": self.mode, "max_workers": self.max_workers},
        )
        if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
            return asyncio.ensure_future(result, loop=self._loop)
        return self._loop.run_in_executor(None, lambda: result)

    async def iter_completed(self, futures: Iterable[asyncio.Future]) -> Iterator:
        for awaitable in asyncio.as_completed(list(futures)):
            yield await awaitable

    def shutdown(self, wait: bool = True) -> None:  # pragma: no cover - interface parity
        if self._shutdown:
            return
        self._shutdown = True
        observability.worker_pool_event(
            "shutdown", mode=self.mode, max_workers=self.max_workers
        )

    def __enter__(self) -> "AsyncWorkerPool":  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        self.shutdown()


@dataclass(slots=True)
class TranslationTask:
    """Unit of work produced by the translation pipeline."""

    index: int
    sentence_number: int
    sentence: str
    target_language: str
    translation: str
    transliteration: str = ""


def configure_default_client(**kwargs) -> None:
    """Adjust the fallback client settings used when no explicit client is provided."""

    llm_client_manager.configure_default_client(**kwargs)


def _valid_translation(text: str) -> bool:
    return not text_norm.is_placeholder_translation(text)


def _letter_count(value: str) -> int:
    return sum(1 for char in value if char.isalpha())


def _has_non_latin_letters(value: str) -> bool:
    return bool(_NON_LATIN_LETTER_PATTERN.search(value))


def _latin_fraction(value: str) -> float:
    if not value:
        return 0.0
    latin = len(_LATIN_LETTER_PATTERN.findall(value))
    non_latin = len(_NON_LATIN_LETTER_PATTERN.findall(value))
    total = latin + non_latin
    if total == 0:
        return 0.0
    return latin / total


def _is_probable_transliteration(
    original_sentence: str, translation_text: str, target_language: str
) -> bool:
    """
    Return True when the response likely contains only a Latin transliteration
    even though the target language expects non-Latin script output.
    """

    target_lower = (target_language or "").lower()
    if not translation_text or not _has_non_latin_letters(original_sentence):
        return False
    if not any(hint in target_lower for hint in _NON_LATIN_TARGET_HINTS):
        return False
    return _latin_fraction(translation_text) >= 0.6


def _is_translation_too_short(
    original_sentence: str, translation_text: str
) -> bool:
    """
    Heuristic for truncated translations. Skip very short inputs to avoid
    over-triggering on single words.
    """

    translation_text = translation_text or ""
    original_letters = _letter_count(original_sentence)
    if original_letters <= 12:
        return False
    translation_letters = _letter_count(translation_text)
    if translation_letters == 0:
        return True
    if original_letters >= 80 and translation_letters < 15:
        return True
    ratio = translation_letters / float(original_letters)
    return original_letters >= 30 and ratio < 0.28


def translate_sentence_simple(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    include_transliteration: bool = False,
    client: Optional[LLMClient] = None,
) -> str:
    """Translate a sentence using the configured Ollama model."""

    wrapped_sentence = f"{prompt_templates.SOURCE_START}\n{sentence}\n{prompt_templates.SOURCE_END}"
    system_prompt = prompt_templates.make_translation_prompt(
        input_language,
        target_language,
        include_transliteration=include_transliteration,
    )

    with llm_client_manager.client_scope(client) as resolved_client:
        payload = prompt_templates.make_sentence_payload(
            wrapped_sentence,
            model=resolved_client.model,
            stream=True,
            system_prompt=system_prompt,
        )

        last_error: Optional[str] = None
        for attempt in range(1, _TRANSLATION_RESPONSE_ATTEMPTS + 1):
            response = resolved_client.send_chat_request(
                payload,
                max_attempts=_LLM_REQUEST_ATTEMPTS,
                timeout=90,
                validator=_valid_translation,
                backoff_seconds=1.0,
            )

            if response.text:
                cleaned_text = response.text.strip()
                if cleaned_text and not text_norm.is_placeholder_translation(cleaned_text):
                    translation_text, transliteration_text = text_norm.split_translation_and_transliteration(
                        cleaned_text
                    )
                    if _is_probable_transliteration(
                        sentence, translation_text, target_language
                    ):
                        last_error = "Transliteration returned instead of translation"
                        if resolved_client.debug_enabled:
                            logger.debug(
                                "Retrying translation due to transliteration on attempt %s/%s",
                                attempt,
                                _TRANSLATION_RESPONSE_ATTEMPTS,
                            )
                    elif _is_translation_too_short(sentence, translation_text):
                        last_error = "Translation shorter than expected"
                        if resolved_client.debug_enabled:
                            logger.debug(
                                "Retrying translation due to short response (%s/%s)",
                                attempt,
                                _TRANSLATION_RESPONSE_ATTEMPTS,
                            )
                    elif _is_segmentation_ok(
                        sentence,
                        cleaned_text,
                        target_language,
                        translation_text=translation_text,
                    ):
                        return cleaned_text
                    else:
                        last_error = "Unsegmented translation received"
                        if resolved_client.debug_enabled:
                            logger.debug(
                                "Retrying translation due to missing word spacing (%s/%s)",
                                attempt,
                                _TRANSLATION_RESPONSE_ATTEMPTS,
                            )
                else:
                    last_error = "Placeholder translation received"
                    if resolved_client.debug_enabled:
                        logger.debug(
                            "Retrying translation due to placeholder response (%s/%s)",
                            attempt,
                            _TRANSLATION_RESPONSE_ATTEMPTS,
                        )
            else:
                last_error = response.error or "Empty translation response"
                if resolved_client.debug_enabled and response.error:
                    logger.debug(
                        "Translation attempt %s/%s failed: %s",
                        attempt,
                        _TRANSLATION_RESPONSE_ATTEMPTS,
                        response.error,
                    )

            if attempt < _TRANSLATION_RESPONSE_ATTEMPTS:
                time.sleep(_TRANSLATION_RETRY_DELAY_SECONDS)

            if resolved_client.debug_enabled and last_error:
                logger.debug("Translation failed after retries: %s", last_error)
    failure_reason = last_error or "no response from LLM"
    return format_retry_failure(
        "translation",
        _TRANSLATION_RESPONSE_ATTEMPTS,
        reason=failure_reason,
    )


def _is_segmentation_ok(
    original_sentence: str,
    translation: str,
    target_language: str,
    *,
    translation_text: Optional[str] = None,
) -> bool:
    """
    Require word-like spacing for select languages; otherwise retry.

    We bypass this check when the original sentence is a single word to avoid
    retry loops on very short content.
    """

    lang = (target_language or "").strip().lower()
    if lang not in _SEGMENTATION_LANGS:
        return True
    original_word_count = max(len(original_sentence.split()), 1)
    if original_word_count <= 1:
        return True
    candidate = translation_text or translation
    tokens = split_highlight_tokens(candidate)
    token_count = len(tokens)
    if token_count <= 1:
        return False
    # Accept if segmentation yields enough tokens and isn't clearly over-split.
    required_min = max(4, int(original_word_count * 0.6))
    max_reasonable = original_word_count * 4
    if token_count < required_min:
        return False
    if token_count > max_reasonable:
        return False
    return True



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
    client: Optional[LLMClient] = None,
    worker_pool: Optional[ThreadWorkerPool] = None,
) -> List[str]:
    """Translate ``sentences`` concurrently while preserving order."""

    if not sentences:
        return []

    targets = _normalize_target_sequence(target_language, len(sentences))
    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences)))

    results: List[str] = ["" for _ in sentences]

    with llm_client_manager.client_scope(client) as resolved_client:
        def _translate(index: int, sentence: str, target: str) -> str:
            return translate_sentence_simple(
                sentence,
                input_language,
                target,
                include_transliteration=include_transliteration,
                client=resolved_client,
            )

        pool = worker_pool or ThreadWorkerPool(max_workers=worker_count)
        if getattr(pool, "mode", "thread") != "thread":
            raise RuntimeError(
                "translate_batch does not support asynchronous worker pools in synchronous mode"
            )

        own_pool = worker_pool is None
        try:
            future_map = {
                pool.submit(_translate, idx, sentence, target): idx
                for idx, (sentence, target) in enumerate(zip(sentences, targets))
            }
            for future in pool.iter_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Translation failed for sentence %s: %s", idx, exc)
                    results[idx] = "N/A"
        finally:
            if own_pool:
                pool.shutdown()

    return results


def _enqueue_with_backpressure(
    queue: Queue[Optional[TranslationTask]],
    task: Optional[TranslationTask],
    *,
    stop_event: Optional[threading.Event],
) -> bool:
    while True:
        if stop_event and stop_event.is_set():
            return False
        try:
            queue.put(task, timeout=0.1)
            return True
        except Full:
            continue


def _log_translation_timing(sentence_number: int, elapsed: float, mode: str) -> None:
    observability.record_metric(
        "translation.duration_seconds",
        elapsed,
        {"mode": mode},
    )
    logger.debug(
        "Producer translated sentence %s in %.3fs",
        sentence_number,
        elapsed,
    )


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
    client: Optional[LLMClient] = None,
    worker_pool: Optional[ThreadWorkerPool] = None,
    transliterator: Optional[TransliterationService] = None,
    include_transliteration: bool = False,
) -> threading.Thread:
    """Spawn a background producer thread that streams translations into ``output_queue``."""

    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences) or 1))
    transliterator = transliterator or get_transliterator()

    active_context = cfg.get_runtime_context(None)

    def _producer() -> None:
        if active_context is not None:
            cfg.set_runtime_context(active_context)

        local_client, owns_client = llm_client_manager.acquire_client(client)
        pool = worker_pool or ThreadWorkerPool(max_workers=worker_count)
        own_pool = worker_pool is None
        pool_mode = getattr(pool, "mode", "thread")

        try:
            if not sentences:
                for _ in range(max(1, consumer_count)):
                    _enqueue_with_backpressure(
                        output_queue, None, stop_event=stop_event
                    )
                return

            futures_map: dict = {}

            def _translate(index: int, sentence: str, target: str) -> TranslationTask:
                start_time = time.perf_counter()
                try:
                    translation = translate_sentence_simple(
                        sentence,
                        input_language,
                        target,
                        include_transliteration=include_transliteration,
                        client=local_client,
                    )
                    transliteration_text = ""
                    if (
                        include_transliteration
                        and not text_norm.is_placeholder_translation(translation)
                        and not is_failure_annotation(translation)
                    ):
                        translation_only, inline_transliteration = text_norm.split_translation_and_transliteration(
                            translation
                        )
                        transliteration_text = inline_transliteration.strip()
                        transliteration_source = translation_only or translation
                        if transliteration_source and not transliteration_text:
                            transliteration_result = transliterator.transliterate(
                                transliteration_source, target, client=local_client
                            )
                            transliteration_text = transliteration_result.text.strip()
                finally:
                    elapsed = time.perf_counter() - start_time
                    _log_translation_timing(start_sentence + index, elapsed, pool_mode)
                return TranslationTask(
                    index=index,
                    sentence_number=start_sentence + index,
                    sentence=sentence,
                    target_language=target,
                    translation=translation,
                    transliteration=transliteration_text,
                )

            try:
                if pool_mode != "thread":
                    raise RuntimeError(
                        "start_translation_pipeline requires a threaded worker pool in synchronous mode"
                    )
                futures_map = {
                    pool.submit(_translate, idx, sentence, target): idx
                    for idx, (sentence, target) in enumerate(zip(sentences, target_language))
                }
                for future in pool.iter_completed(futures_map):
                    if stop_event and stop_event.is_set():
                        break
                    idx = futures_map[future]
                    try:
                        task = future.result()
                    except Exception as exc:  # pragma: no cover - defensive logging
                        sentence_number = start_sentence + idx
                        logger.error(
                            "Translation failed for sentence %s: %s", sentence_number, exc
                        )
                        task = TranslationTask(
                            index=idx,
                            sentence_number=sentence_number,
                            sentence=sentences[idx],
                            target_language=target_language[idx],
                            translation="N/A",
                        )
                    if progress_tracker:
                        progress_tracker.record_translation_completion(
                            task.index, task.sentence_number
                        )
                    if not _enqueue_with_backpressure(
                        output_queue, task, stop_event=stop_event
                    ):
                        break
                else:
                    # Only executed if loop did not break
                    pass
            finally:
                if own_pool:
                    pool.shutdown()
        finally:
            for _ in range(max(1, consumer_count)):
                _enqueue_with_backpressure(
                    output_queue, None, stop_event=stop_event
                )
            llm_client_manager.release_client(local_client, owns_client)
            if active_context is not None:
                cfg.clear_runtime_context()

    thread = threading.Thread(target=_producer, name="TranslationProducer", daemon=True)
    thread.start()
    return thread
