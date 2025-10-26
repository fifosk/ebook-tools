"""Base protocol definitions for media rendering backends."""
from __future__ import annotations

from typing import Mapping, Optional, Protocol, Sequence, runtime_checkable

from PIL import Image
from pydub import AudioSegment


@runtime_checkable
class AudioSynthesizer(Protocol):
    """Protocol describing audio synthesis backends."""

    def synthesize_sentence(
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
        *,
        tts_backend: str = "auto",
        tts_executable_path: Optional[str] = None,
    ) -> AudioSegment:
        """Render audio for a single translated sentence."""


@runtime_checkable
class VideoRenderer(Protocol):
    """Protocol describing slide/video rendering backends."""

    def render_slides(
        self,
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
        slide_render_options: Optional[object] = None,
        cleanup: bool = True,
        slide_size: Sequence[int] = (1280, 720),
        initial_font_size: int = 60,
        bg_color: Optional[Sequence[int]] = None,
        template_name: Optional[str] = None,
    ) -> str:
        """Render a batch of slides and return the resulting video path."""


class GolangVideoRenderer(VideoRenderer):
    """Placeholder renderer for the Go-based implementation."""

    def render_slides(  # pragma: no cover - documentation placeholder
        self,
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
        slide_render_options: Optional[object] = None,
        cleanup: bool = True,
        slide_size: Sequence[int] = (1280, 720),
        initial_font_size: int = 60,
        bg_color: Optional[Sequence[int]] = None,
        template_name: Optional[str] = None,
    ) -> str:
        raise NotImplementedError("Golang renderer backend has not been implemented yet")


class ExternalAudioSynthesizer(AudioSynthesizer):
    """Placeholder synthesizer for external TTS integrations."""

    def synthesize_sentence(  # pragma: no cover - documentation placeholder
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
        *,
        tts_backend: str = "auto",
        tts_executable_path: Optional[str] = None,
    ) -> AudioSegment:
        raise NotImplementedError("External audio synthesizer backend has not been implemented yet")


__all__ = [
    "AudioSynthesizer",
    "ExternalAudioSynthesizer",
    "GolangVideoRenderer",
    "VideoRenderer",
]
