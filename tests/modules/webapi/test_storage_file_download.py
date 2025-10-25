from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_file_locator


@pytest.fixture
def storage_app(tmp_path: Path):
    app = create_app()
    locator = FileLocator(storage_dir=tmp_path)

    def _override_locator() -> FileLocator:
        return locator

    app.dependency_overrides[get_file_locator] = _override_locator
    yield app, locator
    app.dependency_overrides.clear()


def test_download_full_file(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-full"
    file_path = locator.resolve_path(job_id, "results/output.txt")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("pipeline completed")

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/files/results/output.txt")

    assert response.status_code == 200
    assert response.content == b"pipeline completed"
    assert response.headers["Content-Length"] == str(len("pipeline completed"))
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Disposition"].endswith('"output.txt"')


def test_download_full_file_without_files_prefix(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-full-legacy"
    file_path = locator.resolve_path(job_id, "results/output.txt")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("pipeline completed")

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/results/output.txt")

    assert response.status_code == 200
    assert response.content == b"pipeline completed"
    assert response.headers["Content-Length"] == str(len("pipeline completed"))
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Disposition"].endswith('"output.txt"')


def test_download_partial_range(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-range"
    file_path = locator.resolve_path(job_id, "chunk.bin")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"abcdefghij")

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/chunk.bin",
            headers={"Range": "bytes=2-5"},
        )

    assert response.status_code == 206
    assert response.content == b"cdef"
    assert response.headers["Content-Range"] == "bytes 2-5/10"
    assert response.headers["Content-Length"] == "4"


def test_download_invalid_range_returns_416(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-invalid-range"
    file_path = locator.resolve_path(job_id, "data.bin")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"12345")

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/data.bin",
            headers={"Range": "bytes=10-20"},
        )

    assert response.status_code == 416
    assert response.headers["Content-Range"] == "bytes */5"


def test_download_missing_file_returns_404(storage_app) -> None:
    app, _ = storage_app
    job_id = "missing-file"

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/files/result.txt")

    assert response.status_code == 404
