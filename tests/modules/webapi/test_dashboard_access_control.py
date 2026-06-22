from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_pipeline_service,
    get_runtime_context_provider,
)
from modules.services.job_manager.job import PipelineJob, PipelineJobStatus

import pytest

pytestmark = pytest.mark.webapi


class _StubPipelineService:
    def __init__(self) -> None:
        self.list_calls: list[dict[str, object | None]] = []
        self.count_calls: list[dict[str, object | None]] = []
        self.enqueue_calls: list[dict[str, object | None]] = []
        self.jobs: dict[str, PipelineJob] = {}
        self.total = 0

    def list_jobs(self, *, user_id=None, user_role=None, offset=None, limit=None):
        self.list_calls.append(
            {
                "user_id": user_id,
                "user_role": user_role,
                "offset": offset,
                "limit": limit,
            }
        )
        return dict(self.jobs)

    def count_jobs(self, *, user_id=None, user_role=None):
        self.count_calls.append({"user_id": user_id, "user_role": user_role})
        return self.total

    def enqueue(self, request, *, user_id=None, user_role=None):
        self.enqueue_calls.append(
            {"user_id": user_id, "user_role": user_role, "request": request}
        )
        return SimpleNamespace(
            job_id="job-123",
            status=PipelineJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            job_type="book",
        )


class _StubRuntimeContextProvider:
    def __init__(self) -> None:
        self.resolve_calls: list[dict[str, object]] = []
        self.build_calls: list[dict[str, object]] = []

    def resolve_config(self, config=None):
        payload = {"config": dict(config or {})}
        self.resolve_calls.append(payload)
        return {"resolved": True}

    def build_context(self, config, overrides=None):
        payload = {"config": config, "overrides": dict(overrides or {})}
        self.build_calls.append(payload)
        return {"context": True, "config": config, "overrides": overrides}


def test_dashboard_jobs_endpoint_passes_session_metadata() -> None:
    app = create_app()
    stub_service = _StubPipelineService()
    app.dependency_overrides[get_pipeline_service] = lambda: stub_service

    with TestClient(app) as client:
        response = client.get(
            "/pipelines/jobs",
            headers={"X-User-Id": "alice", "X-User-Role": "editor"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert stub_service.list_calls == [
        {"user_id": "alice", "user_role": "editor", "offset": None, "limit": None}
    ]
    assert stub_service.count_calls == []


def test_dashboard_jobs_endpoint_returns_paginated_job_contract() -> None:
    app = create_app()
    stub_service = _StubPipelineService()
    older = PipelineJob(
        job_id="job-older",
        job_type="pipeline",
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime(2026, 6, 22, 9, 30, tzinfo=timezone.utc),
        user_id="alice",
        user_role="editor",
        request_payload={
            "inputs": {
                "input_file": "/library/slow.epub",
                "base_output_file": "slow-book",
                "target_languages": ["es"],
                "selected_voice": "macOS-auto-male",
            }
        },
        result_payload={
            "success": True,
            "output_files": ["slow-book.html"],
            "media_metadata": {"title": "Slow Book"},
        },
    )
    newer = PipelineJob(
        job_id="job-newer",
        job_type="pipeline",
        status=PipelineJobStatus.RUNNING,
        created_at=datetime(2026, 6, 22, 10, 45, tzinfo=timezone.utc),
        started_at=datetime(2026, 6, 22, 10, 46, tzinfo=timezone.utc),
        user_id="alice",
        user_role="editor",
        access={"visibility": "private", "grants": []},
        generated_files={"audio": ["chapter-1.mp3"]},
        request_payload={
            "inputs": {
                "input_file": "/library/fast.epub",
                "base_output_file": "fast-book",
                "target_languages": ["de", "fr"],
                "selected_voice": "piper-en_US-lessac-medium",
                "audio_mode": "narration",
                "generate_audio": True,
                "add_images": True,
            }
        },
    )
    stub_service.jobs = {older.job_id: older, newer.job_id: newer}
    stub_service.total = 12
    app.dependency_overrides[get_pipeline_service] = lambda: stub_service

    with TestClient(app) as client:
        response = client.get(
            "/pipelines/jobs?offset=5&limit=2",
            headers={"X-User-Id": "alice", "X-User-Role": "editor"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 12
    assert payload["offset"] == 5
    assert payload["limit"] == 2
    assert [job["job_id"] for job in payload["jobs"]] == ["job-newer", "job-older"]
    assert stub_service.count_calls == [{"user_id": "alice", "user_role": "editor"}]
    assert stub_service.list_calls == [
        {"user_id": "alice", "user_role": "editor", "offset": 5, "limit": 2}
    ]

    latest = payload["jobs"][0]
    assert latest["status"] == "running"
    assert latest["user_id"] == "alice"
    assert latest["access"]["visibility"] == "private"
    assert latest["access"]["grants"] == []
    assert latest["access"]["updatedBy"] is None
    assert latest["access"]["updatedAt"] is None
    assert latest["generated_files"] == {"audio": ["chapter-1.mp3"]}
    assert latest["parameters"]["input_file"] == "/library/fast.epub"
    assert latest["parameters"]["base_output_file"] == "fast-book"
    assert latest["parameters"]["target_languages"] == ["de", "fr"]
    assert latest["parameters"]["selected_voice"] == "piper-en_US-lessac-medium"
    assert latest["parameters"]["audio_mode"] == "narration"
    assert latest["parameters"]["add_images"] is True
    assert latest["job_label"] == "fast"


def test_dashboard_submission_uses_session_metadata() -> None:
    app = create_app()
    stub_service = _StubPipelineService()
    stub_context = _StubRuntimeContextProvider()
    app.dependency_overrides[get_pipeline_service] = lambda: stub_service
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context

    payload = {
        "inputs": {
            "input_file": "demo.epub",
            "base_output_file": "demo",
            "input_language": "en",
            "target_languages": ["en"],
        }
    }

    with TestClient(app) as client:
        response = client.post(
            "/pipelines",
            json=payload,
            headers={"X-User-Id": "bob", "X-User-Role": "editor"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert stub_service.enqueue_calls and stub_service.enqueue_calls[0]["user_id"] == "bob"
    assert stub_service.enqueue_calls[0]["user_role"] == "editor"
    assert stub_context.resolve_calls and stub_context.build_calls
