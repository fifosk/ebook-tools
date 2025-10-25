"""Render manifest primitives shared across media pipelines."""
from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Deque, Dict, Iterable, Optional

from .context import MediaType, RenderBatchContext


@dataclass(slots=True)
class RenderTask:
    """Description of a single asynchronous render operation."""

    order: int
    media_type: MediaType
    action: Callable[[], Awaitable[Any]] | Awaitable[Any]
    label: Optional[str] = None

    async def run(self) -> Any:
        """Execute the task action and return its result."""

        if inspect.iscoroutine(self.action) or inspect.isawaitable(self.action):
            return await self.action  # type: ignore[return-value]
        result = self.action()
        if not inspect.isawaitable(result):
            raise TypeError("RenderTask action must produce an awaitable result")
        return await result  # type: ignore[return-value]


class RenderManifest:
    """Container that exposes render tasks to media-specific workers."""

    def __init__(
        self,
        tasks: Iterable[RenderTask] | None = None,
        *,
        context: Optional[RenderBatchContext] = None,
    ) -> None:
        self._queues: Dict[MediaType, Deque[RenderTask]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._size = 0
        self._context = context or RenderBatchContext()
        if tasks:
            for task in tasks:
                self.add_task(task)

    @property
    def context(self) -> RenderBatchContext:
        """Return the context associated with this manifest."""

        return self._context

    def set_context(self, context: RenderBatchContext) -> None:
        """Update the manifest context."""

        self._context = context

    def add_task(self, task: RenderTask) -> None:
        self._queues[task.media_type].append(task)
        self._size += 1

    async def acquire(self, media_type: MediaType) -> Optional[RenderTask]:
        """Return the next task for ``media_type`` or ``None`` if exhausted."""

        async with self._lock:
            queue = self._queues.get(media_type)
            if not queue:
                return None
            self._size -= 1
            task = queue.popleft()
            if not queue:
                self._queues.pop(media_type, None)
            return task

    def __len__(self) -> int:  # pragma: no cover - trivial
        return self._size


__all__ = ["RenderManifest", "RenderTask"]
