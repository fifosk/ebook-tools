from __future__ import annotations

from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from modules.services.resume_service import ResumeEntry
from modules.webapi.application import create_app
from modules.webapi.dependencies import RequestUserContext, get_request_user, get_resume_service

pytestmark = pytest.mark.webapi


class _StubResumeService:
    def __init__(self) -> None:
        self.list_calls: list[dict[str, object]] = []
        self.entries = [
            ResumeEntry(
                job_id="job-1",
                kind="time",
                updated_at=1_800_000_000.0,
                position=120.0,
                sentence=None,
                chunk_id=None,
                media_type="audio",
                base_id="chunk-1",
            ),
            ResumeEntry(
                job_id="job-2",
                kind="sentence",
                updated_at=1_800_000_100.0,
                position=None,
                sentence=42,
                chunk_id="chunk-2",
                media_type="text",
                base_id=None,
            ),
        ]

    def list(self, user_id: str, *, job_ids=None, limit: int = 200):
        self.list_calls.append({"user_id": user_id, "job_ids": list(job_ids or []), "limit": limit})
        if job_ids:
            allowed = set(job_ids)
            return [entry for entry in self.entries if entry.job_id in allowed]
        return list(self.entries)


def test_list_resume_positions_filters_visible_jobs_without_path_details() -> None:
    app = create_app()
    service = _StubResumeService()
    app.dependency_overrides[get_resume_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/resume", params=[("job_id", "job-2")])
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.list_calls == [{"user_id": "alice", "job_ids": ["job-2"], "limit": 200}]
    assert response.json() == {
        "entries": [
            {
                key: value
                for key, value in asdict(service.entries[1]).items()
                if key in {"job_id", "kind", "updated_at", "position", "sentence", "chunk_id", "media_type", "base_id"}
            }
        ]
    }
    rendered = response.text
    assert "alice" not in rendered
    assert "/storage" not in rendered


def test_list_resume_positions_requires_authenticated_user() -> None:
    app = create_app()
    app.dependency_overrides[get_resume_service] = lambda: _StubResumeService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role="anonymous",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/resume")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
