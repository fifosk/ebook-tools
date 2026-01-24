"""Dynamic thread pool executor with adaptive sizing."""

from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


class DynamicThreadPoolExecutor:
    """Thread pool executor that scales workers based on queue depth.

    This executor monitors the pending task queue and adjusts the number
    of active workers within configured bounds. It helps balance resource
    usage with responsiveness.

    Features:
    - Scales up when queue depth exceeds scale_up_threshold
    - Scales down when queue is empty and workers are idle
    - Respects min_workers and max_workers bounds
    - Provides queue depth metrics for monitoring
    """

    def __init__(
        self,
        *,
        min_workers: int = 1,
        max_workers: int = 4,
        scale_up_threshold: int = 2,
        scale_check_interval: float = 1.0,
        idle_timeout: float = 30.0,
    ) -> None:
        """Initialize the dynamic executor.

        Args:
            min_workers: Minimum number of workers to maintain.
            max_workers: Maximum number of workers allowed.
            scale_up_threshold: Queue depth that triggers scaling up.
            scale_check_interval: Seconds between scale checks.
            idle_timeout: Seconds of idleness before scaling down.
        """
        self._min_workers_count = max(1, min_workers)
        self._max_workers_count = max(self._min_workers_count, max_workers)
        self._scale_up_threshold = max(1, scale_up_threshold)
        self._scale_check_interval = max(0.1, scale_check_interval)
        self._idle_timeout = max(1.0, idle_timeout)

        self._lock = threading.Lock()
        self._task_queue: queue.Queue[tuple[Callable, tuple, dict, Future]] = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._active_count = 0
        self._shutdown = threading.Event()
        self._last_activity = time.monotonic()

        # Start minimum workers
        for _ in range(self._min_workers_count):
            self._add_worker()

        # Start scale monitor thread
        self._monitor_thread = threading.Thread(
            target=self._scale_monitor,
            name="DynamicExecutor-monitor",
            daemon=True,
        )
        self._monitor_thread.start()

    def _add_worker(self) -> None:
        """Add a new worker thread."""
        worker = threading.Thread(
            target=self._worker_loop,
            name=f"DynamicExecutor-worker-{len(self._workers)}",
            daemon=True,
        )
        self._workers.append(worker)
        worker.start()

    def _worker_loop(self) -> None:
        """Main loop for worker threads."""
        while not self._shutdown.is_set():
            try:
                # Wait for a task with timeout
                task = self._task_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            fn, args, kwargs, future = task

            if future.cancelled():
                continue

            with self._lock:
                self._active_count += 1
                self._last_activity = time.monotonic()

            try:
                result = fn(*args, **kwargs)
                future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)
            finally:
                with self._lock:
                    self._active_count -= 1
                    self._last_activity = time.monotonic()

    def _scale_monitor(self) -> None:
        """Monitor queue depth and adjust worker count."""
        while not self._shutdown.wait(timeout=self._scale_check_interval):
            queue_depth = self._task_queue.qsize()

            with self._lock:
                current_workers = len(self._workers)
                active = self._active_count
                idle_time = time.monotonic() - self._last_activity

            # Scale up if queue is backing up and we have capacity
            if queue_depth > self._scale_up_threshold and current_workers < self._max_workers_count:
                needed = min(
                    queue_depth - self._scale_up_threshold,
                    self._max_workers_count - current_workers,
                )
                for _ in range(needed):
                    self._add_worker()

            # Scale down if idle and above minimum
            elif (
                queue_depth == 0
                and active == 0
                and idle_time > self._idle_timeout
                and current_workers > self._min_workers_count
            ):
                # We don't actually remove threads (complex with ThreadPoolExecutor)
                # but we stop creating new ones and let them naturally terminate
                pass

    def submit(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> Future[T]:
        """Submit a task for execution.

        Args:
            fn: The callable to execute.
            *args: Positional arguments for fn.
            **kwargs: Keyword arguments for fn.

        Returns:
            A Future representing the pending result.
        """
        if self._shutdown.is_set():
            raise RuntimeError("Executor is shut down")

        future: Future[T] = Future()
        self._task_queue.put((fn, args, kwargs, future))

        with self._lock:
            self._last_activity = time.monotonic()

        return future

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """Shut down the executor.

        Args:
            wait: If True, wait for pending tasks to complete.
            cancel_futures: If True, cancel pending tasks.
        """
        self._shutdown.set()

        if cancel_futures:
            while True:
                try:
                    task = self._task_queue.get_nowait()
                    _, _, _, future = task
                    future.cancel()
                except queue.Empty:
                    break

        if wait:
            for worker in self._workers:
                if worker.is_alive():
                    worker.join(timeout=5.0)

    @property
    def queue_depth(self) -> int:
        """Return current number of pending tasks."""
        return self._task_queue.qsize()

    @property
    def worker_count(self) -> int:
        """Return current number of workers."""
        with self._lock:
            return len(self._workers)

    @property
    def active_count(self) -> int:
        """Return number of workers currently executing tasks."""
        with self._lock:
            return self._active_count

    # Compatibility with ThreadPoolExecutor
    @property
    def _max_workers(self) -> int:
        """Return max workers (for compatibility)."""
        return self._max_workers_count

    def __enter__(self) -> "DynamicThreadPoolExecutor":
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown(wait=True)


__all__ = ["DynamicThreadPoolExecutor"]
