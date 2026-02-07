from typing import Optional

import pytest
from pydub import AudioSegment

from modules.media.exceptions import MediaBackendError
from modules.render.backends.polly import PollyAudioSynthesizer


class _StubAudioClient:
    def __init__(self, *, error: Optional[Exception] = None):
        self.calls = []
        self._error = error

    def synthesize(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        segment = AudioSegment.silent(duration=10)
        if kwargs.get("return_metadata"):
            return segment, {}
        return segment


@pytest.fixture(autouse=True)
def _stub_thread_count(monkeypatch):
    monkeypatch.setattr("modules.render.backends.polly.cfg.get_thread_count", lambda: 1)


@pytest.fixture
def synthesizer(monkeypatch):
    metrics = []
    monkeypatch.setattr(
        "modules.render.backends.polly.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )
    client = _StubAudioClient()
    synth = PollyAudioSynthesizer(audio_client=client)
    return synth, client, metrics


def _synthesize_sentence(synth):
    return synth.synthesize_sentence(
        sentence_number=1,
        input_sentence="Hello",
        fluent_translation="Bonjour",
        input_language="English",
        target_language="French",
        audio_mode="5",
        total_sentences=1,
        language_codes={"English": "en", "French": "fr"},
        selected_voice="test",
        voice_overrides=None,
        tempo=1.0,
        macos_reading_speed=180,
    )


def test_polly_synthesizer_uses_audio_api_client(synthesizer):
    synth, client, metrics = synthesizer

    result = _synthesize_sentence(synth)

    assert len(result.audio) > 0
    assert client.calls, "Audio API client should be invoked"
    assert metrics, "Telemetry metric should be recorded"
    metric_name, attributes = metrics[-1]
    assert metric_name == "audio.api.synthesize.duration"
    assert attributes["status"] == "success"


def test_polly_synthesizer_falls_back_on_media_backend_error(monkeypatch):
    metrics = []
    monkeypatch.setattr(
        "modules.render.backends.polly.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )

    fallback_calls = []

    def _fake_generate_audio(text, lang_code, voice, speed, config, **kwargs):
        fallback_calls.append((text, lang_code, voice, speed, config))
        return AudioSegment.silent(duration=12)

    monkeypatch.setattr(
        "modules.render.backends.polly.generate_audio", _fake_generate_audio
    )

    error = MediaBackendError("boom")
    client = _StubAudioClient(error=error)
    synth = PollyAudioSynthesizer(audio_client=client)

    result = _synthesize_sentence(synth)

    assert len(result.audio) > 0, "Synthesizer should fall back to legacy backend"
    assert client.calls, "Audio API client should be invoked"
    assert fallback_calls, "Legacy backend should be used after API failure"
    assert metrics, "Telemetry metric should be recorded"
    metric_name, attributes = metrics[-1]
    assert metric_name == "audio.api.synthesize.duration"
    assert attributes["status"] == "error"


def test_polly_synthesizer_builds_client_from_environment(monkeypatch):
    metrics = []
    monkeypatch.setattr(
        "modules.render.backends.polly.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )
    monkeypatch.setenv("EBOOK_AUDIO_API_BASE_URL", "https://audio.example")
    monkeypatch.setenv("EBOOK_AUDIO_API_TIMEOUT_SECONDS", "120")

    created: dict[str, tuple[str, float]] = {}

    class _FakeClient:
        def __init__(self, base_url, timeout):
            created["args"] = (base_url, timeout)

        def synthesize(self, **kwargs):
            segment = AudioSegment.silent(duration=20)
            if kwargs.get("return_metadata"):
                return segment, {}
            return segment

    monkeypatch.setattr(
        "modules.integrations.audio_client.AudioAPIClient", _FakeClient
    )

    synth = PollyAudioSynthesizer()
    result = _synthesize_sentence(synth)

    assert len(result.audio) > 0
    assert created["args"] == ("https://audio.example", 120.0)
    assert metrics, "Expected API metrics when using the HTTP client"
