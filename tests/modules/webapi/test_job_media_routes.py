from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import pytest
from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_file_locator, get_pipeline_service
from modules.webapi.jobs import PipelineJob, PipelineJobStatus


class _StubPipelineService:
    def __init__(self, job: PipelineJob) -> None:
        self._job = job

    def get_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        assert job_id == self._job.job_id
        return self._job


class _TrackerStub:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = payload

    def get_generated_files(self) -> Mapping[str, Any]:
        return self._payload


@pytest.fixture
def api_app(tmp_path):
    app = create_app()
    file_locator = FileLocator(storage_dir=tmp_path, base_url="https://example.invalid/jobs")

    def _override_locator() -> FileLocator:
        return file_locator

    app.dependency_overrides[get_file_locator] = _override_locator
    yield app, file_locator
    app.dependency_overrides.clear()


def test_get_job_media_returns_completed_entries(api_app) -> None:
    app, file_locator = api_app
    job_id = "job-media"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    job_root = file_locator.resolve_path(job_id)
    file_path = job_root / "chunk-001" / "sample.mp3"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"hello world")

    expected_mtime = datetime(2024, 1, 1, tzinfo=timezone.utc)
    os.utime(file_path, (expected_mtime.timestamp(), expected_mtime.timestamp()))

    job.generated_files = {
        "files": [
            {
                "type": "audio",
                "relative_path": "chunk-001/sample.mp3",
            }
        ]
    }

    service = _StubPipelineService(job)

    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    payload = response.json()

    assert response.status_code == 200
    assert "audio" in payload["media"]
    entry = payload["media"]["audio"][0]
    assert entry["name"] == "sample.mp3"
    assert entry["size"] == file_path.stat().st_size
    assert entry["source"] == "completed"
    assert entry["url"].endswith("chunk-001/sample.mp3")
    assert datetime.fromisoformat(entry["updated_at"]) == expected_mtime


def test_get_job_media_live_prefers_tracker_snapshot(api_app) -> None:
    app, file_locator = api_app
    job_id = "job-live"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )

    job_root = file_locator.resolve_path(job_id)
    live_path = job_root / "chunk-002" / "live.html"
    live_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text("<p>content</p>")

    os.utime(live_path, (live_path.stat().st_mtime, live_path.stat().st_mtime))

    tracker_payload = {
        "files": [
            {
                "type": "html",
                "path": str(live_path),
            }
        ]
    }

    job.tracker = _TrackerStub(tracker_payload)
    job.generated_files = {
        "files": [
            {
                "type": "html",
                "relative_path": "stale/live.html",
            }
        ]
    }

    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media/live")

    payload = response.json()

    assert response.status_code == 200
    assert "html" in payload["media"]
    entry = payload["media"]["html"][0]
    assert entry["name"] == "live.html"
    assert entry["source"] == "live"
    assert entry["url"].endswith("chunk-002/live.html")
    assert entry["size"] == live_path.stat().st_size
