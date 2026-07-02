from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.library import LibraryError, LibraryNotFoundError
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_library_sync,
    get_request_user,
)

import pytest

pytestmark = pytest.mark.webapi


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)


class _StubLibrarySync:
    def __init__(
        self,
        resolved_path: Path | None = None,
        *,
        error: Exception | None = None,
        item: object | None = None,
        expected_job_id: str = "library-job",
        expected_relative_path: str = "dubbed.mp4",
    ) -> None:
        self._resolved_path = resolved_path
        self._error = error
        self._item = item
        self._expected_job_id = expected_job_id
        self._expected_relative_path = expected_relative_path
        self.calls: list[dict[str, str]] = []

    def get_item(self, job_id: str):
        return self._item

    def resolve_media_file(self, job_id: str, relative_path: str) -> Path:
        self.calls.append({"job_id": job_id, "relative_path": relative_path})
        assert job_id == self._expected_job_id
        assert relative_path == self._expected_relative_path
        if self._error is not None:
            raise self._error
        assert self._resolved_path is not None
        return self._resolved_path


def _private_library_item() -> object:
    return SimpleNamespace(
        owner_id="other-user",
        metadata=SimpleNamespace(data={"access": {"visibility": "private"}}),
    )


def _has_stream_count(metrics_text: str, *, result: str, media_kind: str) -> bool:
    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_text)
    }
    metric = families["ebook_tools_media_stream_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == "file_stream"
        and sample.labels.get("result") == result
        and sample.labels.get("media_kind") == media_kind
        and sample.value >= 1
        for sample in metric.samples
    )


def _has_library_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_text)
    }
    metric = families["ebook_tools_library_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


def test_library_media_file_supports_range_with_inline_disposition(tmp_path: Path) -> None:
    media_path = tmp_path / "dubbed.mp4"
    media_path.write_bytes(b"0123456789")

    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync(media_path)
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="test", user_role="admin"
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/library/media/library-job/file/dubbed.mp4",
                headers={"Range": "bytes=1-4"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 206
    assert response.content == b"1234"
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Range"] == "bytes 1-4/10"
    assert response.headers["Content-Type"].startswith("video/mp4")
    assert response.headers["Content-Disposition"].startswith("inline;")
    assert _has_stream_count(metrics_response.text, result="partial", media_kind="video")


def test_library_media_file_records_token_safe_resolver_timing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "dubbed.mp4"
    media_path.write_bytes(b"0123456789")
    job_id = "secret-library-job"
    user_id = "secret-user-id"
    logger = _RecordingLogger()

    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync(
        media_path,
        expected_job_id=job_id,
        expected_relative_path="secret-dubbed.mp4",
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=user_id,
        user_role="admin",
    )
    monkeypatch.setattr("modules.webapi.routers.library_telemetry.LOGGER", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/library/media/{job_id}/file/secret-dubbed.mp4",
                headers={"Range": "bytes=0-2"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 206
    assert _has_library_metric_count(
        metrics_response.text,
        operation="media_file",
        result="success",
    )
    rendered = metrics_response.text + "\n".join(logger.messages)
    assert "Library media file resolve result=success" in rendered
    assert "has_range=True" in rendered
    assert job_id not in rendered
    assert user_id not in rendered
    assert "secret-dubbed.mp4" not in rendered


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail", "expected_result"),
    [
        (
            LibraryNotFoundError(
                "missing secret-dubbed.mp4 for secret-library-job under "
                "/Volumes/Data/private/library"
            ),
            404,
            "Library media file not found.",
            "not_found",
        ),
        (
            LibraryError(
                "invalid media path secret-dubbed.mp4 for secret-library-job at "
                "/Volumes/Data/private/library"
            ),
            400,
            "Unable to resolve library media file.",
            "bad_request",
        ),
        (
            RuntimeError(
                "resolver crashed for secret-dubbed.mp4 at "
                "/Volumes/Data/private/library"
            ),
            502,
            "Unable to resolve library media file.",
            "error",
        ),
    ],
)
def test_library_media_file_resolver_errors_use_generic_detail_and_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    job_id = "secret-library-job"
    user_id = "secret-user-id"
    logger = _RecordingLogger()

    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync(
        error=error,
        expected_job_id=job_id,
        expected_relative_path="secret-dubbed.mp4",
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=user_id,
        user_role="admin",
    )
    monkeypatch.setattr("modules.webapi.routers.library_telemetry.LOGGER", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/library/media/{job_id}/file/secret-dubbed.mp4",
                headers={"Range": "bytes=0-2"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert _has_library_metric_count(
        metrics_response.text,
        operation="media_file",
        result=expected_result,
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert f"Library media file resolve result={expected_result}" in rendered
    assert "has_range=True" in rendered
    assert job_id not in rendered
    assert user_id not in rendered
    assert "secret-dubbed.mp4" not in rendered
    assert "/Volumes/Data/private/library" not in rendered


def test_library_media_file_forbidden_records_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "secret-library-job"
    user_id = "secret-user-id"
    logger = _RecordingLogger()
    sync = _StubLibrarySync(
        item=_private_library_item(),
        expected_job_id=job_id,
        expected_relative_path="secret-dubbed.mp4",
    )

    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: sync
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=user_id,
        user_role="viewer",
    )
    monkeypatch.setattr("modules.webapi.routers.library_telemetry.LOGGER", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/library/media/{job_id}/file/secret-dubbed.mp4",
                headers={"Range": "bytes=0-2"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access library item"}
    assert sync.calls == []
    assert _has_library_metric_count(
        metrics_response.text,
        operation="media_file",
        result="forbidden",
    )
    rendered = response.text + metrics_response.text + "\n".join(logger.messages)
    assert "Library media file resolve result=forbidden" in rendered
    assert "has_range=True" in rendered
    assert job_id not in rendered
    assert user_id not in rendered
    assert "secret-dubbed.mp4" not in rendered
