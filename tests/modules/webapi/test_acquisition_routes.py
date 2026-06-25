from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.dependencies import get_runtime_context_provider


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
