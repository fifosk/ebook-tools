from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from modules.media.exceptions import MediaBackendError
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_audio_service


@dataclass
class _StubSegment:
    payload: bytes

    def export(self, buffer, format: str = "mp3"):
        buffer.write(self.payload)
        return buffer


@dataclass
class _RecordingAudioService:
    segment: _StubSegment
    calls: list[dict[str, object]] = field(default_factory=list)

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: str | None = None,
    ) -> _StubSegment:
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "speed": speed,
                "lang_code": lang_code,
                "output_path": output_path,
            }
        )
        return self.segment


class _FailingAudioService:
    def synthesize(self, **_: object) -> None:
        raise MediaBackendError("Backend offline")


@pytest.fixture(autouse=True)
def _mock_audio_config(monkeypatch):
    def _load_configuration(verbose: bool = False):  # noqa: ARG001 - required signature
        return {
            "selected_voice": "Config Voice",
            "macos_reading_speed": 180,
            "input_language": "English",
            "language_codes": {"English": "en"},
        }

    monkeypatch.setattr(
        "modules.webapi.audio_routes.cfg.load_configuration",
        _load_configuration,
    )
    yield


def test_synthesize_audio_streams_bytes():
    app = create_app()
    service = _RecordingAudioService(_StubSegment(b"fake-mp3"))
    app.dependency_overrides[get_audio_service] = lambda: service

    response = None
    try:
        with TestClient(app) as client:
            response = client.post("/api/audio", json={"text": " Hello world "})
    finally:
        app.dependency_overrides.clear()

    assert response is not None
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.content == b"fake-mp3"
    assert service.calls == [
        {
            "text": "Hello world",
            "voice": "Config Voice",
            "speed": 180,
            "lang_code": "en",
            "output_path": None,
        }
    ]


def test_synthesize_audio_rejects_blank_text():
    app = create_app()

    response = None
    try:
        with TestClient(app) as client:
            response = client.post("/api/audio", json={"text": "   "})
    finally:
        app.dependency_overrides.clear()

    assert response is not None
    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert detail["msg"] == "Text must not be empty."


def test_synthesize_audio_handles_backend_failure():
    app = create_app()
    app.dependency_overrides[get_audio_service] = lambda: _FailingAudioService()

    response = None
    try:
        with TestClient(app) as client:
            response = client.post("/api/audio", json={"text": "Hello"})
    finally:
        app.dependency_overrides.clear()

    assert response is not None
    assert response.status_code == 502
    payload = response.json()
    assert payload["error"] == "synthesis_failed"
    assert "Backend offline" in payload["message"]
