from __future__ import annotations

from typing import Any, Dict, Iterator, Mapping, Tuple

import pytest
from fastapi.testclient import TestClient
from pydub import AudioSegment

from modules.media.exceptions import MediaBackendError
from modules.services.file_locator import FileLocator
from modules.services.video_service import VideoTaskSnapshot
from modules.user_management import AuthService
from modules.user_management.local_user_store import LocalUserStore
from modules.user_management.session_manager import SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_audio_service,
    get_auth_service,
    get_file_locator,
    get_video_service,
)


class _StubAudioService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.should_fail = False

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: str | None = None,
    ) -> AudioSegment:
        if self.should_fail:
            raise MediaBackendError("backend-failure")
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "speed": speed,
                "lang_code": lang_code,
                "output_path": output_path,
            }
        )
        return AudioSegment.silent(duration=50)


class _StubVideoService:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []
        self.status = "queued"

    def enqueue(
        self,
        job_id: str,
        parameters: Mapping[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> VideoTaskSnapshot:
        request_id = f"video-request-{len(self.calls) + 1}"
        self.calls.append(
            {
                "job_id": job_id,
                "parameters": dict(parameters),
                "correlation_id": correlation_id,
            }
        )
        return VideoTaskSnapshot(
            request_id=request_id,
            job_id=job_id,
            status=self.status,
            output_path=None,
            logs_path=None,
            logs_url=None,
            error=None,
        )


@pytest.fixture
def media_client(tmp_path) -> Iterator[Tuple[TestClient, str, str, _StubAudioService, _StubVideoService, FileLocator]]:
    user_store_path = tmp_path / "users.json"
    session_file = tmp_path / "sessions.json"
    job_storage = tmp_path / "storage"

    service = AuthService(
        LocalUserStore(storage_path=user_store_path),
        SessionManager(session_file=session_file),
    )

    service.user_store.create_user("viewer", "secret", roles=["viewer"])
    service.user_store.create_user("producer", "secret", roles=["media_producer"])

    viewer_token = service.session_manager.create_session("viewer")
    producer_token = service.session_manager.create_session("producer")

    locator = FileLocator(storage_dir=job_storage)
    audio_service = _StubAudioService()
    video_service = _StubVideoService()

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: service
    app.dependency_overrides[get_audio_service] = lambda: audio_service
    app.dependency_overrides[get_video_service] = lambda: video_service
    app.dependency_overrides[get_file_locator] = lambda: locator

    with TestClient(app) as client:
        yield client, viewer_token, producer_token, audio_service, video_service, locator

    app.dependency_overrides.clear()


def test_media_generation_requires_authentication(media_client) -> None:
    client, *_ = media_client

    response = client.post(
        "/api/media/generate",
        json={
            "job_id": "job-1",
            "media_type": "audio",
            "audio": {"request": {"text": "sample"}},
        },
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"] == "missing_token"


def test_media_generation_requires_elevated_role(media_client) -> None:
    client, viewer_token, *_ = media_client

    response = client.post(
        "/api/media/generate",
        json={
            "job_id": "job-1",
            "media_type": "audio",
            "audio": {"request": {"text": "sample"}},
        },
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"] == "insufficient_permissions"


def test_audio_generation_creates_artifact(media_client) -> None:
    client, _, producer_token, audio_service, _, locator = media_client

    response = client.post(
        "/api/media/generate",
        json={
            "job_id": "job-123",
            "media_type": "audio",
            "audio": {
                "request": {
                    "text": "Hello there",
                    "voice": "SampleVoice",
                    "speed": 180,
                    "language": "en",
                },
                "output_filename": "greeting.mp3",
                "correlation_id": "corr-audio",
            },
        },
        headers={"Authorization": f"Bearer {producer_token}"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["media_type"] == "audio"
    assert payload["requested_by"] == "producer"
    assert payload["artifact_path"].endswith("greeting.mp3")
    artifact_path = payload["artifact_path"]
    stored_file = locator.resolve_path("job-123", artifact_path)
    assert stored_file.exists()

    params = payload["parameters"]
    assert params["voice"] == "SampleVoice"
    assert params["speed"] == 180
    assert params["language"] == "en"
    assert audio_service.calls
    assert payload["correlation_id"] == "corr-audio"


def test_audio_generation_reports_backend_failure(media_client) -> None:
    client, _, producer_token, audio_service, _, _ = media_client
    audio_service.should_fail = True

    response = client.post(
        "/api/media/generate",
        json={
            "job_id": "job-500",
            "media_type": "audio",
            "audio": {"request": {"text": "Failure expected"}},
        },
        headers={"Authorization": f"Bearer {producer_token}"},
    )

    assert response.status_code == 502
    payload = response.json()
    assert payload["error"] == "synthesis_failed"


def test_video_generation_submits_job(media_client) -> None:
    client, _, producer_token, _, video_service, locator = media_client

    job_id = "job-555"
    job_dir = locator.resolve_path(job_id)
    audio_dir = job_dir / "media" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_file = audio_dir / "clip.mp3"
    audio_file.write_bytes(b"fake")

    response = client.post(
        "/api/media/generate",
        json={
            "job_id": job_id,
            "media_type": "video",
            "video": {
                "request": {
                    "slides": ["Slide 1"],
                    "audio": [{"relative_path": "media/audio/clip.mp3"}],
                    "options": {"book_author": "Author"},
                },
            },
        },
        headers={"Authorization": f"Bearer {producer_token}"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == video_service.status
    assert payload["media_type"] == "video"
    assert payload["request_id"] == "video-request-1"
    assert payload["parameters"]["audio"][0]["job_id"] == job_id
    assert video_service.calls
