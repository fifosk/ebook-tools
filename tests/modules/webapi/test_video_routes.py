from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

import pytest
from fastapi.testclient import TestClient

from modules.progress_tracker import ProgressTracker
from modules.services.file_locator import FileLocator
from modules.video.jobs import VideoJob, VideoJobResult, VideoJobStatus
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_video_job_manager, get_video_service


@dataclass
class _RecordingVideoJobManager:
    locator: FileLocator
    submissions: List[object] = field(default_factory=list)
    jobs: dict[str, VideoJob] = field(default_factory=dict)

    def __init__(self, locator: FileLocator) -> None:
        self.locator = locator
        self.submissions = []
        self.jobs = {}

    def submit(self, task, *, video_service):
        tracker = ProgressTracker(total_blocks=len(task.slides))
        job = VideoJob(
            job_id="job-123",
            status=VideoJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            tracker=tracker,
        )
        self.submissions.append({"task": task, "service": video_service})
        self.jobs[job.job_id] = job
        return job

    def get(self, job_id: str):
        return self.jobs.get(job_id)


def _build_payload(audio_bytes: bytes) -> dict[str, object]:
    encoded_audio = base64.b64encode(audio_bytes).decode("ascii")
    return {
        "slides": ["Slide 1"],
        "audio": [
            {
                "data": encoded_audio,
                "mime_type": "audio/mpeg",
            }
        ],
        "options": {"batch_start": 5, "batch_end": 5},
    }


@pytest.fixture
def _video_dependencies(tmp_path):
    locator = FileLocator(storage_dir=tmp_path / "jobs")
    manager = _RecordingVideoJobManager(locator)
    service = object()

    app = create_app()
    app.dependency_overrides[get_video_job_manager] = lambda: manager
    app.dependency_overrides[get_video_service] = lambda: service

    yield app, manager

    app.dependency_overrides.clear()


def test_submit_video_job_dispatches_work(_video_dependencies):
    app, manager = _video_dependencies

    response = None
    try:
        with TestClient(app) as client:
            response = client.post("/api/video", json=_build_payload(b"stub-audio"))
    finally:
        app.dependency_overrides.clear()

    assert response is not None
    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "job-123"
    assert payload["status"] == VideoJobStatus.PENDING.value
    assert manager.submissions, "Expected task submission to be recorded"
    submitted_task = manager.submissions[0]["task"]
    assert submitted_task.slides == ["Slide 1"]
    assert submitted_task.options.batch_start == 5
    assert submitted_task.options.batch_end == 5


def test_submit_video_job_rejects_mismatched_audio(_video_dependencies):
    app, _ = _video_dependencies

    invalid_payload = {
        "slides": ["Slide 1", "Slide 2"],
        "audio": [
            {"data": base64.b64encode(b"a").decode("ascii"), "mime_type": "audio/mpeg"}
        ],
    }

    with TestClient(app) as client:
        response = client.post("/api/video", json=invalid_payload)

    assert response.status_code == 422


def test_get_video_job_status_returns_state(_video_dependencies):
    app, manager = _video_dependencies

    with TestClient(app) as client:
        submit_response = client.post("/api/video", json=_build_payload(b"stub"))
        assert submit_response.status_code == 202

        job = manager.get("job-123")
        assert job is not None
        job.status = VideoJobStatus.COMPLETED
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = datetime.now(timezone.utc)
        job.result = VideoJobResult(
            path=manager.locator.resolve_path(job.job_id, "video.mp4"),
            relative_path="video.mp4",
            url="https://example.com/video.mp4",
        )
        job.generated_files = {
            "files": [
                {"type": "video", "path": "video.mp4", "url": "https://example.com/video.mp4"}
            ]
        }
        job.tracker.publish_start({"stage": "video_render"})
        job.tracker.record_media_completion(0, 5)
        job.tracker.mark_finished(reason="completed", forced=False)

        status_response = client.get("/api/video/job-123")

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == VideoJobStatus.COMPLETED.value
    assert status_payload["result"]["relative_path"] == "video.mp4"
    assert status_payload["progress"]["completed"] == 1


def test_get_video_job_status_returns_404(_video_dependencies):
    app, _ = _video_dependencies

    with TestClient(app) as client:
        response = client.get("/api/video/missing-job")

    assert response.status_code == 404
