from __future__ import annotations

from typing import Any, Dict, Iterator, Tuple

import pytest
from fastapi.testclient import TestClient

from modules.services.video_service import VideoTaskSnapshot
from modules.user_management import AuthService
from modules.user_management.local_user_store import LocalUserStore
from modules.user_management.session_manager import SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service, get_video_service


class _StubVideoService:
    def __init__(self) -> None:
        self.enqueued: list[Dict[str, Any]] = []
        self.snapshots: dict[str, VideoTaskSnapshot] = {}

    def enqueue(
        self,
        job_id: str,
        parameters: Dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> VideoTaskSnapshot:
        request_id = f"req-{len(self.enqueued) + 1}"
        snapshot = VideoTaskSnapshot(
            request_id=request_id,
            job_id=job_id,
            status="queued",
            output_path=None,
            logs_path=None,
            logs_url=None,
            error=None,
        )
        self.enqueued.append(
            {
                "job_id": job_id,
                "parameters": dict(parameters),
                "correlation_id": correlation_id,
            }
        )
        self.snapshots[job_id] = snapshot
        return snapshot

    def get_status(self, job_id: str) -> VideoTaskSnapshot | None:
        return self.snapshots.get(job_id)

    def get_preview_path(self, job_id: str):
        raise FileNotFoundError(job_id)


@pytest.fixture
def video_client(tmp_path) -> Iterator[Tuple[TestClient, str, _StubVideoService]]:
    user_store_path = tmp_path / "users.json"
    session_file = tmp_path / "sessions.json"
    auth_service = AuthService(
        LocalUserStore(storage_path=user_store_path),
        SessionManager(session_file=session_file),
    )
    auth_service.user_store.create_user("editor", "secret", roles=["editor"])
    token = auth_service.session_manager.create_session("editor")

    video_service = _StubVideoService()

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_video_service] = lambda: video_service

    with TestClient(app) as client:
        yield client, token, video_service

    app.dependency_overrides.clear()


def test_generate_video_enqueues_task(video_client) -> None:
    client, token, service = video_client
    headers = {
        "Authorization": f"Bearer {token}",
        "x-request-id": "video-corr-1",
    }

    response = client.post(
        "/api/video/generate",
        json={
            "job_id": "job-video-1",
            "parameters": {"slides": ["Slide 1"], "audio": ["placeholder"]},
        },
        headers=headers,
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-video-1"
    assert payload["status"] == "queued"
    assert payload["request_id"] == "req-1"
    assert service.enqueued
    assert service.enqueued[0]["correlation_id"] == "video-corr-1"


def test_get_video_status_returns_snapshot(video_client) -> None:
    client, token, service = video_client
    service.snapshots["job-status"] = VideoTaskSnapshot(
        request_id="req-status",
        job_id="job-status",
        status="completed",
        output_path="media/video/output.mp4",
        logs_path="media/video/logs.txt",
        logs_url="https://example.com/logs",
        error=None,
    )

    response = client.get(
        "/api/video/status/job-status",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["output_path"] == "media/video/output.mp4"
    assert payload["logs_url"] == "https://example.com/logs"


def test_get_video_status_returns_404_for_unknown_job(video_client) -> None:
    client, token, _ = video_client

    response = client.get(
        "/api/video/status/unknown-job",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
