from __future__ import annotations

from pathlib import Path

from modules.services.acquisition import list_acquisition_providers


def _provider_by_id(payload, provider_id: str):
    return next(provider for provider in payload.providers if provider.id == provider_id)


def test_acquisition_providers_report_available_local_roots(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    video_root = tmp_path / "videos"
    books_root.mkdir()
    video_root.mkdir()

    registry = list_acquisition_providers(
        config={
            "ebooks_dir": str(books_root),
            "youtube_video_root": str(video_root),
        }
    )

    local_epub = _provider_by_id(registry, "local_epub")
    assert local_epub.status == "available"
    assert local_epub.available is True
    assert local_epub.source_path == books_root.as_posix()
    assert "import_local" in local_epub.capabilities

    nas_video = _provider_by_id(registry, "nas_video")
    assert nas_video.status == "available"
    assert nas_video.available is True
    assert nas_video.source_path == video_root.as_posix()
    assert "extract_subtitles" in nas_video.capabilities


def test_acquisition_provider_config_status_and_policy_notes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "secret-youtube-key")
    monkeypatch.setenv("SYNOLOGY_DOWNLOAD_STATION_URL", "https://nas.example.invalid")
    registry = list_acquisition_providers(
        config={
            "ebooks_dir": str(tmp_path / "missing-books"),
            "youtube_video_root": str(tmp_path / "missing-videos"),
            "prowlarr_url": "https://indexer.example.invalid",
        }
    )

    providers = {provider.id: provider for provider in registry.providers}
    assert providers["local_epub"].status == "not_configured"
    assert providers["nas_video"].status == "not_configured"
    assert providers["youtube_search"].status == "available"
    assert providers["download_station"].status == "available"
    assert providers["newznab_torznab"].status == "available"
    assert providers["gutenberg"].status == "planned"

    serialized = str(registry.as_dict())
    assert "secret-youtube-key" not in serialized
    assert "nas.example.invalid" not in serialized
    assert "indexer.example.invalid" not in serialized
    assert any("Z-Library" in note for note in registry.policy_notes)
