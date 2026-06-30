from __future__ import annotations

from pathlib import Path

import pytest

from modules.services.export_service import (
    _collect_inline_subtitles,
    _ensure_export_assets,
    _sanitize_media_metadata,
)

pytestmark = pytest.mark.services


def test_offline_export_media_metadata_strips_sensitive_fields_and_urls(
    tmp_path: Path,
) -> None:
    job_root = tmp_path / "job"
    (job_root / "media" / "images").mkdir(parents=True)

    payload = _sanitize_media_metadata(
        {
            "title": "Portable Export",
            "generated_files": {"chunks": "drop-me"},
            "chunks": [{"text": "drop-me"}],
            "api_key": "drop-me",
            "source_url": (
                "https://user:secret@indexer.example.invalid/download/7"
                "?title=Demo&apikey=secret#name=Demo&access_token=secret"
            ),
            "job_cover_asset_url": str(job_root / "media" / "images" / "cover.jpg"),
            "media_metadata_lookup": {
                "provider": "openlibrary",
                "private_key": "drop-me",
                "source_url": (
                    "https://catalog.example.invalid/book?id=7"
                    "&passkey=secret#name=Demo&token=secret"
                ),
            },
            "alternates": [
                {"label": "safe", "credential": "drop-me"},
                "https://viewer.example.invalid/watch?sid=secret&id=7",
            ],
        },
        job_root=job_root,
    )

    assert payload == {
        "title": "Portable Export",
        "source_url": "https://indexer.example.invalid/download/7?title=Demo#name=Demo",
        "job_cover_asset_url": "media/images/cover.jpg",
        "media_metadata_lookup": {
            "provider": "openlibrary",
            "source_url": "https://catalog.example.invalid/book?id=7#name=Demo",
        },
        "alternates": [
            {"label": "safe"},
            "https://viewer.example.invalid/watch?id=7",
        ],
        "job_cover_asset": "media/images/cover.jpg",
        "book_cover_file": "media/images/cover.jpg",
    }


def test_collect_inline_subtitles_uses_safe_stat_for_source_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job"
    subtitle_path = job_root / "media" / "captions.en.vtt"
    subtitle_path.parent.mkdir(parents=True)
    subtitle_path.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n", encoding="utf-8")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == subtitle_path:
            raise AssertionError("export subtitle collection should use safe_stat instead of exists")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    payload = _collect_inline_subtitles(
        {"subtitles": [{"path": "media/captions.en.vtt"}]},
        job_root=job_root,
    )

    assert payload == {"media/captions.en.vtt": subtitle_path.read_text(encoding="utf-8")}


def test_ensure_export_assets_uses_safe_stat_for_template_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets_root = tmp_path / "export-dist"
    assets_root.mkdir()
    export_html = assets_root / "export.html"
    export_html.write_text("<html></html>", encoding="utf-8")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path in {assets_root, export_html}:
            raise AssertionError("export asset lookup should use safe_stat instead of exists")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert _ensure_export_assets(assets_root) == export_html
