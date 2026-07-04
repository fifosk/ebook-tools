from __future__ import annotations

import inspect
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from modules.services.job_manager import PipelineJob, PipelineJobStatus
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_media_metadata_service,
    get_pipeline_service,
    get_request_user,
)
from modules.webapi.routes import jobs_routes


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

    def get_job(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        return self._record("get", job_id, user_id=user_id, user_role=user_role)

    def update_job_access(
        self,
        job_id: str,
        *,
        visibility=None,
        grants=None,
        user_id=None,
        user_role=None,
    ) -> PipelineJob:
        return self._record("update_access", job_id, user_id=user_id, user_role=user_role)

    def refresh_metadata(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        return self._record("refresh_metadata", job_id, user_id=user_id, user_role=user_role)

    def enrich_metadata(
        self,
        job_id: str,
        *,
        force=False,
        user_id=None,
        user_role=None,
    ) -> tuple[PipelineJob, dict[str, object]]:
        job = self._record("enrich_metadata", job_id, user_id=user_id, user_role=user_role)
        return job, {"enriched": True, "confidence": "high", "source": "test", "metadata": {}}


class _RestartValueErrorPipelineService:
    def restart_job(self, job_id: str, *, user_id=None, user_role=None):
        raise ValueError("Restart is not supported for job type 'youtube_dub'")


class _RecordingMediaMetadataService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None, str | None]] = []

    def _record(self, action: str, job_id: str, *, user_id=None, user_role=None) -> dict[str, object]:
        self.calls.append((action, job_id, user_id, user_role))
        return {"job_id": job_id, "source_name": "book.epub"}

    def get_openlibrary_metadata(self, job_id: str, *, user_id=None, user_role=None):
        return self._record("get_book_metadata", job_id, user_id=user_id, user_role=user_role)

    def lookup_openlibrary_metadata(self, job_id: str, *, force=False, user_id=None, user_role=None):
        return self._record("lookup_book_metadata", job_id, user_id=user_id, user_role=user_role)


def test_pipeline_job_list_openapi_marks_jobs_required() -> None:
    schema = create_app().openapi()["components"]["schemas"]

    assert {"jobs"} <= set(schema["PipelineJobListResponse"]["required"])


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


def test_job_action_routes_use_shared_route_id_normalizer() -> None:
    source = inspect.getsource(jobs_routes)

    assert "from ..route_ids import normalize_route_id" in source
    assert "def _normalize_route_id" not in source
    assert "normalized_job_id = normalize_route_id(job_id)" in source


def test_job_status_and_events_normalize_route_job_id() -> None:
    app = create_app()
    service = _RecordingPipelineService()
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            status_response = client.get("/api/pipelines/%20%20job-1%20%20")
            event_response = client.get("/api/pipelines/%20%20job-1%20%20/events")
    finally:
        app.dependency_overrides.clear()

    assert status_response.status_code == 200
    assert status_response.json()["job_id"] == "job-1"
    assert event_response.status_code == 200
    assert service.calls == [
        ("get", "job-1", "alice", "editor"),
        ("get", "job-1", "alice", "editor"),
    ]


def test_job_access_and_metadata_routes_normalize_route_job_id() -> None:
    app = create_app()
    service = _RecordingPipelineService()
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            access_response = client.get("/api/pipelines/%20%20job-1%20%20/access")
            update_access_response = client.patch(
                "/api/pipelines/%20%20job-1%20%20/access",
                json={"visibility": "public"},
            )
            refresh_response = client.post("/api/pipelines/%20%20job-1%20%20/metadata/refresh")
            enrich_response = client.post(
                "/api/pipelines/%20%20job-1%20%20/metadata/enrich",
                json={"force": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert access_response.status_code == 200
    assert update_access_response.status_code == 200
    assert refresh_response.status_code == 200
    assert enrich_response.status_code == 200
    assert enrich_response.json()["job_id"] == "job-1"
    assert service.calls == [
        ("get", "job-1", "alice", "editor"),
        ("update_access", "job-1", "alice", "editor"),
        ("refresh_metadata", "job-1", "alice", "editor"),
        ("enrich_metadata", "job-1", "alice", "editor"),
    ]


def test_job_book_metadata_routes_normalize_route_job_id() -> None:
    app = create_app()
    service = _RecordingMediaMetadataService()
    app.dependency_overrides[get_media_metadata_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            metadata_response = client.get("/api/pipelines/%20%20job-1%20%20/metadata/book")
            lookup_response = client.post(
                "/api/pipelines/%20%20job-1%20%20/metadata/book/lookup",
                json={"force": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert metadata_response.status_code == 200
    assert metadata_response.json()["job_id"] == "job-1"
    assert lookup_response.status_code == 200
    assert lookup_response.json()["job_id"] == "job-1"
    assert service.calls == [
        ("get_book_metadata", "job-1", "alice", "editor"),
        ("lookup_book_metadata", "job-1", "alice", "editor"),
    ]


@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("get", "/api/pipelines/%20%20%20", None),
        ("get", "/api/pipelines/%20%20%20/events", None),
        ("get", "/api/pipelines/%20%20%20/access", None),
        ("patch", "/api/pipelines/%20%20%20/access", {"visibility": "public"}),
        ("post", "/api/pipelines/%20%20%20/metadata/refresh", None),
        ("post", "/api/pipelines/%20%20%20/metadata/enrich", {"force": True}),
        ("get", "/api/pipelines/%20%20%20/metadata/book", None),
        ("post", "/api/pipelines/%20%20%20/metadata/book/lookup", {"force": True}),
        ("post", "/api/pipelines/jobs/%20%20%20/restart", None),
    ],
)
def test_job_routes_reject_blank_job_id_without_service_lookup(
    method: str,
    path: str,
    json_payload: dict[str, object] | None,
) -> None:
    app = create_app()
    pipeline_service = _RecordingPipelineService()
    metadata_service = _RecordingMediaMetadataService()
    app.dependency_overrides[get_pipeline_service] = lambda: pipeline_service
    app.dependency_overrides[get_media_metadata_service] = lambda: metadata_service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.request(method.upper(), path, json=json_payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    assert pipeline_service.calls == []
    assert metadata_service.calls == []


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
