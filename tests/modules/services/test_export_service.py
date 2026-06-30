from __future__ import annotations

from pathlib import Path

import pytest

from modules.services.export_service import _sanitize_media_metadata

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
