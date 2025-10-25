"""Utilities for batching text rendering workloads."""
from __future__ import annotations

import inspect
import math
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Sequence

from modules.config.loader import get_rendering_config
from .context import RenderBatchContext
from .parallel import RenderTask, RenderingConcurrency

TextBatch = Sequence[str]
_TaskFactory = Callable[[TextBatch], Awaitable[object] | object]


@dataclass(slots=True)
class TextWorkItem:
    """Simple representation of a text rendering unit."""

    chapter: str


def batch_text_chapters(chapters: Sequence[str], concurrency: int) -> List[List[str]]:
    """Group chapters into batches according to the concurrency limit."""

    if concurrency <= 0:
        raise ValueError("concurrency must be greater than zero for text batching")
    if not chapters:
        return []
    batch_size = max(1, math.ceil(len(chapters) / concurrency))
    return [list(chapters[i : i + batch_size]) for i in range(0, len(chapters), batch_size)]


async def _ensure_awaitable(result: object) -> object:
    if inspect.isawaitable(result):
        return await result  # type: ignore[return-value]
    return result


def build_text_tasks(
    chapters: Sequence[str],
    *,
    concurrency: RenderingConcurrency | None = None,
    task_factory: _TaskFactory | None = None,
    start_index: int = 0,
    batch_context: RenderBatchContext | None = None,
) -> List[RenderTask]:
    """Create render tasks for the provided chapters respecting concurrency limits."""

    manifest_context = batch_context.manifest if batch_context else {}
    text_context = batch_context.media_context("text") if batch_context else {}

    if not chapters and text_context:
        context_chapters = text_context.get("chapters") or manifest_context.get("chapters")
        if isinstance(context_chapters, Sequence):
            chapters = context_chapters

    if start_index == 0 and text_context:
        context_start = text_context.get("start_index") or manifest_context.get("start_index")
        if isinstance(context_start, int):
            start_index = context_start

    if concurrency is None:
        config = get_rendering_config()
        concurrency = RenderingConcurrency(
            video=config.video_concurrency,
            audio=config.audio_concurrency,
            text=config.text_concurrency,
        )
    batches = batch_text_chapters(chapters, concurrency.text)

    if task_factory is None:
        async def default_factory(batch: TextBatch) -> List[str]:
            return list(batch)

        task_factory = default_factory

    tasks: List[RenderTask] = []
    for offset, batch in enumerate(batches):
        async def _runner(batch=batch) -> object:
            return await _ensure_awaitable(task_factory(batch))

        tasks.append(
            RenderTask(
                order=start_index + offset,
                media_type="text",
                action=_runner,
                label=f"text:{start_index + offset}",
            )
        )
    return tasks


__all__ = ["TextWorkItem", "batch_text_chapters", "build_text_tasks"]
