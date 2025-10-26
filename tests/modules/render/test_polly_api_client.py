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
        return AudioSegment.silent(duration=10)


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
        tempo=1.0,
        macos_reading_speed=180,
    )


def test_polly_synthesizer_uses_audio_api_client(synthesizer):
    synth, client, metrics = synthesizer

    segment = _synthesize_sentence(synth)

    assert len(segment) > 0
    assert client.calls, "Audio API client should be invoked"
    assert metrics, "Telemetry metric should be recorded"
    metric_name, attributes = metrics[-1]
    assert metric_name == "audio.api.synthesize.duration"
    assert attributes["status"] == "success"


def test_polly_synthesizer_records_error_metrics(monkeypatch):
    metrics = []
    monkeypatch.setattr(
        "modules.render.backends.polly.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )
    error = MediaBackendError("boom")
    client = _StubAudioClient(error=error)
    synth = PollyAudioSynthesizer(audio_client=client)

    with pytest.raises(MediaBackendError):
        _synthesize_sentence(synth)

    assert client.calls, "Audio API client should be invoked"
    assert metrics, "Telemetry metric should be recorded"
    metric_name, attributes = metrics[-1]
    assert metric_name == "audio.api.synthesize.duration"
    assert attributes["status"] == "error"
