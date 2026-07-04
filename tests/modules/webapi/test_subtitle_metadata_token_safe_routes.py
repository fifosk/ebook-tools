from __future__ import annotations

import inspect

from fastapi.testclient import TestClient
import pytest

from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_request_user,
    get_subtitle_metadata_service,
    get_youtube_video_metadata_service,
)
from modules.webapi.routers.subtitle_utils import metadata_routes

pytestmark = pytest.mark.webapi


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)


class _FailingSubtitleMetadataService:
    def lookup_tv_metadata_for_source(self, source_name: str, *, force: bool = False):
        raise RuntimeError(f"secret tv source leaked: {source_name}")

    def clear_metadata_cache_for_query(self, query: str):
        raise RuntimeError(f"secret tv cache query leaked: {query}")


class _FailingYoutubeMetadataService:
    def lookup_youtube_metadata_for_source(self, source_name: str, *, force: bool = False):
        raise RuntimeError(f"secret youtube source leaked: {source_name}")

    def clear_metadata_cache_for_query(self, query: str):
        raise RuntimeError(f"secret youtube cache query leaked: {query}")


class _RecordingSubtitleMetadataService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bool, str | None, str | None]] = []

    def get_tv_metadata(self, job_id: str, *, user_id=None, user_role=None):
        self.calls.append(("get_tv", job_id, False, user_id, user_role))
        return {"job_id": job_id, "source_name": "show.srt"}

    def lookup_tv_metadata(self, job_id: str, *, force: bool = False, user_id=None, user_role=None):
        self.calls.append(("lookup_tv", job_id, force, user_id, user_role))
        return {"job_id": job_id, "source_name": "show.srt"}


class _RecordingYoutubeMetadataService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bool, str | None, str | None]] = []

    def get_youtube_metadata(self, job_id: str, *, user_id=None, user_role=None):
        self.calls.append(("get_youtube", job_id, False, user_id, user_role))
        return {"job_id": job_id, "source_name": "video.mkv"}

    def lookup_youtube_metadata(self, job_id: str, *, force: bool = False, user_id=None, user_role=None):
        self.calls.append(("lookup_youtube", job_id, force, user_id, user_role))
        return {"job_id": job_id, "source_name": "video.mkv"}


def _editor_user() -> RequestUserContext:
    return RequestUserContext(user_id="editor-user", user_role="editor")


def _assert_token_safe_failure(
    response_json: dict[str, object],
    logs: str,
    *secrets: str,
) -> None:
    assert "secret" not in str(response_json)
    assert "/Volumes/Data" not in str(response_json)
    assert "NAS923" not in str(response_json)
    assert "secret" not in logs
    assert "/Volumes/Data" not in logs
    assert "NAS923" not in logs
    for secret in secrets:
        assert secret not in str(response_json)
        assert secret not in logs


def test_subtitle_metadata_routes_use_shared_route_id_normalizer() -> None:
    source = inspect.getsource(metadata_routes)

    assert "from ...route_ids import normalize_route_id" in source
    assert "def _normalize_route_id" not in source
    assert "normalized_job_id = normalize_route_id(job_id)" in source


def test_subtitle_tv_metadata_routes_normalize_route_job_id() -> None:
    app = create_app()
    service = _RecordingSubtitleMetadataService()
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_subtitle_metadata_service] = lambda: service

    try:
        with TestClient(app) as client:
            metadata_response = client.get(
                "/api/subtitles/jobs/%20%20subtitle-job%20%20/metadata/tv"
            )
            lookup_response = client.post(
                "/api/subtitles/jobs/%20%20subtitle-job%20%20/metadata/tv/lookup",
                json={"force": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert metadata_response.status_code == 200
    assert metadata_response.json()["job_id"] == "subtitle-job"
    assert lookup_response.status_code == 200
    assert lookup_response.json()["job_id"] == "subtitle-job"
    assert service.calls == [
        ("get_tv", "subtitle-job", False, "editor-user", "editor"),
        ("lookup_tv", "subtitle-job", True, "editor-user", "editor"),
    ]


def test_youtube_metadata_routes_normalize_route_job_id() -> None:
    app = create_app()
    service = _RecordingYoutubeMetadataService()
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_youtube_video_metadata_service] = lambda: service

    try:
        with TestClient(app) as client:
            metadata_response = client.get(
                "/api/subtitles/jobs/%20%20youtube-job%20%20/metadata/youtube"
            )
            lookup_response = client.post(
                "/api/subtitles/jobs/%20%20youtube-job%20%20/metadata/youtube/lookup",
                json={"force": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert metadata_response.status_code == 200
    assert metadata_response.json()["job_id"] == "youtube-job"
    assert lookup_response.status_code == 200
    assert lookup_response.json()["job_id"] == "youtube-job"
    assert service.calls == [
        ("get_youtube", "youtube-job", False, "editor-user", "editor"),
        ("lookup_youtube", "youtube-job", True, "editor-user", "editor"),
    ]


@pytest.mark.parametrize(
    ("path", "method", "json_payload"),
    [
        ("/api/subtitles/jobs/%20%20%20/metadata/tv", "GET", None),
        (
            "/api/subtitles/jobs/%20%20%20/metadata/tv/lookup",
            "POST",
            {"force": True},
        ),
        ("/api/subtitles/jobs/%20%20%20/metadata/youtube", "GET", None),
        (
            "/api/subtitles/jobs/%20%20%20/metadata/youtube/lookup",
            "POST",
            {"force": True},
        ),
    ],
)
def test_subtitle_metadata_routes_reject_blank_job_id_without_service_lookup(
    path: str,
    method: str,
    json_payload: dict[str, object] | None,
) -> None:
    app = create_app()
    tv_service = _RecordingSubtitleMetadataService()
    youtube_service = _RecordingYoutubeMetadataService()
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_subtitle_metadata_service] = lambda: tv_service
    app.dependency_overrides[get_youtube_video_metadata_service] = lambda: youtube_service

    try:
        with TestClient(app) as client:
            response = client.request(method, path, json=json_payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": metadata_routes.METADATA_JOB_NOT_FOUND_MESSAGE}
    assert tv_service.calls == []
    assert youtube_service.calls == []


def test_tv_metadata_preview_failure_is_token_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(metadata_routes, "logger", capture_logger)
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_subtitle_metadata_service] = (
        lambda: _FailingSubtitleMetadataService()
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/metadata/tv/lookup",
                json={
                    "source_name": "/Volumes/Data/NAS923/Shows/Secret.Show.S01E02.srt",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to lookup TV metadata."
    logs = "\n".join(capture_logger.messages)
    assert "Unable to lookup TV metadata for subtitle source" in logs
    _assert_token_safe_failure(response.json(), logs, "Secret.Show.S01E02.srt")


def test_tv_metadata_cache_clear_failure_is_token_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(metadata_routes, "logger", capture_logger)
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_subtitle_metadata_service] = (
        lambda: _FailingSubtitleMetadataService()
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/metadata/tv/cache/clear",
                json={"query": "/Volumes/Data/NAS923/Shows/Secret.Show.S01E02.srt"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to clear metadata cache."
    logs = "\n".join(capture_logger.messages)
    assert "Failed to clear TV metadata cache" in logs
    _assert_token_safe_failure(response.json(), logs, "Secret.Show.S01E02.srt")


def test_youtube_metadata_preview_failure_is_token_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(metadata_routes, "logger", capture_logger)
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_youtube_video_metadata_service] = (
        lambda: _FailingYoutubeMetadataService()
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/metadata/youtube/lookup",
                json={
                    "source_name": (
                        "/Volumes/Data/NAS923/Videos/private-video-[abcDEF12345].mkv"
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to lookup YouTube metadata."
    logs = "\n".join(capture_logger.messages)
    assert "Unable to lookup YouTube metadata for source" in logs
    _assert_token_safe_failure(response.json(), logs, "private-video", "abcDEF12345")


def test_youtube_metadata_cache_clear_failure_is_token_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(metadata_routes, "logger", capture_logger)
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_youtube_video_metadata_service] = (
        lambda: _FailingYoutubeMetadataService()
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/metadata/youtube/cache/clear",
                json={"query": "/Volumes/Data/NAS923/Videos/private-video-[abcDEF12345].mkv"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to clear metadata cache."
    logs = "\n".join(capture_logger.messages)
    assert "Failed to clear YouTube metadata cache" in logs
    _assert_token_safe_failure(response.json(), logs, "private-video", "abcDEF12345")
