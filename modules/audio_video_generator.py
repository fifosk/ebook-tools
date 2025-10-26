"""Utilities for generating audio and video artifacts."""

import os
import threading
import time
import warnings
from dataclasses import dataclass
from queue import Queue
from typing import List, Mapping, Optional, Sequence, Tuple, TYPE_CHECKING

from pydub import AudioSegment
from PIL import Image

from modules import output_formatter
from modules.audio.backends import get_default_backend_name
from modules.render import AudioWorker, MediaBatchOrchestrator
from modules.render.backends import (
    AudioSynthesizer,
    VideoRenderer,
    get_audio_synthesizer,
)
from modules.video.api import VideoService
from modules.translation_engine import TranslationTask
from modules.video.backends import VideoRenderOptions

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
    tts_backend: str = DEFAULT_TTS_BACKEND,
    tts_executable_path: Optional[str] = None,
    *,
    audio_synthesizer: AudioSynthesizer | None = None,
) -> AudioSegment:
    """Generate audio for a sentence using the configured synthesizer."""

    if audio_synthesizer is None:
        _warn_legacy_audio_usage("generate_audio_for_sentence")
    synthesizer = audio_synthesizer or get_audio_synthesizer()
    return synthesizer.synthesize_sentence(
        sentence_number,
        input_sentence,
        fluent_translation,
        input_language,
        target_language,
        audio_mode,
        total_sentences,
        language_codes,
        selected_voice,
        tempo,
        macos_reading_speed,
        tts_backend=tts_backend,
        tts_executable_path=tts_executable_path,
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
    generate_audio: bool,
    stop_event: Optional[threading.Event] = None,
    progress_tracker: Optional["ProgressTracker"] = None,
    audio_synthesizer: AudioSynthesizer | None = None,
) -> None:
    """Delegate media processing to the shared :class:`AudioWorker`."""

    synthesizer = audio_synthesizer or get_audio_synthesizer()
    worker = AudioWorker(
        name,
        task_queue,
        result_queue,
        total_sentences=total_sentences,
        input_language=input_language,
        audio_mode=audio_mode,
        language_codes=language_codes,
        selected_voice=selected_voice,
        tempo=tempo,
        macos_reading_speed=macos_reading_speed,
        generate_audio=generate_audio,
        audio_stop_event=stop_event,
        progress_tracker=progress_tracker,
        audio_generator=synthesizer.synthesize_sentence,
        media_result_factory=MediaPipelineResult,
    )
    worker.run()


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


def render_video_slides(
    text_blocks: Sequence[str],
    audio_segments: Sequence[AudioSegment],
    output_dir: str,
    batch_start: int,
    batch_end: int,
    base_no_ext: str,
    cover_img: Optional[Image.Image],
    book_author: str,
    book_title: str,
    cumulative_word_counts: Sequence[int],
    total_word_count: int,
    macos_reading_speed: int,
    input_language: str,
    total_sentences: int,
    tempo: float,
    sync_ratio: float,
    word_highlighting: bool,
    highlight_granularity: str,
    voice_name: str = "",
    slide_render_options: Optional[object] = None,
    cleanup: bool = True,
    slide_size: Sequence[int] = (1280, 720),
    initial_font_size: int = 60,
    bg_color: Optional[Sequence[int]] = None,
    template_name: Optional[str] = None,
    *,
    video_renderer: VideoRenderer | None = None,
    video_service: VideoService | None = None,
) -> str:
    """Render video slides using the configured renderer backend."""

    if video_renderer is None:
        _warn_legacy_video_usage("render_video_slides")
    range_fragment = output_formatter.format_sentence_range(
        batch_start, batch_end, total_sentences
    )
    output_path = os.path.join(output_dir, f"{range_fragment}_{base_no_ext}.mp4")
    options = VideoRenderOptions(
        batch_start=batch_start,
        batch_end=batch_end,
        cover_image=cover_img,
        book_author=book_author,
        book_title=book_title,
        cumulative_word_counts=cumulative_word_counts,
        total_word_count=total_word_count,
        macos_reading_speed=macos_reading_speed,
        input_language=input_language,
        total_sentences=total_sentences,
        tempo=tempo,
        sync_ratio=sync_ratio,
        word_highlighting=word_highlighting,
        highlight_granularity=highlight_granularity,
        voice_name=voice_name,
        slide_render_options=slide_render_options,
        cleanup=cleanup,
        slide_size=slide_size,
        initial_font_size=initial_font_size,
        bg_color=bg_color,
        template_name=template_name,
    )

    if video_renderer is not None:
        return video_renderer.render_slides(
            text_blocks, audio_segments, output_path, options
        )

    service = video_service or VideoService()
    return service.render(text_blocks, audio_segments, output_path, options)


def generate_video_slides_ffmpeg(
    text_blocks: Sequence[str],
    audio_segments: Sequence[AudioSegment],
    output_dir: str,
    batch_start: int,
    batch_end: int,
    base_no_ext: str,
    cover_img: Optional[Image.Image],
    book_author: str,
    book_title: str,
    cumulative_word_counts: Sequence[int],
    total_word_count: int,
    macos_reading_speed: int,
    input_language: str,
    total_sentences: int,
    tempo: float,
    sync_ratio: float,
    word_highlighting: bool,
    highlight_granularity: str,
    voice_name: str = "",
    slide_render_options: Optional[object] = None,
    cleanup: bool = True,
    slide_size: Sequence[int] = (1280, 720),
    initial_font_size: int = 60,
    bg_color: Optional[Sequence[int]] = None,
    template_name: Optional[str] = None,
    *,
    video_renderer: VideoRenderer | None = None,
) -> str:
    """Backward-compatible wrapper around :func:`render_video_slides`."""

    return render_video_slides(
        text_blocks,
        audio_segments,
        output_dir,
        batch_start,
        batch_end,
        base_no_ext,
        cover_img,
        book_author,
        book_title,
        cumulative_word_counts,
        total_word_count,
        macos_reading_speed,
        input_language,
        total_sentences,
        tempo,
        sync_ratio,
        word_highlighting,
        highlight_granularity,
        voice_name=voice_name,
        slide_render_options=slide_render_options,
        cleanup=cleanup,
        slide_size=slide_size,
        initial_font_size=initial_font_size,
        bg_color=bg_color,
        template_name=template_name,
        video_renderer=video_renderer,
    )


__all__ = [
    "change_audio_tempo",
    "generate_audio_for_sentence",
    "render_video_slides",
    "generate_video_slides_ffmpeg",
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


def _warn_legacy_video_usage(entry_point: str) -> None:
    warnings.warn(
        (
            f"{entry_point} is deprecated; acquire a VideoService from "
            "modules.video.api.VideoService and invoke it directly."
        ),
        DeprecationWarning,
        stacklevel=2,
    )

