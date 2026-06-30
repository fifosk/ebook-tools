from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules import config_manager as cfg
from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_file_locator,
    get_pipeline_service,
    get_request_user,
)
from modules.webapi.routes.media import storage as storage_routes

pytestmark = pytest.mark.webapi


class _StubPipelineService:
    """Minimal stub that allows job access for any job_id."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str | None, str | None]] = []

    def get_job(self, job_id, *, user_id=None, user_role=None):
        self.calls.append((job_id, user_id, user_role))
        if self.error is not None:
            raise self.error
        from types import SimpleNamespace
        return SimpleNamespace(job_id=job_id)


class _NoLookupPipelineService:
    def get_job(self, job_id, *, user_id=None, user_role=None):
        raise AssertionError("get_job should not be called")


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)


def _metric_samples(metrics_text: str, family_name: str):
    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_text)
    }
    return families[family_name].samples


def _has_stream_count(metrics_text: str, *, result: str, media_kind: str) -> bool:
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == "file_stream"
        and sample.labels.get("result") == result
        and sample.labels.get("media_kind") == media_kind
        and sample.value >= 1
        for sample in _metric_samples(metrics_text, "ebook_tools_media_stream_duration_seconds")
    )


@pytest.fixture
def storage_app(tmp_path: Path):
    app = create_app()
    locator = FileLocator(storage_dir=tmp_path)

    app.dependency_overrides[get_file_locator] = lambda: locator
    app.dependency_overrides[get_pipeline_service] = lambda: _StubPipelineService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="test", user_role="admin"
    )
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


def test_download_job_file_uses_safe_stat_for_nas_file_checks(
    storage_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, locator = storage_app
    job_id = "download-safe-stat"
    filename = "media/results/output.txt"
    file_path = locator.resolve_path(job_id, filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("pipeline completed")
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path) -> bool:
        if path == file_path:
            raise AssertionError("download route should use safe_stat instead of exists")
        return original_exists(path)

    def guarded_is_file(path: Path) -> bool:
        if path == file_path:
            raise AssertionError("download route should use safe_stat instead of is_file")
        return original_is_file(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    with TestClient(app) as client:
        response = client.get(f"/storage/jobs/{job_id}/files/{filename}")

    assert response.status_code == 200
    assert response.content == b"pipeline completed"
    assert response.headers["Content-Length"] == str(len("pipeline completed"))


def test_download_job_file_normalizes_padded_job_id(tmp_path: Path) -> None:
    app = create_app()
    locator = FileLocator(storage_dir=tmp_path)
    service = _StubPipelineService()
    job_id = "download-padded"
    file_path = locator.resolve_path(job_id, "media/results/output.txt")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("pipeline completed")
    app.dependency_overrides[get_file_locator] = lambda: locator
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/storage/jobs/%20%20download-padded%20%20/files/media/results/output.txt"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.content == b"pipeline completed"
    assert service.calls == [(job_id, "alice", "editor")]


def test_download_job_file_rejects_blank_job_id_without_service_lookup(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_file_locator] = lambda: FileLocator(storage_dir=tmp_path)
    app.dependency_overrides[get_pipeline_service] = lambda: _NoLookupPipelineService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/storage/jobs/%20%20%20/files/media/results/output.txt")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_download_job_file_permission_error_uses_generic_detail(tmp_path: Path) -> None:
    app = create_app()
    service = _StubPipelineService(
        error=PermissionError("alice cannot read /Volumes/Data/private/download-secret")
    )
    app.dependency_overrides[get_file_locator] = lambda: FileLocator(storage_dir=tmp_path)
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/storage/jobs/%20%20download-secret%20%20/files/media/results/output.txt"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access job files"}
    rendered = response.text
    assert "alice cannot read" not in rendered
    assert "/Volumes/Data/private" not in rendered
    assert service.calls == [("download-secret", "alice", "editor")]


def test_download_partial_range_records_stream_metric_and_safe_log(storage_app, monkeypatch) -> None:
    app, locator = storage_app
    logger = _RecordingLogger()
    job_id = "download-range"
    filename = "media/chunk.bin"
    file_path = locator.resolve_path(job_id, filename)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"abcdefghij")
    monkeypatch.setattr(storage_routes, "logger", logger)

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/{filename}",
            headers={"Range": "bytes=2-5"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 206
    assert response.content == b"cdef"
    assert response.headers["Content-Range"] == "bytes 2-5/10"
    assert response.headers["Content-Length"] == "4"
    assert _has_stream_count(metrics_response.text, result="partial", media_kind="other")

    rendered_logs = "\n".join(logger.messages)
    assert "Media file stream result=partial media_kind=other status=206 bytes=4" in rendered_logs
    assert job_id not in rendered_logs
    assert filename not in rendered_logs
    assert "bytes=2-5" not in rendered_logs


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


def test_download_invalid_range_records_stream_metric(storage_app) -> None:
    app, locator = storage_app
    job_id = "download-invalid-range-metric"
    file_path = locator.resolve_path(job_id, "media/data.mp4")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"12345")

    with TestClient(app) as client:
        response = client.get(
            f"/storage/jobs/{job_id}/files/media/data.mp4",
            headers={"Range": "bytes=10-20"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 416
    assert _has_stream_count(metrics_response.text, result="range_unsatisfiable", media_kind="video")


def test_download_multi_range_honors_first_range(storage_app) -> None:
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

    # Multi-range requests now honor the first range instead of falling back
    # to a full-body response.
    assert response.status_code == 206
    assert response.content == b"ab"
    assert response.headers["Content-Range"] == "bytes 0-1/10"


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
