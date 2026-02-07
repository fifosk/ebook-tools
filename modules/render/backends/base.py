"""Base protocol definitions for media rendering backends."""
from __future__ import annotations

from typing import Mapping, Optional, Protocol, Sequence, TYPE_CHECKING, runtime_checkable

from pydub import AudioSegment

from modules.audio.backends import get_default_backend_name
from modules.audio.backends.base import SynthesisResult

if TYPE_CHECKING:  # pragma: no cover - typing only
    from modules.progress_tracker import ProgressTracker


_DEFAULT_TTS_BACKEND = get_default_backend_name()


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
        voice_overrides: Mapping[str, str] | None,
        tempo: float,
        macos_reading_speed: int,
        *,
        tts_backend: str = _DEFAULT_TTS_BACKEND,
        tts_executable_path: Optional[str] = None,
        progress_tracker: Optional["ProgressTracker"] = None,
    ) -> SynthesisResult:
        """Render audio for a single translated sentence."""


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
        voice_overrides: Mapping[str, str] | None,
        tempo: float,
        macos_reading_speed: int,
        *,
        tts_backend: str = _DEFAULT_TTS_BACKEND,
        tts_executable_path: Optional[str] = None,
        progress_tracker: Optional["ProgressTracker"] = None,
    ) -> SynthesisResult:
        raise NotImplementedError("External audio synthesizer backend has not been implemented yet")


__all__ = [
    "AudioSynthesizer",
    "ExternalAudioSynthesizer",
    "SynthesisResult",
]
