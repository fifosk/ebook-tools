from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_file_locator, get_pipeline_service
from modules.services.job_manager import PipelineJob, PipelineJobStatus

import pytest

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


def _create_app(tmp_path: Path) -> tuple:
    app = create_app()
    locator = FileLocator(storage_dir=tmp_path)

    def _override_locator() -> FileLocator:
        return locator

    app.dependency_overrides[get_file_locator] = _override_locator
    return app, locator


def test_fetch_job_cover_returns_image(tmp_path: Path) -> None:
    app, locator = _create_app(tmp_path)
    job_id = "job-cover-route"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    metadata_root = locator.metadata_root(job_id)
    metadata_root.mkdir(parents=True, exist_ok=True)
    cover_path = metadata_root / "cover.jpg"
    cover_path.write_bytes(b"image-bytes")

    app.dependency_overrides[get_pipeline_service] = lambda: _StubPipelineService(job)

    with TestClient(app) as client:
        response = client.get(f"/pipelines/{job_id}/cover")

    assert response.status_code == 200
    assert response.content == b"image-bytes"
    assert response.headers["Content-Type"] == "image/jpeg"
    assert response.headers["Content-Disposition"].startswith('inline;')

    app.dependency_overrides.clear()


def test_fetch_job_cover_not_found(tmp_path: Path) -> None:
    app, locator = _create_app(tmp_path)
    job_id = "job-missing-cover"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    app.dependency_overrides[get_pipeline_service] = lambda: _StubPipelineService(job)

    with TestClient(app) as client:
        response = client.get(f"/pipelines/{job_id}/cover")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cover not found"

    app.dependency_overrides.clear()
