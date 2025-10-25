"""Thread and async orchestration utilities for media rendering."""

from __future__ import annotations

import asyncio
import inspect
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from queue import Queue
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    Iterable,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
)

from modules import config_manager as cfg
from modules.config.loader import RenderingConfig, get_rendering_config

from .audio_pipeline import AudioGenerator, AudioWorker

if TYPE_CHECKING:  # pragma: no cover - imports used for static analysis only
    from modules.progress_tracker import ProgressTracker
    from modules.translation_engine import TranslationTask
    from modules.audio_video_generator import MediaPipelineResult


MediaType = Literal["video", "audio", "text"]


@dataclass(frozen=True, slots=True)
class RenderingConcurrency:
    """Concurrency limits for each media pipeline."""

    video: int
    audio: int
    text: int

    def __post_init__(self) -> None:
        for name in ("video", "audio", "text"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} concurrency must be greater than zero")

    @classmethod
    def from_config(cls, config: RenderingConfig) -> "RenderingConcurrency":
        return cls(
            video=config.video_concurrency,
            audio=config.audio_concurrency,
            text=config.text_concurrency,
        )


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
            raise TypeError(
                "RenderTask action must produce an awaitable result"
            )
        return await result  # type: ignore[return-value]


class RenderManifest:
    """Container that exposes render tasks to media-specific workers."""

    def __init__(self, tasks: Iterable[RenderTask] | None = None) -> None:
        self._queues: Dict[MediaType, Deque[RenderTask]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._size = 0
        if tasks:
            for task in tasks:
                self.add_task(task)

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
                # Clean up empty queues to keep ``__len__`` accurate
                self._queues.pop(media_type, None)
            return task

    def __len__(self) -> int:  # pragma: no cover - trivial
        return self._size


async def dispatch_render_manifest(
    manifest: RenderManifest,
    *,
    concurrency: Optional[RenderingConcurrency] = None,
) -> list[Any]:
    """Execute render tasks grouped by media type using task groups."""

    if concurrency is None:
        config = get_rendering_config()
        concurrency = RenderingConcurrency.from_config(config)

    results: Dict[int, Any] = {}
    results_lock = asyncio.Lock()

    async def worker(media_type: MediaType) -> None:
        while True:
            task = await manifest.acquire(media_type)
            if task is None:
                break
            result = await task.run()
            async with results_lock:
                results[task.order] = result

    async def launch_group(media_type: MediaType, limit: int) -> None:
        async with asyncio.TaskGroup() as group:
            for _ in range(limit):
                group.create_task(worker(media_type))

    async with asyncio.TaskGroup() as root_group:
        root_group.create_task(launch_group("video", concurrency.video))
        root_group.create_task(launch_group("audio", concurrency.audio))
        root_group.create_task(launch_group("text", concurrency.text))

    return [results[index] for index in sorted(results)]


class MediaBatchOrchestrator:
    """Manage media worker threads and shared queues for batch processing."""

    def __init__(
        self,
        audio_task_queue: "Queue[Optional[TranslationTask]]",
        *,
        worker_count: Optional[int] = None,
        total_sentences: int,
        input_language: str,
        audio_mode: str,
        language_codes: Mapping[str, str],
        selected_voice: str,
        tempo: float,
        macos_reading_speed: int,
        generate_audio: bool,
        queue_size: Optional[int] = None,
        audio_stop_event: Optional[threading.Event] = None,
        progress_tracker: Optional["ProgressTracker"] = None,
        audio_generator: Optional[AudioGenerator] = None,
        media_result_factory: Optional[Callable[..., "MediaPipelineResult"]] = None,
        audio_worker_cls: Type[AudioWorker] = AudioWorker,
    ) -> None:
        self.audio_task_queue = audio_task_queue
        self.worker_count = worker_count
        self.total_sentences = total_sentences
        self.input_language = input_language
        self.audio_mode = audio_mode
        self.language_codes = language_codes
        self.selected_voice = selected_voice
        self.tempo = tempo
        self.macos_reading_speed = macos_reading_speed
        self.generate_audio = generate_audio
        self.queue_size = queue_size
        self.audio_stop_event = audio_stop_event or threading.Event()
        self.progress_tracker = progress_tracker
        self.audio_generator = audio_generator
        self.media_result_factory = media_result_factory
        self.audio_worker_cls = audio_worker_cls
        self._active_context = cfg.get_runtime_context(None)

    def start(self) -> Tuple["Queue[Optional[MediaPipelineResult]]", Sequence[threading.Thread]]:
        """Start the configured audio workers and return the result queue."""

        worker_total = self.worker_count or cfg.get_thread_count()
        worker_total = max(1, worker_total)
        audio_result_queue: "Queue[Optional[MediaPipelineResult]]" = Queue(
            maxsize=self.queue_size or 0
        )

        threads: list[threading.Thread] = []
        for index in range(worker_total):
            worker_name = f"AudioWorker-{index + 1}"
            worker = self.audio_worker_cls(
                worker_name,
                self.audio_task_queue,
                audio_result_queue,
                total_sentences=self.total_sentences,
                input_language=self.input_language,
                audio_mode=self.audio_mode,
                language_codes=self.language_codes,
                selected_voice=self.selected_voice,
                tempo=self.tempo,
                macos_reading_speed=self.macos_reading_speed,
                generate_audio=self.generate_audio,
                audio_stop_event=self.audio_stop_event,
                progress_tracker=self.progress_tracker,
                audio_generator=self.audio_generator,
                media_result_factory=self.media_result_factory,
            )
            thread = threading.Thread(
                target=self._thread_target,
                name=worker_name,
                args=(worker,),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        return audio_result_queue, threads

    def _thread_target(self, worker: AudioWorker) -> None:
        """Dispatch a worker while maintaining the runtime config context."""

        if self._active_context is not None:
            cfg.set_runtime_context(self._active_context)
        try:
            worker.run()
        finally:
            if self._active_context is not None:
                cfg.clear_runtime_context()


__all__ = [
    "MediaBatchOrchestrator",
    "RenderManifest",
    "RenderTask",
    "RenderingConcurrency",
    "dispatch_render_manifest",
]
