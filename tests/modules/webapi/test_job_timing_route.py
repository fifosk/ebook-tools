from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from modules.services.file_locator import FileLocator
from modules.services.job_manager import PipelineJob, PipelineJobStatus
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_file_locator,
    get_library_repository,
    get_pipeline_job_manager,
    get_request_user,
)
from modules.webapi.routes.media import timing as timing_routes

pytestmark = pytest.mark.webapi


class _RecordingJobManager:
    def __init__(self, job: PipelineJob | None = None, *, error: Exception | None = None) -> None:
        self.job = job
        self.error = error
        self.calls: list[tuple[str, str | None, str | None]] = []

    def get(self, job_id: str, *, user_id=None, user_role=None) -> PipelineJob:
        self.calls.append((job_id, user_id, user_role))
        if self.error is not None:
            raise self.error
        if self.job is None:
            raise KeyError(job_id)
        return self.job


class _EmptyLibraryRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_entry_by_id(self, job_id: str):
        self.calls.append(job_id)
        return None


def _app_with_timing_dependencies(
    *,
    job_manager: _RecordingJobManager,
    file_locator: FileLocator,
    library_repository: _EmptyLibraryRepository | None = None,
):
    app = create_app()
    app.dependency_overrides[get_pipeline_job_manager] = lambda: job_manager
    app.dependency_overrides[get_file_locator] = lambda: file_locator
    app.dependency_overrides[get_library_repository] = (
        lambda: library_repository or _EmptyLibraryRepository()
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )
    return app


def test_job_timing_route_normalizes_padded_job_id(tmp_path: Path) -> None:
    locator = FileLocator(storage_dir=tmp_path)
    job_id = "timing-job"
    job_root = locator.resolve_path(job_id)
    timing_path = job_root / "metadata" / "timing_index.json"
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    timing_path.write_text(
        '{"translation":[{"text":"Hello","start":0.0,"end":0.5}]}',
        encoding="utf-8",
    )
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        result_payload={
            "timing_tracks": {"translation": "metadata/timing_index.json"},
            "timing_meta": {"playbackRate": 1.25},
        },
    )
    manager = _RecordingJobManager(job)
    library_repository = _EmptyLibraryRepository()
    app = _app_with_timing_dependencies(
        job_manager=manager,
        file_locator=locator,
        library_repository=library_repository,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/jobs/%20%20timing-job%20%20/timing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job_id
    assert payload["tracks"]["translation"]["playback_rate"] == 1.25
    assert payload["tracks"]["translation"]["segments"] == [
        {"text": "Hello", "start": 0.0, "end": 0.5}
    ]
    assert manager.calls == [(job_id, "alice", "editor")]
    assert library_repository.calls == [job_id]


def test_job_timing_route_uses_safe_stat_for_timing_file_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locator = FileLocator(storage_dir=tmp_path)
    job_id = "timing-safe-stat"
    job_root = locator.resolve_path(job_id)
    manifest_path = job_root / "metadata" / "job.json"
    timing_path = job_root / "metadata" / "timing_index.json"
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}", encoding="utf-8")
    timing_path.write_text(
        '{"translation":[{"text":"Hello","start":0.0,"end":0.5}]}',
        encoding="utf-8",
    )
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        result_payload={"timing_tracks": {"translation": "metadata/timing_index.json"}},
    )
    manager = _RecordingJobManager(job)
    app = _app_with_timing_dependencies(
        job_manager=manager,
        file_locator=locator,
    )
    guarded_paths = {manifest_path, timing_path}
    original_exists = Path.exists
    original_stat = Path.stat

    def guarded_exists(path: Path) -> bool:
        if path in guarded_paths:
            raise AssertionError("timing route should use safe_stat instead of exists")
        return original_exists(path)

    def guarded_stat(path: Path, *args, **kwargs):
        if path in guarded_paths:
            raise AssertionError("timing route should use safe_stat instead of direct stat")
        return original_stat(path, *args, **kwargs)

    def fake_safe_stat(path: Path):
        if path in guarded_paths:
            return os.stat(path)
        try:
            return original_stat(path)
        except OSError:
            return None

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "stat", guarded_stat)
    monkeypatch.setattr(timing_routes, "safe_stat", fake_safe_stat)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/jobs/{job_id}/timing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["tracks"]["translation"]["segments"] == [
        {"text": "Hello", "start": 0.0, "end": 0.5}
    ]


def test_job_timing_route_rejects_blank_job_id_without_lookup(tmp_path: Path) -> None:
    manager = _RecordingJobManager()
    library_repository = _EmptyLibraryRepository()
    app = _app_with_timing_dependencies(
        job_manager=manager,
        file_locator=FileLocator(storage_dir=tmp_path),
        library_repository=library_repository,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/jobs/%20%20%20/timing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    assert manager.calls == []
    assert library_repository.calls == []


def test_job_timing_route_permission_error_uses_generic_detail(tmp_path: Path) -> None:
    manager = _RecordingJobManager(
        error=PermissionError("alice cannot read /Volumes/Data/private/timing-job")
    )
    app = _app_with_timing_dependencies(
        job_manager=manager,
        file_locator=FileLocator(storage_dir=tmp_path),
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/jobs/%20%20timing-job%20%20/timing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access timing"}
    rendered = response.text
    assert "alice cannot read" not in rendered
    assert "/Volumes/Data/private" not in rendered
    assert manager.calls == [("timing-job", "alice", "editor")]
