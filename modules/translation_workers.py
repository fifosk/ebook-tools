"""Worker pool implementations for translation tasks.

This module provides thread-based and async worker pool implementations
used by the translation pipeline for parallel processing of translation tasks.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Iterable, Iterator, Optional

from concurrent.futures import Future

from modules import config_manager as cfg, observability


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
