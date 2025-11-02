from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Tuple

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


@dataclass
class _StubVideoService:
    backend_name: str = "stub-backend"

    @property
    def renderer(self):  # pragma: no cover - simple stub
        return type("_StubRenderer", (), {"name": self.backend_name})()


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
    locator = FileLocator(storage_dir=tmp_path / "storage")
    manager = _RecordingVideoJobManager(locator)
    service = _StubVideoService()

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
        job.status = VideoJobStatus.RUNNING

        status_response = client.get("/api/video/job-123")

    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["job_id"] == "job-123"
    assert payload["status"] == VideoJobStatus.RUNNING.value


def test_get_video_job_status_returns_results(_video_dependencies):
    app, manager = _video_dependencies

    with TestClient(app) as client:
        submit_response = client.post("/api/video", json=_build_payload(b"stub"))
        assert submit_response.status_code == 202

        job = manager.get("job-123")
        assert job is not None
        job.status = VideoJobStatus.COMPLETED
        job.result = VideoJobResult(
            job_id="job-123",
            created_at=datetime.now(timezone.utc),
            backend="stub-backend",
            slides=["Slide 1"],
            output_path="storage/job-123/video.mp4",
        )

        status_response = client.get("/api/video/job-123")

    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["result"]["backend"] == "stub-backend"
    assert payload["result"]["output_path"] == "storage/job-123/video.mp4"


def test_get_video_job_status_not_found(_video_dependencies):
    app, _ = _video_dependencies

    with TestClient(app) as client:
        response = client.get("/api/video/missing-job")

    assert response.status_code == 404


def test_submit_video_job_instrumentation(_video_dependencies, monkeypatch, caplog):
    app, _ = _video_dependencies

    recorded_metrics: List[Tuple[str, float, dict[str, object]]] = []

    def _record_metric(name: str, value: float, attributes=None):
        recorded_metrics.append((name, value, dict(attributes or {})))

    monkeypatch.setattr(
        "modules.webapi.video_routes.record_metric",
        _record_metric,
    )

    response = None
    with caplog.at_level(logging.INFO, logger="ebook_tools.webapi.video"):
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/video",
                    json=_build_payload(b"stub-audio"),
                    headers={"x-request-id": "video-submit"},
                )
        finally:
            app.dependency_overrides.clear()

    assert response is not None
    assert response.status_code == 202
    events = {record.event for record in caplog.records}
    assert "video.job.submit.request" in events
    assert "video.job.submit.success" in events

    metric_names = [entry[0] for entry in recorded_metrics]
    assert "video.job.submit.requests" in metric_names
    assert "video.job.submit.success" in metric_names
    duration_metrics = [
        entry for entry in recorded_metrics if entry[0] == "video.job.submit.duration_ms"
    ]
    assert duration_metrics
    assert duration_metrics[0][2]["status"] == "success"


def test_get_video_job_status_instrumentation(_video_dependencies, monkeypatch, caplog):
    app, manager = _video_dependencies

    recorded_metrics: List[Tuple[str, float, dict[str, object]]] = []

    def _record_metric(name: str, value: float, attributes=None):
        recorded_metrics.append((name, value, dict(attributes or {})))

    monkeypatch.setattr(
        "modules.webapi.video_routes.record_metric",
        _record_metric,
    )

    with TestClient(app) as client:
        submit_response = client.post(
            "/api/video",
            json=_build_payload(b"stub"),
            headers={"x-request-id": "video-submit-2"},
        )
        assert submit_response.status_code == 202

        job = manager.get("job-123")
        assert job is not None
        job.status = VideoJobStatus.RUNNING

        caplog.clear()
        with caplog.at_level(logging.INFO, logger="ebook_tools.webapi.video"):
            status_response = client.get(
                "/api/video/job-123",
                headers={"x-request-id": "video-status"},
            )

    assert status_response.status_code == 200
    events = {record.event for record in caplog.records}
    assert "video.job.status.request" in events
    assert "video.job.status.success" in events

    status_metrics = [
        entry for entry in recorded_metrics if entry[0].startswith("video.job.status")
    ]
    assert status_metrics
    duration_metrics = [
        entry for entry in status_metrics if entry[0] == "video.job.status.duration_ms"
    ]
    assert duration_metrics
    assert duration_metrics[0][2]["status"] == VideoJobStatus.RUNNING.value


def test_get_video_job_status_not_found_instrumentation(
    _video_dependencies, monkeypatch, caplog
):
    app, _ = _video_dependencies

    recorded_metrics: List[Tuple[str, float, dict[str, object]]] = []

    def _record_metric(name: str, value: float, attributes=None):
        recorded_metrics.append((name, value, dict(attributes or {})))

    monkeypatch.setattr(
        "modules.webapi.video_routes.record_metric",
        _record_metric,
    )

    with caplog.at_level(logging.INFO, logger="ebook_tools.webapi.video"):
        with TestClient(app) as client:
            response = client.get(
                "/api/video/missing-job",
                headers={"x-request-id": "video-status-miss"},
            )

    assert response.status_code == 404
    events = {record.event for record in caplog.records}
    assert "video.job.status.request" in events
    assert "video.job.status.not_found" in events

    metric_names = [entry[0] for entry in recorded_metrics]
    assert "video.job.status.not_found" in metric_names
    not_found_durations = [
        entry for entry in recorded_metrics if entry[0] == "video.job.status.duration_ms"
    ]
    assert not_found_durations
    assert not_found_durations[0][2]["status"] == "not_found"
