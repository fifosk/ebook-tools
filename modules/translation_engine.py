"""Translation engine utilities for ebook-tools."""

from __future__ import annotations

import asyncio
import concurrent.futures
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Full, Queue
import threading
import time
from typing import Iterable, Iterator, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules import observability, prompt_templates
from modules.llm_client import ClientSettings, LLMClient, create_client

logger = log_mgr.logger


class TranslationWorkerPool:
    """Abstraction for executing translation work using different execution models."""

    def __init__(
        self,
        *,
        max_workers: Optional[int] = None,
        mode: str = "thread",
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        if mode not in {"thread", "async"}:
            raise ValueError("mode must be either 'thread' or 'async'")
        self.mode = mode
        self.max_workers = max(1, max_workers or cfg.get_thread_count())
        self._loop = loop
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._shutdown = False
        observability.worker_pool_event(
            "created", mode=self.mode, max_workers=self.max_workers
        )

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------
    @property
    def is_async(self) -> bool:
        return self.mode == "async"

    def _ensure_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        if self.mode != "thread":
            raise RuntimeError("Executor access is only valid for threaded pools.")
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            )
            observability.worker_pool_event(
                "executor_initialized", mode=self.mode, max_workers=self.max_workers
            )
        return self._executor

    def submit(self, func, *args, **kwargs):
        if self.mode == "thread":
            observability.record_metric(
                "worker_pool.tasks_submitted",
                1.0,
                {"mode": self.mode, "max_workers": self.max_workers},
            )
            return self._ensure_executor().submit(func, *args, **kwargs)

        loop = self._loop or asyncio.get_event_loop()
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
            observability.record_metric(
                "worker_pool.tasks_submitted",
                1.0,
                {"mode": self.mode, "max_workers": self.max_workers},
            )
            return asyncio.ensure_future(result, loop=loop)
        observability.record_metric(
            "worker_pool.tasks_submitted",
            1.0,
            {"mode": self.mode, "max_workers": self.max_workers},
        )
        return loop.run_in_executor(None, lambda: result)

    def iter_completed(self, futures: Iterable) -> Iterator:
        if self.mode != "thread":
            raise RuntimeError(
                "iter_completed is only available in threaded mode. "
                "Use async_iter_completed for asynchronous pools."
            )
        return concurrent.futures.as_completed(futures)

    async def async_iter_completed(self, futures: Iterable) -> Iterator:
        if self.mode != "async":
            raise RuntimeError("async_iter_completed is only available in async mode")
        for awaitable in asyncio.as_completed(list(futures)):
            yield await awaitable

    def shutdown(self, wait: bool = True) -> None:
        if self._shutdown:
            return
        if self.mode == "thread" and self._executor is not None:
            self._executor.shutdown(wait=wait)
        self._shutdown = True
        observability.worker_pool_event(
            "shutdown", mode=self.mode, max_workers=self.max_workers
        )

    def __enter__(self) -> "TranslationWorkerPool":  # pragma: no cover - trivial
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


_DEFAULT_CLIENT_SETTINGS = ClientSettings()


def configure_default_client(
    *,
    model: Optional[str] = None,
    api_url: Optional[str] = None,
    debug: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> None:
    """Adjust the fallback client settings used when no explicit client is provided."""

    global _DEFAULT_CLIENT_SETTINGS
    updates = {}
    if model is not None:
        updates["model"] = model
    if api_url is not None:
        updates["api_url"] = api_url
    if debug is not None:
        updates["debug"] = debug
    if api_key is not None:
        updates["api_key"] = api_key
    if updates:
        _DEFAULT_CLIENT_SETTINGS = _DEFAULT_CLIENT_SETTINGS.with_updates(**updates)


def _borrow_client(client: Optional[LLMClient]) -> tuple[LLMClient, bool]:
    if client is not None:
        return client, False
    return (
        create_client(
            model=_DEFAULT_CLIENT_SETTINGS.model,
            api_url=_DEFAULT_CLIENT_SETTINGS.api_url,
            debug=_DEFAULT_CLIENT_SETTINGS.debug,
            api_key=_DEFAULT_CLIENT_SETTINGS.api_key,
        ),
        True,
    )


@contextmanager
def _client_scope(client: Optional[LLMClient]):
    resolved, owns = _borrow_client(client)
    try:
        yield resolved
    finally:
        if owns:
            resolved.close()


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

    with _client_scope(client) as resolved_client:
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


def transliterate_sentence(
    translated_sentence: str,
    target_language: str,
    *,
    client: Optional[LLMClient] = None,
) -> str:
    """Return a romanised version of ``translated_sentence`` when possible."""

    lang = target_language.lower()
    with _client_scope(client) as resolved_client:
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
            if resolved_client.debug_enabled:
                logger.debug("Non-LLM transliteration error for %s: %s", target_language, exc)

        system_prompt = prompt_templates.make_transliteration_prompt(target_language)
        payload = prompt_templates.make_sentence_payload(
            translated_sentence,
            model=resolved_client.model,
            stream=False,
            system_prompt=system_prompt,
        )

        response = resolved_client.send_chat_request(payload, max_attempts=2, timeout=60)
        if response.text:
            return response.text.strip()

        if resolved_client.debug_enabled and response.error:
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
    client: Optional[LLMClient] = None,
    worker_pool: Optional[TranslationWorkerPool] = None,
) -> List[str]:
    """Translate ``sentences`` concurrently while preserving order."""

    if not sentences:
        return []

    targets = _normalize_target_sequence(target_language, len(sentences))
    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences)))

    results: List[str] = ["" for _ in sentences]

    with _client_scope(client) as resolved_client:
        def _translate(index: int, sentence: str, target: str) -> str:
            return translate_sentence_simple(
                sentence,
                input_language,
                target,
                include_transliteration=include_transliteration,
                client=resolved_client,
            )

        pool = worker_pool or TranslationWorkerPool(max_workers=worker_count)
        if pool.is_async:
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
    worker_pool: Optional[TranslationWorkerPool] = None,
) -> threading.Thread:
    """Spawn a background producer thread that streams translations into ``output_queue``."""

    worker_count = max_workers or cfg.get_thread_count()
    worker_count = max(1, min(worker_count, len(sentences) or 1))

    active_context = cfg.get_runtime_context(None)

    def _producer() -> None:
        if active_context is not None:
            cfg.set_runtime_context(active_context)

        local_client, owns_client = _borrow_client(client)
        pool = worker_pool or TranslationWorkerPool(max_workers=worker_count)
        own_pool = worker_pool is None

        try:
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
                        client=local_client,
                    )
                finally:
                    elapsed = time.perf_counter() - start
                    logger.debug(
                        "Producer translated sentence %s in %.3fs",
                        start_sentence + index,
                        elapsed,
                    )
                return translated

            try:
                if pool.is_async:
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
                if own_pool:
                    pool.shutdown()
        finally:
            for _ in range(max(1, consumer_count)):
                output_queue.put(None)
            if owns_client:
                local_client.close()
            if active_context is not None:
                cfg.clear_runtime_context()

    thread = threading.Thread(target=_producer, name="TranslationProducer", daemon=True)
    thread.start()
    return thread
