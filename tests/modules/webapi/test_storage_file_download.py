from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from modules import config_manager as cfg
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
    file_path = locator.resolve_path(job_id, "media/results/output.txt")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("pipeline completed")

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/files/media/results/output.txt")

    assert response.status_code == 200
    assert response.content == b"pipeline completed"
    assert response.headers["Content-Length"] == str(len("pipeline completed"))
    assert response.headers["Accept-Ranges"] == "bytes"
    assert 'filename="output.txt"' in response.headers["Content-Disposition"]


def test_download_full_file_without_files_prefix(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-full-legacy"
    file_path = locator.resolve_path(job_id, "media/results/output.txt")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("pipeline completed")

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/media/results/output.txt")

    assert response.status_code == 200
    assert response.content == b"pipeline completed"
    assert response.headers["Content-Length"] == str(len("pipeline completed"))
    assert response.headers["Accept-Ranges"] == "bytes"
    assert 'filename="output.txt"' in response.headers["Content-Disposition"]


def test_download_partial_range(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-range"
    file_path = locator.resolve_path(job_id, "media/chunk.bin")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"abcdefghij")

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/media/chunk.bin",
            headers={"Range": "bytes=2-5"},
        )

    assert response.status_code == 206
    assert response.content == b"cdef"
    assert response.headers["Content-Range"] == "bytes 2-5/10"
    assert response.headers["Content-Length"] == "4"


def test_download_invalid_range_returns_416(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-invalid-range"
    file_path = locator.resolve_path(job_id, "media/data.bin")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"12345")

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/media/data.bin",
            headers={"Range": "bytes=10-20"},
        )

    assert response.status_code == 416
    assert response.headers["Content-Range"] == "bytes */5"


def test_download_multi_range_falls_back_to_full_payload(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-multi-range"
    file_path = locator.resolve_path(job_id, "media/chunk.bin")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"abcdefghij")

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/media/chunk.bin",
            headers={"Range": "bytes=0-1,4-5"},
        )

    assert response.status_code == 200
    assert response.content == b"abcdefghij"


def test_download_missing_file_returns_404(storage_app) -> None:
    app, _ = storage_app
    job_id = "missing-file"

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/files/media/result.txt")

    assert response.status_code == 404


def test_download_cover_file(tmp_path: Path) -> None:
    app = create_app()

    cover_root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
    cover_root.mkdir(parents=True, exist_ok=True)
    cover_path = cover_root / "test-cover.jpg"
    cover_path.write_bytes(b"cover-bytes")

    try:
        with TestClient(app) as client:
            response = client.get("/storage/covers/test-cover.jpg")

        assert response.status_code == 200
        assert response.content == b"cover-bytes"
        assert 'filename="test-cover.jpg"' in response.headers["Content-Disposition"]
    finally:
        try:
            cover_path.unlink()
        except FileNotFoundError:
            pass


def test_download_video_defaults_inline_disposition(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-video-inline"
    file_path = locator.resolve_path(job_id, "media/video/output.mp4")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"not-a-real-mp4")

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/files/media/video/output.mp4")

    assert response.status_code == 200
    assert response.content == b"not-a-real-mp4"
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Type"].startswith("video/mp4")
    assert response.headers["Content-Disposition"].startswith("inline;")


def test_download_video_range_keeps_inline_disposition(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-video-range-inline"
    file_path = locator.resolve_path(job_id, "media/video/output.mp4")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"0123456789")

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/media/video/output.mp4",
            headers={"Range": "bytes=0-3"},
        )

    assert response.status_code == 206
    assert response.content == b"0123"
    assert response.headers["Content-Range"] == "bytes 0-3/10"
    assert response.headers["Content-Disposition"].startswith("inline;")
