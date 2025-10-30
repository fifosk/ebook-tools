"""Thread and async orchestration utilities for media rendering."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from queue import Queue
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
)

from modules import config_manager as cfg
from modules.audio.backends import get_default_backend_name
from modules.config.loader import RenderingConfig, get_rendering_config


DEFAULT_TTS_BACKEND = get_default_backend_name()

from .audio_pipeline import AudioGenerator, AudioWorker
from .backends import AudioSynthesizer, get_audio_synthesizer
from .context import MediaType, RenderBatchContext
from .manifest import RenderManifest, RenderTask

if TYPE_CHECKING:  # pragma: no cover - imports used for static analysis only
    from modules.progress_tracker import ProgressTracker
    from modules.translation_engine import TranslationTask
    from modules.audio_video_generator import MediaPipelineResult


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
        voice_overrides: Mapping[str, str] | None = None,
        generate_audio: bool,
        tts_backend: str = DEFAULT_TTS_BACKEND,
        tts_executable_path: Optional[str] = None,
        queue_size: Optional[int] = None,
        audio_stop_event: Optional[threading.Event] = None,
        progress_tracker: Optional["ProgressTracker"] = None,
        audio_generator: Optional[AudioGenerator] = None,
        audio_synthesizer: Optional[AudioSynthesizer] = None,
        media_result_factory: Optional[Callable[..., "MediaPipelineResult"]] = None,
        audio_worker_cls: Type[AudioWorker] = AudioWorker,
        batch_context: Optional[RenderBatchContext] = None,
    ) -> None:
        self.audio_task_queue = audio_task_queue
        self.worker_count = worker_count
        self.queue_size = queue_size
        self.audio_stop_event = audio_stop_event or threading.Event()
        self.progress_tracker = progress_tracker
        if voice_overrides:
            resolved_voice_overrides = {
                str(key).strip(): str(value).strip()
                for key, value in voice_overrides.items()
                if isinstance(key, str)
                and isinstance(value, str)
                and str(key).strip()
                and str(value).strip()
            }
        else:
            resolved_voice_overrides = {}
        if audio_generator and audio_synthesizer:
            raise ValueError("Provide either audio_generator or audio_synthesizer, not both")
        if audio_generator is not None:
            self._audio_callable = audio_generator
            self.audio_synthesizer = None
        else:
            synthesizer = audio_synthesizer or get_audio_synthesizer()
            self.audio_synthesizer = synthesizer
            self._audio_callable = (
                synthesizer.synthesize_sentence if synthesizer is not None else None
            )
        self.audio_generator = self._audio_callable
        if media_result_factory is None:
            raise ValueError("media_result_factory must be provided for audio workers")
        self.media_result_factory = media_result_factory
        self.audio_worker_cls = audio_worker_cls
        manifest_payload = {
            "total_sentences": total_sentences,
            "input_language": input_language,
            "audio_mode": audio_mode,
            "selected_voice": selected_voice,
            "voice_overrides": dict(resolved_voice_overrides),
            "tempo": tempo,
            "macos_reading_speed": macos_reading_speed,
            "generate_audio": generate_audio,
            "tts_backend": tts_backend,
            "tts_executable_path": tts_executable_path,
            "say_path": tts_executable_path,
        }
        audio_payload = {
            "total_sentences": total_sentences,
            "input_language": input_language,
            "audio_mode": audio_mode,
            "language_codes": dict(language_codes),
            "selected_voice": selected_voice,
            "voice_overrides": dict(resolved_voice_overrides),
            "tempo": tempo,
            "macos_reading_speed": macos_reading_speed,
            "generate_audio": generate_audio,
            "tts_backend": tts_backend,
            "tts_executable_path": tts_executable_path,
            "say_path": tts_executable_path,
        }
        context = batch_context or RenderBatchContext(manifest=manifest_payload, media={"audio": audio_payload})
        context = context.merge_manifest(manifest_payload).merge_media("audio", audio_payload)
        self.batch_context = context
        self._active_context = cfg.get_runtime_context(None)
        self.voice_overrides = resolved_voice_overrides

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
                batch_context=self.batch_context,
                media_result_factory=self.media_result_factory,
                audio_stop_event=self.audio_stop_event,
                progress_tracker=self.progress_tracker,
                audio_generator=self._audio_callable,
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
