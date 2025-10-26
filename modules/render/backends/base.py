"""Base protocol definitions for media rendering backends."""
from __future__ import annotations

from typing import Mapping, Optional, Protocol, Sequence, runtime_checkable

from pydub import AudioSegment

from modules.video.backends import BaseVideoRenderer as VideoRenderer


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


class GolangVideoRenderer(VideoRenderer):
    """Placeholder renderer for the Go-based implementation."""

    def render_slides(  # pragma: no cover - documentation placeholder
        self,
        slides: Sequence[str],
        audio_tracks: Sequence[AudioSegment],
        output_path: str,
        options: Optional[object] = None,
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
