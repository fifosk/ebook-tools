from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_request_user,
    get_runtime_context_provider,
)


pytestmark = pytest.mark.webapi


class _StubRuntimeContextProvider:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def resolve_config(self) -> dict[str, Any]:
        return dict(self._config)


def test_acquisition_provider_route_returns_token_safe_contract(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    video_root = tmp_path / "videos"
    books_root.mkdir()
    video_root.mkdir()
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "ebooks_dir": str(books_root),
            "youtube_video_root": str(video_root),
            "youtube_api_key": "secret-youtube-key",
            "download_station_url": "https://nas.example.invalid",
            "download_station_username": "nas-user",
            "download_station_password": "nas-secret",
        }
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/acquisition/providers")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    provider_ids = {provider["id"] for provider in payload["providers"]}
    assert {
        "local_epub",
        "manual_downloads",
        "nas_video",
        "youtube_url",
        "youtube_search",
        "download_station",
        "newznab_torznab",
        "openlibrary",
        "gutenberg",
        "internet_archive",
    } <= provider_ids

    local_epub = next(
        provider for provider in payload["providers"] if provider["id"] == "local_epub"
    )
    assert local_epub["status"] == "available"
    assert local_epub["source_path"] == books_root.as_posix()
    youtube_search = next(
        provider for provider in payload["providers"] if provider["id"] == "youtube_search"
    )
    assert youtube_search["configured"] is True
    openlibrary = next(
        provider for provider in payload["providers"] if provider["id"] == "openlibrary"
    )
    assert openlibrary["available"] is True
    assert openlibrary["capabilities"] == ["search", "metadata"]
    download_station = next(
        provider
        for provider in payload["providers"]
        if provider["id"] == "download_station"
    )
    assert download_station["available"] is True
    assert any("Z-Library" in note for note in payload["policy_notes"])

    rendered = str(payload)
    assert "secret-youtube-key" not in rendered
    assert "nas.example.invalid" not in rendered
    assert "nas-user" not in rendered
    assert "nas-secret" not in rendered
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_acquisition_route_duration_seconds_count{operation="providers",result="success"}'
        in metrics_response.text
    )


def test_acquisition_discover_route_returns_manual_download_epubs(tmp_path: Path) -> None:
    manual_root = tmp_path / "manual"
    manual_root.mkdir()
    book_path = manual_root / "Origin.epub"
    book_path.write_text("demo", encoding="utf-8")
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "manual_download_root": str(manual_root),
        }
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/acquisition/discover?media_kind=book&provider=manual_downloads&q=origin"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers_queried"] == ["manual_downloads"]
    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["provider"] == "manual_downloads"
    assert candidate["local_path"] == book_path.as_posix()


def test_acquisition_discover_route_returns_local_epub_candidates(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    (books_root / "The Lost Symbol.epub").write_text("demo", encoding="utf-8")
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "ebooks_dir": str(books_root),
            "youtube_api_key": "secret-youtube-key",
        }
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/acquisition/discover?media_kind=book&q=lost")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers_queried"] == ["local_epub"]
    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["provider"] == "local_epub"
    assert candidate["local_path"] == "The Lost Symbol.epub"
    assert candidate["title"] == "The Lost Symbol"
    assert candidate["candidate_token"]
    rendered = str(payload)
    assert "secret-youtube-key" not in rendered
    assert (
        'ebook_tools_acquisition_route_duration_seconds_count{operation="discover",result="success"}'
        in metrics_response.text
    )


def test_acquisition_discover_route_supports_newznab_torznab_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.services.acquisition import (
        AcquisitionCandidate,
        AcquisitionDiscoveryResult,
    )
    from modules.webapi.routers import acquisition as acquisition_router

    def _fake_discovery(**kwargs):
        assert kwargs["media_kind"] == "video"
        assert kwargs["provider"] == "newznab_torznab"
        assert kwargs["query"] == "readable history"
        assert kwargs["config"]["torznab_api_key"] == "secret-indexer-key"
        return AcquisitionDiscoveryResult(
            providers_queried=("newznab_torznab",),
            candidates=(
                AcquisitionCandidate(
                    candidate_id="newznab_torznab:demo",
                    provider="newznab_torznab",
                    media_kind="video",
                    title="Readable History S01E01",
                    rights="unknown",
                    capabilities=("search", "metadata"),
                    candidate_token="token",
                    size_bytes=734003200,
                    requires_confirmation=True,
                    policy_notes=("Review-only metadata.",),
                    metadata={
                        "source_kind": "newznab_torznab",
                        "seeders": 14,
                        "has_download_url": True,
                    },
                ),
            ),
        )

    monkeypatch.setattr(acquisition_router, "discover_acquisition_candidates", _fake_discovery)
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "torznab_url": "https://indexer.example.invalid/api",
            "torznab_api_key": "secret-indexer-key",
        }
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/acquisition/discover?media_kind=video&provider=newznab_torznab&q=readable%20history"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["providers_queried"] == ["newznab_torznab"]
    assert payload["candidates"][0]["provider"] == "newznab_torznab"
    assert payload["candidates"][0]["metadata"]["seeders"] == 14
    assert "secret-indexer-key" not in str(payload)


def test_acquisition_discover_route_rejects_non_discovery_provider(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {"youtube_video_root": str(tmp_path)}
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/acquisition/discover?media_kind=video&provider=download_station"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "download_station" in response.json()["detail"]


def test_acquisition_discover_route_returns_provider_error_without_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.services.acquisition import AcquisitionProviderDiscoveryError
    from modules.webapi.routers import acquisition as acquisition_router

    def _fail_discovery(**kwargs):
        raise AcquisitionProviderDiscoveryError(
            provider="youtube_search",
            reason="quotaExceeded",
            message="YouTube search quota or rate limit was exceeded. Check the backend YouTube Data API quota, then try again.",
        )

    monkeypatch.setattr(acquisition_router, "discover_acquisition_candidates", _fail_discovery)
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {"youtube_api_key": "secret-youtube-key"}
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/acquisition/discover?media_kind=video&provider=youtube_search&q=demo"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "quota" in detail.casefold()
    assert "secret-youtube-key" not in detail


def test_acquisition_acquire_route_returns_prepared_artifact(tmp_path: Path, monkeypatch) -> None:
    from modules.services.acquisition import AcquisitionArtifact
    from modules.webapi.routers import acquisition as acquisition_router

    def _fake_acquire_candidate(**kwargs):
        assert kwargs["candidate_token"] == "token"
        assert kwargs["confirmed"] is True
        assert kwargs["filename"] == "Frankenstein.epub"
        return AcquisitionArtifact(
            provider="gutenberg",
            media_kind="book",
            status="completed",
            artifact_path="Frankenstein.epub",
            local_path="Frankenstein.epub",
            filename="Frankenstein.epub",
            size_bytes=9,
            modified_at=datetime(2026, 6, 25, 12, 0, 0),
            next_actions=("create_book_job", "load_content_index"),
            metadata={"source_kind": "gutenberg", "gutenberg_id": 84},
        )

    monkeypatch.setattr(acquisition_router, "acquire_acquisition_candidate", _fake_acquire_candidate)
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {"ebooks_dir": str(tmp_path)}
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/acquisition/acquire",
                json={
                    "candidate_token": "token",
                    "confirmed": True,
                    "filename": "Frankenstein.epub",
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["provider"] == "gutenberg"
    assert payload["media_kind"] == "book"
    assert payload["local_path"] == "Frankenstein.epub"
    assert payload["next_actions"] == ["create_book_job", "load_content_index"]
    assert payload["metadata"]["gutenberg_id"] == 84
    assert (
        'ebook_tools_acquisition_route_duration_seconds_count{operation="acquire",result="success"}'
        in metrics_response.text
    )


def test_acquisition_acquire_route_returns_internet_archive_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from modules.services.acquisition import AcquisitionArtifact
    from modules.webapi.routers import acquisition as acquisition_router

    def _fake_acquire_candidate(**kwargs):
        assert kwargs["candidate_token"] == "internet-archive-token"
        assert kwargs["confirmed"] is True
        assert kwargs["filename"] == "Demo Public Book.epub"
        return AcquisitionArtifact(
            provider="internet_archive",
            media_kind="book",
            status="completed",
            artifact_path="Demo Public Book.epub",
            local_path="Demo Public Book.epub",
            filename="Demo Public Book.epub",
            size_bytes=4567,
            modified_at=datetime(2026, 6, 25, 12, 30, 0),
            next_actions=("create_book_job", "load_content_index"),
            metadata={
                "source_kind": "internet_archive",
                "identifier": "demo_public_book",
                "source_url": "https://archive.org/download/demo_public_book/demo_public_book.epub",
            },
        )

    monkeypatch.setattr(acquisition_router, "acquire_acquisition_candidate", _fake_acquire_candidate)
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {"ebooks_dir": str(tmp_path)}
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/acquisition/acquire",
                json={
                    "candidate_token": "internet-archive-token",
                    "confirmed": True,
                    "filename": "Demo Public Book.epub",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["provider"] == "internet_archive"
    assert payload["media_kind"] == "book"
    assert payload["local_path"] == "Demo Public Book.epub"
    assert payload["next_actions"] == ["create_book_job", "load_content_index"]
    assert payload["metadata"]["identifier"] == "demo_public_book"
    assert "archive.org" in payload["metadata"]["source_url"]


def test_acquisition_job_route_submits_download_station_handoff(tmp_path: Path, monkeypatch) -> None:
    from modules.services.acquisition import AcquisitionJobStatus
    from modules.webapi.routers import acquisition as acquisition_router

    def _fake_enqueue_job(**kwargs):
        assert kwargs["source_uri"] == "magnet:?xt=urn:btih:abc123"
        assert kwargs["confirmed"] is True
        assert kwargs["destination"] == "downloads"
        assert kwargs["config"]["download_station_password"] == "nas-secret"
        return AcquisitionJobStatus(
            provider="download_station",
            task_id="dbid_001",
            status="submitted",
            external_task_id="dbid_001",
            message="Download Station accepted the reviewed task.",
            next_actions=("poll_download", "discover_manual_downloads", "import_local"),
            metadata={"source_kind": "download_station"},
        )

    monkeypatch.setattr(acquisition_router, "enqueue_download_station_task", _fake_enqueue_job)
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "download_station_url": "https://nas.example.invalid",
            "download_station_username": "nas-user",
            "download_station_password": "nas-secret",
        }
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/acquisition/jobs",
                json={
                    "provider": "download_station",
                    "source_uri": "magnet:?xt=urn:btih:abc123",
                    "confirmed": True,
                    "destination": "downloads",
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = response.json()
    assert payload["provider"] == "download_station"
    assert payload["task_id"] == "dbid_001"
    assert payload["status"] == "submitted"
    assert payload["next_actions"] == [
        "poll_download",
        "discover_manual_downloads",
        "import_local",
    ]
    rendered = str(payload)
    assert "nas-secret" not in rendered
    assert "nas-user" not in rendered
    assert (
        'ebook_tools_acquisition_route_duration_seconds_count{operation="job_create",result="success"}'
        in metrics_response.text
    )


def test_acquisition_job_poll_route_returns_download_station_status(tmp_path: Path, monkeypatch) -> None:
    from modules.services.acquisition import AcquisitionJobStatus
    from modules.webapi.routers import acquisition as acquisition_router

    def _fake_poll_job(**kwargs):
        assert kwargs["task_id"] == "dbid_001"
        assert kwargs["config"]["download_station_password"] == "nas-secret"
        return AcquisitionJobStatus(
            provider="download_station",
            task_id="dbid_001",
            status="completed",
            progress=1.0,
            external_task_id="dbid_001",
            raw_status="finished",
            completed_files=("Demo.mkv",),
            next_actions=("discover_manual_downloads", "import_local"),
            metadata={"source_kind": "download_station"},
        )

    monkeypatch.setattr(acquisition_router, "poll_download_station_task", _fake_poll_job)
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "download_station_url": "https://nas.example.invalid",
            "download_station_username": "nas-user",
            "download_station_password": "nas-secret",
        }
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/acquisition/jobs/dbid_001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["progress"] == 1.0
    assert payload["completed_files"] == ["Demo.mkv"]
    assert payload["next_actions"] == ["discover_manual_downloads", "import_local"]


def test_acquisition_job_route_maps_download_station_errors_without_secret(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from modules.services.acquisition import DownloadStationError
    from modules.webapi.routers import acquisition as acquisition_router

    def _fail_enqueue(**kwargs):
        raise DownloadStationError(
            reason="auth_failed",
            message="Download Station authentication did not return a session id.",
        )

    monkeypatch.setattr(acquisition_router, "enqueue_download_station_task", _fail_enqueue)
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "download_station_url": "https://nas.example.invalid",
            "download_station_username": "nas-user",
            "download_station_password": "nas-secret",
        }
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="editor",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/acquisition/jobs",
                json={
                    "provider": "download_station",
                    "source_uri": "https://example.invalid/demo.torrent",
                    "confirmed": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "authentication" in detail.casefold()
    assert "nas-secret" not in detail


def test_acquisition_discover_requires_editor_role(tmp_path: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {"ebooks_dir": str(tmp_path)}
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="viewer",
        user_role="viewer",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/acquisition/discover?media_kind=book")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
