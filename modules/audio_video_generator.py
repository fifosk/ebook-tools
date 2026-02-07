"""Utilities for generating audio artifacts."""

import threading
import time
import warnings
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

from pydub import AudioSegment

from modules.audio.backends import get_default_backend_name
from modules.render import MediaBatchOrchestrator, RenderBatchContext
from modules.render.audio_pipeline import audio_worker_body
from modules.render.backends import (
    AudioSynthesizer,
    get_audio_synthesizer,
)
from modules.render.backends.base import SynthesisResult
from modules.translation_engine import TranslationTask

DEFAULT_TTS_BACKEND = get_default_backend_name()

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker

@dataclass(slots=True)
class MediaPipelineResult:
    """Result produced by the media generation workers."""

    index: int
    sentence_number: int
    sentence: str
    target_language: str
    translation: str
    transliteration: str
    audio_segment: Optional[AudioSegment]
    audio_tracks: Optional[Mapping[str, AudioSegment]] = None
    voice_metadata: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def audio(self) -> Optional[AudioSegment]:
        """Backward-compatible accessor returning the synthesized audio segment."""

        return self.audio_segment
# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------


def change_audio_tempo(sound: AudioSegment, tempo: float = 1.0) -> AudioSegment:
    """Adjust the tempo of an ``AudioSegment`` by modifying its frame rate."""

    if tempo == 1.0:
        return sound
    new_frame_rate = int(sound.frame_rate * tempo)
    return sound._spawn(sound.raw_data, overrides={"frame_rate": new_frame_rate}).set_frame_rate(
        sound.frame_rate
    )


def generate_audio_for_sentence(
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
    voice_overrides: Mapping[str, str] | None = None,
    tts_backend: str = DEFAULT_TTS_BACKEND,
    tts_executable_path: Optional[str] = None,
    *,
    audio_synthesizer: AudioSynthesizer | None = None,
    progress_tracker: Optional["ProgressTracker"] = None,
) -> SynthesisResult:
    """Generate audio for a sentence using the configured synthesizer."""

    if audio_synthesizer is None:
        _warn_legacy_audio_usage("generate_audio_for_sentence")
    synthesizer = audio_synthesizer or get_audio_synthesizer()
    return synthesizer.synthesize_sentence(
        sentence_number=sentence_number,
        input_sentence=input_sentence,
        fluent_translation=fluent_translation,
        input_language=input_language,
        target_language=target_language,
        audio_mode=audio_mode,
        total_sentences=total_sentences,
        language_codes=language_codes,
        selected_voice=selected_voice,
        voice_overrides=voice_overrides,
        tempo=tempo,
        macos_reading_speed=macos_reading_speed,
        tts_backend=tts_backend,
        tts_executable_path=tts_executable_path,
        progress_tracker=progress_tracker,
    )


def _media_worker(
    name: str,
    task_queue: Queue[Optional[TranslationTask]],
    result_queue: Queue[Optional[MediaPipelineResult]],
    *,
    total_sentences: int,
    input_language: str,
    audio_mode: str,
    language_codes: Mapping[str, str],
    selected_voice: str,
    tempo: float,
    macos_reading_speed: int,
    voice_overrides: Mapping[str, str] | None = None,
    generate_audio: bool,
    stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
    audio_synthesizer: AudioSynthesizer | None = None,
) -> None:
    """Delegate media processing to the shared :class:`AudioWorker`."""

    synthesizer = audio_synthesizer or get_audio_synthesizer()
    batch_context = RenderBatchContext(
        manifest={
            "total_sentences": total_sentences,
            "input_language": input_language,
            "audio_mode": audio_mode,
            "selected_voice": selected_voice,
            "voice_overrides": dict(voice_overrides or {}),
            "tempo": tempo,
            "macos_reading_speed": macos_reading_speed,
            "generate_audio": generate_audio,
        },
        media={
            "audio": {
                "total_sentences": total_sentences,
                "input_language": input_language,
                "audio_mode": audio_mode,
                "language_codes": dict(language_codes),
                "selected_voice": selected_voice,
                "voice_overrides": dict(voice_overrides or {}),
                "tempo": tempo,
                "macos_reading_speed": macos_reading_speed,
                "generate_audio": generate_audio,
            }
        },
    )
    audio_worker_body(
        name,
        task_queue,
        result_queue,
        batch_context=batch_context,
        media_result_factory=MediaPipelineResult,
        audio_stop_event=stop_event,
        progress_tracker=progress_tracker,
        audio_generator=synthesizer.synthesize_sentence,
    )


def start_media_pipeline(
    task_queue: Queue[Optional[TranslationTask]],
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
    queue_size: Optional[int] = None,
    stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
    audio_synthesizer: AudioSynthesizer | None = None,
    tts_backend: str = DEFAULT_TTS_BACKEND,
    tts_executable_path: Optional[str] = None,
) -> Tuple[Queue[Optional[MediaPipelineResult]], List[threading.Thread]]:
    """Start consumer threads that transform translations into media artifacts."""

    if audio_synthesizer is None:
        _warn_legacy_audio_usage("start_media_pipeline")

    orchestrator = MediaBatchOrchestrator(
        task_queue,
        worker_count=worker_count,
        total_sentences=total_sentences,
        input_language=input_language,
        audio_mode=audio_mode,
        language_codes=language_codes,
        selected_voice=selected_voice,
        voice_overrides=voice_overrides,
        tempo=tempo,
        macos_reading_speed=macos_reading_speed,
        generate_audio=generate_audio,
        queue_size=queue_size,
        audio_stop_event=stop_event,
        progress_tracker=progress_tracker,
        audio_synthesizer=audio_synthesizer,
        media_result_factory=MediaPipelineResult,
        tts_backend=tts_backend,
        tts_executable_path=tts_executable_path,
    )
    return orchestrator.start()


__all__ = [
    "change_audio_tempo",
    "generate_audio_for_sentence",
]


def _warn_legacy_audio_usage(entry_point: str) -> None:
    warnings.warn(
        (
            f"{entry_point} is deprecated; construct an AudioSynthesizer via "
            "modules.render.backends.get_audio_synthesizer() and call it directly."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
