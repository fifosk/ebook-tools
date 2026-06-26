from __future__ import annotations

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
