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
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_acquisition_route_duration_seconds_count{operation="providers",result="success"}'
        in metrics_response.text
    )


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
