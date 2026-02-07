from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import pytest
from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_file_locator, get_pipeline_service
from modules.services.job_manager import PipelineJob, PipelineJobStatus

pytestmark = pytest.mark.webapi


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
    file_path = job_root / "media" / "chunk-001" / "sample.mp3"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"hello world")

    expected_mtime = datetime(2024, 1, 1, tzinfo=timezone.utc)
    os.utime(file_path, (expected_mtime.timestamp(), expected_mtime.timestamp()))

    job.generated_files = {
        "files": [
            {
                "type": "audio",
                "relative_path": "media/chunk-001/sample.mp3",
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
    assert "chunks" in payload
    assert isinstance(payload["chunks"], list)
    assert "complete" in payload
    entry = payload["media"]["audio"][0]
    assert entry["name"] == "sample.mp3"
    assert entry["size"] == file_path.stat().st_size
    assert entry["source"] == "completed"
    assert entry["url"].endswith("media/chunk-001/sample.mp3")
    assert datetime.fromisoformat(entry["updated_at"]) == expected_mtime


def test_get_job_media_populates_sentence_count_from_range(api_app) -> None:
    """sentenceCount must be derived from start/end when not explicitly set.

    During in-progress jobs the tracker may supply chunks with metadata_path
    but without an explicit sentence_count.  The media endpoint must fall back
    to computing the count from start_sentence / end_sentence so the frontend
    can gate interactive playback correctly.
    """
    app, file_locator = api_app
    job_id = "job-progress"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )

    # Create a minimal chunk file on disk so the metadata_path resolves.
    job_root = file_locator.resolve_path(job_id)
    chunk_file = job_root / "metadata" / "chunk_0001.json"
    chunk_file.parent.mkdir(parents=True, exist_ok=True)
    chunk_file.write_text('{"version": 3, "sentence_count": 0}')

    audio_path = job_root / "media" / "chunk-001" / "audio.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"\x00" * 64)

    # Tracker payload mirrors what ProgressTracker emits: chunks with
    # start/end but no sentence_count, and a metadata_path present.
    tracker_payload: dict[str, Any] = {
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "range_fragment": "001-010",
                "start_sentence": 1,
                "end_sentence": 11,
                "metadata_path": "metadata/chunk_0001.json",
                # Note: no 'sentence_count' key here
                "files": [
                    {"type": "audio", "path": str(audio_path)},
                ],
            }
        ],
    }

    job.tracker = _TrackerStub(tracker_payload)
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["chunks"]) == 1

    chunk = payload["chunks"][0]
    # The critical assertion: sentenceCount must be populated (11 - 1 = 10)
    assert chunk["sentenceCount"] == 10
    assert chunk["startSentence"] == 1
    assert chunk["endSentence"] == 11


def test_get_job_media_live_prefers_tracker_snapshot(api_app) -> None:
    app, file_locator = api_app
    job_id = "job-live"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )

    job_root = file_locator.resolve_path(job_id)
    live_path = job_root / "media" / "chunk-002" / "live.html"
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
                "relative_path": "media/stale/live.html",
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
    assert "chunks" in payload
    assert isinstance(payload["chunks"], list)
    assert "complete" in payload
    entry = payload["media"]["html"][0]
    assert entry["name"] == "live.html"
    assert entry["source"] == "live"
    assert entry["url"].endswith("media/chunk-002/live.html")
    assert entry["size"] == live_path.stat().st_size
