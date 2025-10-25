"""Thread orchestration utilities for media rendering."""

from __future__ import annotations

import threading
from queue import Queue
from typing import TYPE_CHECKING, Callable, Mapping, Optional, Sequence, Tuple, Type

from modules import config_manager as cfg

from .audio_pipeline import AudioGenerator, AudioWorker

if TYPE_CHECKING:  # pragma: no cover - imports used for static analysis only
    from modules.progress_tracker import ProgressTracker
    from modules.translation_engine import TranslationTask
    from modules.audio_video_generator import MediaPipelineResult


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


__all__ = ["MediaBatchOrchestrator"]
