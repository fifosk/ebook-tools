from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_pipeline_service,
    get_runtime_context_provider,
)
from modules.services.job_manager.job import PipelineJobStatus


class _StubPipelineService:
    def __init__(self) -> None:
        self.list_calls: list[dict[str, object | None]] = []
        self.enqueue_calls: list[dict[str, object | None]] = []

    def list_jobs(self, *, user_id=None, user_role=None):
        self.list_calls.append({"user_id": user_id, "user_role": user_role})
        return {}

    def enqueue(self, request, *, user_id=None, user_role=None):
        self.enqueue_calls.append(
            {"user_id": user_id, "user_role": user_role, "request": request}
        )
        return SimpleNamespace(
            job_id="job-123",
            status=PipelineJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
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
    assert stub_service.list_calls == [{"user_id": "alice", "user_role": "editor"}]


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
            headers={"X-User-Id": "bob", "X-User-Role": "viewer"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert stub_service.enqueue_calls and stub_service.enqueue_calls[0]["user_id"] == "bob"
    assert stub_service.enqueue_calls[0]["user_role"] == "viewer"
    assert stub_context.resolve_calls and stub_context.build_calls
