from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from modules.services.job_manager import PipelineJob, PipelineJobStatus
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_pipeline_service,
    get_request_user,
)


pytestmark = pytest.mark.webapi


class _RecordingPipelineService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None, str | None]] = []

    def _record(self, action: str, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        self.calls.append((action, job_id, user_id, user_role))
        return PipelineJob(
            job_id=job_id,
            status=PipelineJobStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
        )

    def pause_job(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        return self._record("pause", job_id, user_id=user_id, user_role=user_role)

    def resume_job(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        return self._record("resume", job_id, user_id=user_id, user_role=user_role)

    def cancel_job(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        return self._record("cancel", job_id, user_id=user_id, user_role=user_role)

    def delete_job(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        return self._record("delete", job_id, user_id=user_id, user_role=user_role)

    def restart_job(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        return self._record("restart", job_id, user_id=user_id, user_role=user_role)


class _RestartValueErrorPipelineService:
    def restart_job(self, job_id: str, *, user_id=None, user_role=None):
        raise ValueError("Restart is not supported for job type 'youtube_dub'")


def test_job_action_routes_normalize_route_job_id() -> None:
    app = create_app()
    service = _RecordingPipelineService()
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            responses = {
                action: client.post(f"/api/pipelines/jobs/%20%20job-1%20%20/{action}")
                for action in ("pause", "resume", "cancel", "delete", "restart")
            }
    finally:
        app.dependency_overrides.clear()

    assert {action: response.status_code for action, response in responses.items()} == {
        "pause": 200,
        "resume": 200,
        "cancel": 200,
        "delete": 200,
        "restart": 200,
    }
    assert all(response.json()["job"]["job_id"] == "job-1" for response in responses.values())
    assert service.calls == [
        ("pause", "job-1", "alice", "editor"),
        ("resume", "job-1", "alice", "editor"),
        ("cancel", "job-1", "alice", "editor"),
        ("delete", "job-1", "alice", "editor"),
        ("restart", "job-1", "alice", "editor"),
    ]


def test_job_action_routes_reject_blank_job_id_without_service_lookup() -> None:
    app = create_app()
    service = _RecordingPipelineService()
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/pipelines/jobs/%20%20%20/restart")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    assert service.calls == []


def test_restart_job_action_value_error_returns_client_error() -> None:
    app = create_app()
    app.dependency_overrides[get_pipeline_service] = lambda: _RestartValueErrorPipelineService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/pipelines/jobs/job-1/restart")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Restart is not supported for job type 'youtube_dub'"
    }
