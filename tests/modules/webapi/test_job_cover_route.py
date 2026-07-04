from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_file_locator, get_library_sync, get_pipeline_service
from modules.services.job_manager import PipelineJob, PipelineJobStatus
import modules.webapi.routes.books_routes as books_routes

import pytest

pytestmark = pytest.mark.webapi


class _StubPipelineService:
    def __init__(self, job: PipelineJob) -> None:
        self._job = job
        self.calls: list[dict[str, object]] = []

    def get_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        self.calls.append(
            {
                "job_id": job_id,
                "user_id": user_id,
                "user_role": user_role,
            }
        )
        assert job_id == self._job.job_id
        return self._job


class _StubLibrarySync:
    def __init__(self) -> None:
        self.get_item_calls: list[str] = []
        self.find_cover_asset_calls: list[str] = []

    def get_item(self, job_id: str) -> None:
        self.get_item_calls.append(job_id)
        return None

    def find_cover_asset(self, job_id: str) -> None:
        self.find_cover_asset_calls.append(job_id)
        return None


def _create_app(tmp_path: Path) -> tuple:
    app = create_app()
    locator = FileLocator(storage_dir=tmp_path)
    library_sync = _StubLibrarySync()

    def _override_locator() -> FileLocator:
        return locator

    app.dependency_overrides[get_file_locator] = _override_locator
    app.dependency_overrides[get_library_sync] = lambda: library_sync
    return app, locator, library_sync


def test_job_cover_route_uses_shared_route_id_normalizer() -> None:
    source = Path(books_routes.__file__).read_text(encoding="utf-8")

    assert "from ..route_ids import normalize_route_id" in source
    assert "def _normalize_route_id" not in source
    assert "normalized_job_id = normalize_route_id(job_id)" in source
    assert "pipeline_service.get_job(\n            normalized_job_id," in source
    assert "metadata_root = file_locator.metadata_root(normalized_job_id)" in source


def test_fetch_job_cover_returns_image(tmp_path: Path) -> None:
    app, locator, _library_sync = _create_app(tmp_path)
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
    app, locator, _library_sync = _create_app(tmp_path)
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


def test_fetch_job_cover_normalizes_padded_job_id(tmp_path: Path) -> None:
    app, locator, library_sync = _create_app(tmp_path)
    job_id = "job-cover-normalized"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )
    service = _StubPipelineService(job)

    metadata_root = locator.metadata_root(job_id)
    metadata_root.mkdir(parents=True, exist_ok=True)
    cover_path = metadata_root / "cover.png"
    cover_path.write_bytes(b"png-bytes")

    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/pipelines/%20%20job-cover-normalized%20%20/cover")

    assert response.status_code == 200
    assert response.content == b"png-bytes"
    assert response.headers["Content-Type"] == "image/png"
    assert service.calls == [
        {
            "job_id": job_id,
            "user_id": None,
            "user_role": None,
        }
    ]
    assert library_sync.get_item_calls == []
    assert library_sync.find_cover_asset_calls == []

    app.dependency_overrides.clear()


def test_fetch_job_cover_rejects_blank_job_id_without_service_lookup(tmp_path: Path) -> None:
    app, _locator, library_sync = _create_app(tmp_path)

    class RaisingPipelineService:
        def get_job(self, *_args: object, **_kwargs: object) -> PipelineJob:
            raise AssertionError("blank cover job ids should not reach pipeline service")

    app.dependency_overrides[get_pipeline_service] = lambda: RaisingPipelineService()

    with TestClient(app) as client:
        response = client.get("/pipelines/%20%20%20/cover")

    assert response.status_code == 404
    assert response.json() == {"detail": "Cover not found"}
    assert library_sync.get_item_calls == []
    assert library_sync.find_cover_asset_calls == []

    app.dependency_overrides.clear()
