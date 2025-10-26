"""Worker implementations for media rendering pipelines."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Empty, Full, Queue
from typing import Callable, Mapping, Optional, Protocol, TYPE_CHECKING

from pydub import AudioSegment

from modules import logging_manager as log_mgr
from .context import RenderBatchContext

if TYPE_CHECKING:  # pragma: no cover - imports for static analysis only
    from modules.progress_tracker import ProgressTracker
    from modules.translation_engine import TranslationTask
    from modules.audio_video_generator import MediaPipelineResult

logger = log_mgr.logger


class AudioGenerator(Protocol):
    """Callable protocol used to synthesize audio for a translation task."""

    def __call__(
        self,
        sentence_number: int,
        input_sentence: str,
        fluent_translation: str,
        input_language: str,
        target_language: str,
        audio_mode: str,
        total_sentences: int,
        language_codes: Mapping[str, str],
        selected_voice: str,
        tempo: float,
        macos_reading_speed: int,
    ) -> AudioSegment:
        """Render audio for a single translated sentence."""


class MediaResultFactory(Protocol):
    """Protocol describing the factory used to build media worker outputs."""

    def __call__(
        self,
        *,
        index: int,
        sentence_number: int,
        sentence: str,
        target_language: str,
        translation: str,
        transliteration: str,
        audio_segment: Optional[AudioSegment],
    ) -> "MediaPipelineResult":
        """Return a media result instance."""


@dataclass(slots=True)
class AudioWorker:
    """Wrap the audio worker coroutine so it can be reused and extended."""

    name: str
    audio_task_queue: "Queue[Optional[TranslationTask]]"
    audio_result_queue: "Queue[Optional[MediaPipelineResult]]"
    batch_context: RenderBatchContext
    media_result_factory: MediaResultFactory
    audio_stop_event: Optional[threading.Event] = None
    progress_tracker: Optional["ProgressTracker"] = None
    audio_generator: Optional[AudioGenerator] = None

    def run(self) -> None:
        """Execute the wrapped audio worker coroutine."""

        audio_worker_body(
            self.name,
            self.audio_task_queue,
            self.audio_result_queue,
            batch_context=self.batch_context,
            media_result_factory=self.media_result_factory,
            audio_stop_event=self.audio_stop_event,
            progress_tracker=self.progress_tracker,
            audio_generator=self.audio_generator,
        )


@dataclass(slots=True)
class _SimpleWorker:
    """Utility wrapper that exposes a ``run`` method for simple callables."""

    name: str
    worker_fn: Callable[..., None]

    def run(self, *args, **kwargs) -> None:
        self.worker_fn(*args, **kwargs)


class VideoWorker(_SimpleWorker):
    """Wrapper for video worker coroutines."""


class TextWorker(_SimpleWorker):
    """Wrapper for text worker coroutines."""


def audio_worker_body(
    worker_name: str,
    audio_task_queue: "Queue[Optional[TranslationTask]]",
    audio_result_queue: "Queue[Optional[MediaPipelineResult]]",
    *,
    batch_context: RenderBatchContext,
    media_result_factory: MediaResultFactory,
    audio_stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
    audio_generator: Optional[AudioGenerator] = None,
) -> None:
    """Consume translation results and emit completed media payloads."""

    manifest_context = batch_context.manifest
    audio_context = batch_context.media_context("audio")

    total_sentences = int(
        audio_context.get("total_sentences")
        or manifest_context.get("total_sentences")
        or 0
    )
    input_language = str(
        audio_context.get("input_language")
        or manifest_context.get("input_language")
        or ""
    )
    audio_mode = str(audio_context.get("audio_mode") or manifest_context.get("audio_mode") or "1")
    raw_language_codes = audio_context.get("language_codes") or manifest_context.get("language_codes") or {}
    if not isinstance(raw_language_codes, Mapping):
        raw_language_codes = {}
    language_codes = dict(raw_language_codes)
    selected_voice = str(
        audio_context.get("selected_voice")
        or manifest_context.get("selected_voice")
        or ""
    )
    tempo = float(audio_context.get("tempo") or manifest_context.get("tempo") or 1.0)
    macos_reading_speed = int(
        audio_context.get("macos_reading_speed")
        or manifest_context.get("macos_reading_speed")
        or 0
    )
    generate_audio = bool(
        audio_context.get("generate_audio", manifest_context.get("generate_audio", True))
    )
    raw_tts_backend = audio_context.get("tts_backend") or manifest_context.get("tts_backend")
    if isinstance(raw_tts_backend, str):
        tts_backend = raw_tts_backend.strip() or "auto"
    else:
        tts_backend = "auto"
    raw_tts_executable = (
        audio_context.get("tts_executable_path")
        or manifest_context.get("tts_executable_path")
    )
    if isinstance(raw_tts_executable, str):
        stripped_executable = raw_tts_executable.strip()
        tts_executable_path = stripped_executable or None
    else:
        tts_executable_path = None

    while True:
        if audio_stop_event and audio_stop_event.is_set():
            break
        try:
            translation_task = audio_task_queue.get(timeout=0.1)
        except Empty:
            continue
        if translation_task is None:
            audio_task_queue.task_done()
            break

        start_time = time.perf_counter()
        audio_segment: Optional[AudioSegment] = None
        try:
            if generate_audio and audio_generator is not None:
                audio_segment = audio_generator(
                    translation_task.sentence_number,
                    translation_task.sentence,
                    translation_task.translation,
                    input_language,
                    translation_task.target_language,
                    audio_mode,
                    total_sentences,
                    language_codes,
                    selected_voice,
                    tempo,
                    macos_reading_speed,
                    tts_backend=tts_backend,
                    tts_executable_path=tts_executable_path,
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Consumer %s failed for sentence %s: %s",
                worker_name,
                translation_task.sentence_number,
                exc,
            )
            if generate_audio:
                audio_segment = AudioSegment.silent(duration=0)
        finally:
            audio_task_queue.task_done()

        elapsed = time.perf_counter() - start_time
        logger.debug(
            "Consumer %s processed sentence %s in %.3fs",
            worker_name,
            translation_task.sentence_number,
            elapsed,
        )

        payload = media_result_factory(
            index=translation_task.index,
            sentence_number=translation_task.sentence_number,
            sentence=translation_task.sentence,
            target_language=translation_task.target_language,
            translation=translation_task.translation,
            transliteration=translation_task.transliteration,
            audio_segment=audio_segment,
        )

        while True:
            if audio_stop_event and audio_stop_event.is_set():
                break
            try:
                audio_result_queue.put(payload, timeout=0.1)
                break
            except Full:
                continue


__all__ = [
    "AudioWorker",
    "VideoWorker",
    "TextWorker",
    "audio_worker_body",
]
