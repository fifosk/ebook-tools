from __future__ import annotations

from typing import Any, Dict, List

from pydub import AudioSegment

from modules.render.backends.polly import PollyAudioSynthesizer, _normalize_api_voice


class _DummyAudioClient:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def synthesize(
        self,
        *,
        text: str,
        voice: str | None = None,
        speed: int | None = None,
        language: str,
    ) -> AudioSegment:
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "speed": speed,
                "language": language,
            }
        )
        return AudioSegment.silent(duration=1000)


def test_normalize_api_voice_handles_auto_identifiers() -> None:
    assert _normalize_api_voice(None) is None
    assert _normalize_api_voice("", language="en") is None
    assert _normalize_api_voice("macOS-auto", language="en") == "0"
    assert _normalize_api_voice("macOS-auto-male", language="en") == "0"
    assert _normalize_api_voice("macOS-auto", language="ar") is None
    assert _normalize_api_voice("macOS-auto-male", language="ar") is None
    assert _normalize_api_voice("gTTS", language="en") is None
    assert _normalize_api_voice("Alloy", language="en") == "Alloy"


def test_polly_synthesizer_omits_auto_voice_for_non_english_segments() -> None:
    client = _DummyAudioClient()
    synthesizer = PollyAudioSynthesizer(audio_client=client)

    audio = synthesizer.synthesize_sentence(
        sentence_number=1,
        input_sentence="Hello",
        fluent_translation="مرحبا بالعالم",
        input_language="en",
        target_language="ar",
        audio_mode="1",
        total_sentences=1,
        language_codes={"en": "en", "ar": "ar"},
        selected_voice="macOS-auto-male",
        tempo=1.0,
        macos_reading_speed=200,
    )

    assert isinstance(audio, AudioSegment)
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["language"] == "ar"
    assert call["voice"] is None
    assert call["text"] == "مرحبا بالعالم"


def test_polly_synthesizer_passes_explicit_voice_to_api() -> None:
    client = _DummyAudioClient()
    synthesizer = PollyAudioSynthesizer(audio_client=client)

    synthesizer.synthesize_sentence(
        sentence_number=1,
        input_sentence="Hello",
        fluent_translation="Hola mundo",
        input_language="en",
        target_language="es",
        audio_mode="1",
        total_sentences=1,
        language_codes={"en": "en", "es": "es"},
        selected_voice="alloy",
        tempo=1.0,
        macos_reading_speed=200,
    )

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["language"] == "es"
    assert call["voice"] == "alloy"
    assert call["text"] == "Hola mundo"


def test_polly_synthesizer_uses_api_default_for_english_auto_voice() -> None:
    client = _DummyAudioClient()
    synthesizer = PollyAudioSynthesizer(audio_client=client)

    synthesizer.synthesize_sentence(
        sentence_number=1,
        input_sentence="مرحبا",  # ignored in audio_mode 1
        fluent_translation="Hello world",
        input_language="ar",
        target_language="en",
        audio_mode="1",
        total_sentences=1,
        language_codes={"en": "en", "ar": "ar"},
        selected_voice="macOS-auto-female",
        tempo=1.0,
        macos_reading_speed=180,
    )

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["language"] == "en"
    assert call["voice"] == "0"
    assert call["text"] == "Hello world"
