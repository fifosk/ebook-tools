from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_media_metadata_service,
    get_request_user,
)
from modules.webapi.routes import jobs_routes

pytestmark = pytest.mark.webapi


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)


class _FailingBookMetadataService:
    def lookup_openlibrary_metadata_for_query(self, query: str, *, force: bool = False):
        raise RuntimeError(f"secret book query leaked: {query}")

    def clear_metadata_cache_for_query(self, query: str):
        raise RuntimeError(f"secret book cache query leaked: {query}")


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


def test_book_metadata_preview_failure_is_token_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(jobs_routes, "logger", capture_logger)
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_media_metadata_service] = lambda: _FailingBookMetadataService()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/pipelines/metadata/book/lookup",
                json={"query": "/Volumes/Data/NAS923/Books/Secret Dan Brown.epub"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to lookup Open Library metadata."
    logs = "\n".join(capture_logger.messages)
    assert "Unable to lookup Open Library metadata for query" in logs
    _assert_token_safe_failure(response.json(), logs, "Secret Dan Brown.epub")


def test_book_metadata_cache_clear_failure_is_token_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(jobs_routes, "logger", capture_logger)
    app.dependency_overrides[get_request_user] = _editor_user
    app.dependency_overrides[get_media_metadata_service] = lambda: _FailingBookMetadataService()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/pipelines/metadata/book/cache/clear",
                json={"query": "/Volumes/Data/NAS923/Books/Secret Dan Brown.epub"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to clear metadata cache."
    logs = "\n".join(capture_logger.messages)
    assert "Failed to clear metadata cache" in logs
    _assert_token_safe_failure(response.json(), logs, "Secret Dan Brown.epub")
