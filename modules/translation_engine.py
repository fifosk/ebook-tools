"""Translation engine utilities for ebook-tools."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass
from queue import Full, Queue
import threading
import time
from typing import Iterable, Iterator, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from concurrent.futures import Future
    from modules.progress_tracker import ProgressTracker

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules import observability, prompt_templates
from modules import llm_client_manager
from modules.llm_client import LLMClient
from modules.transliteration import TransliterationService, get_transliterator

logger = log_mgr.logger


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
    if not text:
        return False
    lowered = text.lower()
    return "please provide the text" not in lowered


def translate_sentence_simple(
    sentence: str,
    input_language: str,
    target_language: str,
    *,
    include_transliteration: bool = False,
    client: Optional[LLMClient] = None,
) -> str:
    """Translate a sentence using the configured Ollama model."""

    wrapped_sentence = f"<<<{sentence}>>>"
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

        response = resolved_client.send_chat_request(
            payload,
            max_attempts=3,
            timeout=90,
            validator=_valid_translation,
            backoff_seconds=1.0,
        )

        if response.text:
            return response.text.strip()

        if resolved_client.debug_enabled and response.error:
            logger.debug("Translation failed: %s", response.error)

    return "N/A"


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
                    if include_transliteration and translation not in {"", "N/A"}:
                        transliteration_result = transliterator.transliterate(
                            translation, target, client=local_client
                        )
                        transliteration_text = transliteration_result.text
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
