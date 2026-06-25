from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import modules.services.acquisition.discovery as acquisition_discovery
from modules.services.acquisition import (
    acquire_acquisition_candidate,
    discover_acquisition_candidates,
    list_acquisition_providers,
)


def _provider_by_id(payload, provider_id: str):
    return next(provider for provider in payload.providers if provider.id == provider_id)


def _candidate_token(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


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
    assert providers["gutenberg"].status == "available"

    serialized = str(registry.as_dict())
    assert "secret-youtube-key" not in serialized
    assert "nas.example.invalid" not in serialized
    assert "indexer.example.invalid" not in serialized
    assert any("Z-Library" in note for note in registry.policy_notes)


def test_discover_local_epub_candidates_are_newest_first(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    old_book = books_root / "Angels and Demons.epub"
    new_book = books_root / "Inferno.epub"
    old_book.write_text("old", encoding="utf-8")
    new_book.write_text("new", encoding="utf-8")
    old_mtime = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
    new_mtime = datetime(2026, 6, 25, tzinfo=timezone.utc).timestamp()
    os.utime(old_book, (old_mtime, old_mtime))
    os.utime(new_book, (new_mtime, new_mtime))

    result = discover_acquisition_candidates(
        media_kind="book",
        query="",
        config={"ebooks_dir": str(books_root)},
    )

    assert result.providers_queried == ("local_epub",)
    assert [candidate.local_path for candidate in result.candidates] == [
        "Inferno.epub",
        "Angels and Demons.epub",
    ]
    assert result.candidates[0].provider == "local_epub"
    assert result.candidates[0].rights == "user_provided"
    assert result.candidates[0].candidate_token


def test_discover_zero_limit_skips_provider_scan(tmp_path: Path, monkeypatch) -> None:
    def _fail_scan(*args, **kwargs):
        raise AssertionError("zero-limit discovery should not scan provider roots")

    monkeypatch.setattr(acquisition_discovery, "walk_visible_source_files", _fail_scan)

    result = discover_acquisition_candidates(
        media_kind="book",
        query="",
        limit=0,
        config={"ebooks_dir": str(tmp_path)},
    )

    assert result.candidates == ()
    assert result.providers_queried == ()


def test_discover_service_caps_oversized_limits(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    for index in range(60):
        book = books_root / f"Book {index:02d}.epub"
        book.write_text(str(index), encoding="utf-8")

    result = discover_acquisition_candidates(
        media_kind="book",
        query="",
        limit=999,
        config={"ebooks_dir": str(books_root)},
    )

    assert len(result.candidates) == 50


def test_discover_rejects_non_discovery_or_incompatible_provider(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="download_station"):
        discover_acquisition_candidates(
            media_kind="video",
            query="",
            provider="download_station",
            config={"youtube_video_root": str(tmp_path)},
        )

    with pytest.raises(ValueError, match="local_epub"):
        discover_acquisition_candidates(
            media_kind="video",
            query="",
            provider="local_epub",
            config={"ebooks_dir": str(tmp_path)},
        )


def test_discover_nas_video_candidates_include_subtitle_hints(tmp_path: Path) -> None:
    video_root = tmp_path / "videos"
    video_root.mkdir()
    video_path = video_root / "Lecture One [abc123xyz].mp4"
    subtitle_path = video_root / "Lecture One [abc123xyz].en.srt"
    video_path.write_bytes(b"video")
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")

    result = discover_acquisition_candidates(
        media_kind="video",
        query="lecture",
        provider="nas_video",
        config={"youtube_video_root": str(video_root)},
    )

    assert result.providers_queried == ("nas_video",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "nas_video"
    assert candidate.local_path == video_path.as_posix()
    assert candidate.subtitles[0].filename == subtitle_path.name
    assert candidate.subtitles[0].language == "en"


def test_discover_gutenberg_normalizes_public_domain_epub_metadata() -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "results": [
                    {
                        "id": 84,
                        "title": "Frankenstein; Or, The Modern Prometheus",
                        "authors": [{"name": "Shelley, Mary Wollstonecraft"}],
                        "languages": ["en"],
                        "copyright": False,
                        "download_count": 12345,
                        "formats": {
                            "application/epub+zip": "https://www.gutenberg.org/ebooks/84.epub3.images",
                            "image/jpeg": "https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg",
                            "text/html": "https://www.gutenberg.org/ebooks/84.html.images",
                        },
                    }
                ]
            }

    class _FakeSession:
        def __init__(self) -> None:
            self.calls = []

        def get(self, url, *, params, timeout):
            self.calls.append((url, params, timeout))
            return _FakeResponse()

    session = _FakeSession()

    result = discover_acquisition_candidates(
        media_kind="book",
        query="frankenstein",
        provider="gutenberg",
        language="English",
        limit=5,
        session=session,
    )

    assert result.providers_queried == ("gutenberg",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "gutenberg"
    assert candidate.rights == "public_domain"
    assert candidate.requires_confirmation is True
    assert candidate.source_url == "https://www.gutenberg.org/ebooks/84.html.images"
    assert candidate.cover_url == "https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg"
    assert candidate.contributors == ("Shelley, Mary Wollstonecraft",)
    assert candidate.metadata["gutenberg_id"] == 84
    assert candidate.metadata["epub_url"].endswith("84.epub3.images")
    assert session.calls[0][0].endswith("/books")
    assert session.calls[0][1]["search"] == "frankenstein"
    assert session.calls[0][1]["languages"] == "en"


def test_acquire_gutenberg_candidate_persists_epub_in_books_root(tmp_path: Path) -> None:
    class _FakeResponse:
        def __init__(self) -> None:
            self.status_code = 200
            self.closed = False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, *, chunk_size):
            yield b"epub"
            yield b" bytes"

        def close(self) -> None:
            self.closed = True

    class _FakeSession:
        def __init__(self) -> None:
            self.response = _FakeResponse()
            self.calls = []

        def get(self, url, *, stream, timeout, allow_redirects):
            self.calls.append((url, stream, timeout, allow_redirects))
            return self.response

    books_root = tmp_path / "books"
    token = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "gutenberg_id": 84,
            "epub_url": "https://www.gutenberg.org/ebooks/84.epub3.images",
        }
    )
    session = _FakeSession()

    artifact = acquire_acquisition_candidate(
        candidate_token=token,
        confirmed=True,
        filename="Frankenstein.epub",
        config={"ebooks_dir": str(books_root)},
        session=session,
    )

    assert artifact.status == "completed"
    assert artifact.provider == "gutenberg"
    assert artifact.media_kind == "book"
    assert artifact.local_path == "Frankenstein.epub"
    assert artifact.next_actions == ("create_book_job", "load_content_index")
    assert (books_root / "Frankenstein.epub").read_bytes() == b"epub bytes"
    assert artifact.size_bytes == len(b"epub bytes")
    assert session.calls == [
        ("https://www.gutenberg.org/ebooks/84.epub3.images", True, 30, False)
    ]
    assert session.response.closed is True


def test_acquire_gutenberg_candidate_rejects_unconfirmed_or_untrusted_urls(
    tmp_path: Path,
) -> None:
    trusted_token = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "gutenberg_id": 84,
            "epub_url": "https://www.gutenberg.org/ebooks/84.epub3.images",
        }
    )
    with pytest.raises(ValueError, match="confirmation"):
        acquire_acquisition_candidate(
            candidate_token=trusted_token,
            confirmed=False,
            config={"ebooks_dir": str(tmp_path)},
        )

    untrusted_token = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "gutenberg_id": 84,
            "epub_url": "http://127.0.0.1/internal.epub",
        }
    )
    with pytest.raises(ValueError, match="allowed Gutenberg"):
        acquire_acquisition_candidate(
            candidate_token=untrusted_token,
            confirmed=True,
            config={"ebooks_dir": str(tmp_path)},
        )


def test_acquire_gutenberg_candidate_rejects_untrusted_redirect(tmp_path: Path) -> None:
    class _RedirectResponse:
        status_code = 302
        headers = {"Location": "http://127.0.0.1/internal.epub"}

        def close(self) -> None:
            return None

    class _FakeSession:
        def get(self, url, *, stream, timeout, allow_redirects):
            return _RedirectResponse()

    token = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "gutenberg_id": 84,
            "epub_url": "https://www.gutenberg.org/ebooks/84.epub3.images",
        }
    )

    with pytest.raises(ValueError, match="allowed Gutenberg"):
        acquire_acquisition_candidate(
            candidate_token=token,
            confirmed=True,
            config={"ebooks_dir": str(tmp_path)},
            session=_FakeSession(),
        )


def test_discover_youtube_search_normalizes_metadata_without_secret() -> None:
    class _FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class _FakeSession:
        def __init__(self) -> None:
            self.calls = []

        def get(self, url, *, params, timeout):
            self.calls.append((url, params, timeout))
            if url.endswith("/search"):
                return _FakeResponse(
                    {
                        "items": [
                            {
                                "id": {"videoId": "video123"},
                                "snippet": {
                                    "title": "Demo Video",
                                    "channelTitle": "Demo Channel",
                                    "publishedAt": "2026-06-25T10:00:00Z",
                                    "thumbnails": {"medium": {"url": "https://img.example/demo.jpg"}},
                                },
                            }
                        ]
                    }
                )
            return _FakeResponse(
                {
                    "items": [
                        {
                            "id": "video123",
                            "contentDetails": {"duration": "PT1H2M3S"},
                        }
                    ]
                }
            )

    session = _FakeSession()

    result = discover_acquisition_candidates(
        media_kind="video",
        query="demo",
        provider="youtube_search",
        config={"youtube_api_key": "secret-youtube-key"},
        session=session,
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "youtube_search"
    assert candidate.source_url == "https://www.youtube.com/watch?v=video123"
    assert candidate.duration_seconds == 3723
    assert candidate.requires_confirmation is True
    serialized = str(result)
    assert "secret-youtube-key" not in serialized
    assert session.calls[0][1]["safeSearch"] == "moderate"
