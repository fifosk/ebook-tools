"""Helpers for constructing video rendering tasks."""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Sequence

from .context import RenderBatchContext
from .manifest import RenderTask

VideoBatch = Sequence[str]
_VideoTaskFactory = Callable[[VideoBatch], Awaitable[object] | object]


@dataclass(slots=True)
class VideoWorkItem:
    """Simple description of a video rendering unit."""

    label: str


def build_video_tasks(
    batches: Sequence[VideoBatch] | None = None,
    *,
    batch_context: RenderBatchContext | None = None,
    task_factory: _VideoTaskFactory | None = None,
    start_index: int = 0,
) -> List[RenderTask]:
    """Construct render tasks for video batches derived from context information."""

    manifest_context = batch_context.manifest if batch_context else {}
    video_context = batch_context.media_context("video") if batch_context else {}

    if batches is None:
        context_batches = video_context.get("batches") or manifest_context.get("video_batches")
        if isinstance(context_batches, Sequence):
            batches = context_batches
        else:
            batches = []

    if task_factory is None:
        async def _default_factory(batch: VideoBatch) -> Sequence[str]:
            return list(batch)

        task_factory = _default_factory

    tasks: List[RenderTask] = []
    for offset, batch in enumerate(batches):
        async def _runner(batch=batch):
            result = task_factory(batch)
            if inspect.isawaitable(result):
                return await result
            return result

        label = f"video:{start_index + offset}"
        tasks.append(
            RenderTask(
                order=start_index + offset,
                media_type="video",
                action=_runner,
                label=label,
            )
        )
    return tasks


__all__ = ["VideoBatch", "VideoWorkItem", "build_video_tasks"]
