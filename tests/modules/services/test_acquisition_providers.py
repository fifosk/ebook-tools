from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

import modules.services.acquisition.discovery as acquisition_discovery
import modules.services.acquisition.acquire as acquisition_acquire
import modules.services.acquisition.indexer_discovery as indexer_discovery
import modules.services.acquisition.provider_registry as acquisition_provider_registry
import modules.services.acquisition.youtube_discovery as youtube_discovery
from modules.services.acquisition.discovery_planning import (
    order_default_discovery_candidates,
    provider_query_limit,
)
from modules.services.acquisition.tokens import decode_acquisition_token, encode_acquisition_token
from modules.services.acquisition.url_safety import looks_sensitive_key, strip_sensitive_url_parts
from modules.services.acquisition import (
    AcquisitionProviderDiscoveryError,
    DISCOVERY_PROVIDER_MEDIA_KINDS,
    acquire_acquisition_candidate,
    default_discovery_provider_ids,
    discovery_media_kinds_for,
    discover_acquisition_candidates,
    enqueue_download_station_task,
    is_indexer_search_configured,
    list_acquisition_providers,
    poll_download_station_task,
    prepare_acquisition_artifact,
    resolve_download_station_candidate_source_uri,
)


def _provider_by_id(payload, provider_id: str):
    return next(provider for provider in payload.providers if provider.id == provider_id)


def _candidate_token(payload: dict[str, object]) -> str:
    return encode_acquisition_token(payload)


def test_acquisition_discovery_planning_orders_default_sources_and_limits() -> None:
    def _candidate(
        provider: str,
        title: str,
        modified_at: datetime | None = None,
    ) -> acquisition_discovery.AcquisitionCandidate:
        return acquisition_discovery.AcquisitionCandidate(
            candidate_id=f"{provider}:{title}",
            provider=provider,
            media_kind="book",
            title=title,
            rights="user_provided",
            capabilities=("metadata",),
            candidate_token=_candidate_token({"provider": provider, "title": title}),
            modified_at=modified_at,
        )

    ordered = order_default_discovery_candidates(
        [
            _candidate("gutenberg", "Remote Hit"),
            _candidate(
                "local_epub",
                "Older Local",
                datetime(2026, 6, 1, tzinfo=timezone.utc),
            ),
            _candidate(
                "manual_downloads",
                "Fresh Manual",
                datetime(2026, 7, 2, tzinfo=timezone.utc),
            ),
            _candidate(
                "local_epub",
                "Alpha Local",
                datetime(2026, 7, 1, tzinfo=timezone.utc),
            ),
        ],
        providers=("local_epub", "manual_downloads", "gutenberg"),
    )

    assert [candidate.provider for candidate in ordered] == [
        "manual_downloads",
        "local_epub",
        "local_epub",
        "gutenberg",
    ]
    assert [candidate.title for candidate in ordered[:2]] == [
        "Fresh Manual",
        "Alpha Local",
    ]
    assert provider_query_limit(
        "local_epub",
        candidates=ordered[:2],
        effective_limit=2,
        is_default_provider_fanout=True,
    ) == 2
    assert provider_query_limit(
        "gutenberg",
        candidates=ordered[:2],
        effective_limit=2,
        is_default_provider_fanout=True,
    ) == 1
    assert provider_query_limit(
        "gutenberg",
        candidates=ordered[:2],
        effective_limit=5,
        is_default_provider_fanout=False,
    ) == 3


def test_acquisition_url_safety_helpers_share_sensitive_policy() -> None:
    assert looks_sensitive_key("pass-key")
    assert looks_sensitive_key("access_token")
    assert looks_sensitive_key("rsskey")
    assert looks_sensitive_key("privateKey")
    assert looks_sensitive_key("csrfHeader")
    assert looks_sensitive_key("credential")
    assert not looks_sensitive_key("title")
    assert strip_sensitive_url_parts(
        "https://user:pass@indexer.example.invalid/get?"
        "id=7&passkey=secret#name=demo&access_token=secret"
    ) == "https://indexer.example.invalid/get?id=7#name=demo"


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
    assert local_epub.source_label == "Books root"
    assert local_epub.discovery_media_kinds == ("book",)
    assert local_epub.default_eligible_media_kinds == ("book",)
    assert "import_local" in local_epub.capabilities

    nas_video = _provider_by_id(registry, "nas_video")
    assert nas_video.status == "available"
    assert nas_video.available is True
    assert nas_video.source_path == video_root.as_posix()
    assert nas_video.source_label == "NAS video root"
    assert nas_video.discovery_media_kinds == ("video",)
    assert nas_video.default_eligible_media_kinds == ("video",)
    assert "extract_subtitles" in nas_video.capabilities

    manual_root = tmp_path / "manual"
    manual_root.mkdir()
    registry = list_acquisition_providers(
        config={
            "ebooks_dir": str(books_root),
            "youtube_video_root": str(video_root),
            "manual_download_root": str(manual_root),
        }
    )
    manual_downloads = _provider_by_id(registry, "manual_downloads")
    assert manual_downloads.status == "available"
    assert manual_downloads.available is True
    assert manual_downloads.media_kinds == ("book", "video")
    assert manual_downloads.discovery_media_kinds == ("book", "video")
    assert manual_downloads.default_eligible_media_kinds == ("book", "video")
    assert manual_downloads.source_path is not None
    assert manual_downloads.source_label == "Manual download folders"
    assert manual_root.as_posix() in manual_downloads.source_path.split(";")


def test_manual_download_source_label_uses_configured_root_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "EBOOK_ACQUISITION_MANUAL_ROOTS",
        "EBOOK_MANUAL_DOWNLOAD_ROOTS",
        "EBOOK_ACQUISITION_MANUAL_ROOT",
        "EBOOK_MANUAL_DOWNLOAD_ROOT",
        "DOWNLOAD_STATION_COMPLETED_ROOT",
    ):
        monkeypatch.delenv(key, raising=False)

    missing_manual_root = tmp_path / "missing-manual"
    registry = list_acquisition_providers(
        config={"manual_download_root": str(missing_manual_root)}
    )

    manual_downloads = _provider_by_id(registry, "manual_downloads")
    assert manual_downloads.status == "not_configured"
    assert manual_downloads.configured is True
    assert manual_downloads.available is False
    assert manual_downloads.source_path is None
    assert manual_downloads.source_label == "Manual download folder"


def test_acquisition_provider_config_status_and_policy_notes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "secret-youtube-key")
    monkeypatch.setenv("SYNOLOGY_DOWNLOAD_STATION_URL", "https://nas.example.invalid")
    monkeypatch.setenv("SYNOLOGY_DOWNLOAD_STATION_USERNAME", "nas-user")
    monkeypatch.setenv("SYNOLOGY_DOWNLOAD_STATION_PASSWORD", "nas-secret")
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
    assert providers["openlibrary"].status == "available"
    assert providers["gutenberg"].status == "available"
    assert providers["zlibrary_attended"].status == "planned"
    assert providers["zlibrary_attended"].available is False
    assert providers["zlibrary_attended"].capabilities == ("import_local",)
    assert providers["zlibrary_attended"].discovery_media_kinds == ()
    assert providers["zlibrary_attended"].default_eligible_media_kinds == ()
    assert providers["zlibrary_attended"].rights == ("unknown", "restricted")
    assert providers["youtube_search"].default_eligible_media_kinds == ("video",)
    assert providers["newznab_torznab"].default_eligible_media_kinds == ("video",)
    assert providers["youtube_url"].default_eligible_media_kinds == ()
    assert any(
        "Direct Z-Library automation is intentionally disabled" in note
        for note in providers["zlibrary_attended"].policy_notes
    )

    serialized = str(registry.as_dict())
    assert "secret-youtube-key" not in serialized
    assert "nas.example.invalid" not in serialized
    assert "nas-user" not in serialized
    assert "nas-secret" not in serialized
    assert "indexer.example.invalid" not in serialized
    assert any("Z-Library" in note for note in registry.policy_notes)
    assert registry.default_provider_ids == {
        "book": ("local_epub",),
        "video": ("nas_video", "youtube_search", "newznab_torznab"),
    }


def test_provider_registry_and_discovery_routing_share_discoverability_map(tmp_path: Path) -> None:
    registry = list_acquisition_providers(
        config={
            "ebooks_dir": str(tmp_path / "books"),
            "youtube_video_root": str(tmp_path / "videos"),
        }
    )

    advertised = {
        provider.id: provider.discovery_media_kinds
        for provider in registry.providers
        if provider.discovery_media_kinds
    }

    assert advertised == DISCOVERY_PROVIDER_MEDIA_KINDS
    assert discovery_media_kinds_for(" LOCAL_EPUB ") == ("book",)
    assert discovery_media_kinds_for("Manual_Downloads") == ("book", "video")
    assert discovery_media_kinds_for("youtube_url") == ("video",)
    assert discovery_media_kinds_for("download_station") == ()
    assert discovery_media_kinds_for("zlibrary_attended") == ()
    assert discovery_media_kinds_for("unknown_provider") == ()
    assert registry.default_provider_ids == {
        "book": default_discovery_provider_ids("book", {}),
        "video": default_discovery_provider_ids("video", {}),
    }
    default_eligible = {
        provider.id: provider.default_eligible_media_kinds
        for provider in registry.providers
        if provider.default_eligible_media_kinds
    }
    assert default_eligible == {
        "local_epub": ("book",),
        "nas_video": ("video",),
    }


def test_default_discovery_provider_ids_are_config_aware(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("EBOOK_YOUTUBE_API_KEY", raising=False)
    for key in (
        "EBOOK_ACQUISITION_MANUAL_ROOTS",
        "EBOOK_MANUAL_DOWNLOAD_ROOTS",
        "EBOOK_ACQUISITION_MANUAL_ROOT",
        "EBOOK_MANUAL_DOWNLOAD_ROOT",
        "DOWNLOAD_STATION_COMPLETED_ROOT",
        "PROWLARR_URL",
        "TORZNAB_URL",
        "NEWZNAB_URL",
        "EBOOK_PROWLARR_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    assert default_discovery_provider_ids("book", {}) == ("local_epub",)
    assert default_discovery_provider_ids("video", {}) == ("nas_video",)
    assert default_discovery_provider_ids(
        "video",
        {"youtube_api_key": "secret-youtube-key"},
    ) == ("nas_video", "youtube_search")
    assert default_discovery_provider_ids(
        "video",
        {"prowlarr_url": "https://indexer.example.invalid"},
    ) == ("nas_video", "newznab_torznab")
    assert is_indexer_search_configured(
        {"indexer_url": "https://indexer.example.invalid"}
    )
    assert is_indexer_search_configured({}) is False
    assert default_discovery_provider_ids(" VIDEO ", {}) == ("nas_video",)
    assert default_discovery_provider_ids("audio", {}) == ()

    books_root = tmp_path / "books"
    videos_root = tmp_path / "videos"
    manual_root = tmp_path / "manual"
    books_root.mkdir()
    videos_root.mkdir()
    manual_root.mkdir()
    assert default_discovery_provider_ids(
        "book",
        {
            "ebooks_dir": str(books_root),
            "manual_download_root": str(manual_root),
        },
    ) == ("local_epub", "manual_downloads")
    assert default_discovery_provider_ids(
        "book",
        {
            "ebooks_dir": str(tmp_path / "missing-books"),
            "manual_download_root": str(manual_root),
        },
    ) == ("manual_downloads",)
    assert default_discovery_provider_ids(
        "video",
        {
            "youtube_video_root": str(videos_root),
            "manual_download_root": str(manual_root),
        },
    ) == ("nas_video", "manual_downloads")
    assert default_discovery_provider_ids(
        "video",
        {
            "youtube_video_root": str(tmp_path / "missing-videos"),
            "manual_download_root": str(manual_root),
            "youtube_api_key": "secret-youtube-key",
        },
    ) == ("manual_downloads", "youtube_search")

    monkeypatch.setenv("EBOOK_YOUTUBE_API_KEY", "env-youtube-key")
    assert default_discovery_provider_ids("video", {}) == ("nas_video", "youtube_search")

    monkeypatch.setenv("TORZNAB_URL", "https://indexer.example.invalid/api")
    assert default_discovery_provider_ids("video", {}) == (
        "nas_video",
        "youtube_search",
        "newznab_torznab",
    )
    assert "youtube_url" not in default_discovery_provider_ids(
        "video",
        {
            "youtube_video_root": str(videos_root),
            "manual_download_root": str(manual_root),
            "youtube_api_key": "secret-youtube-key",
            "prowlarr_url": "https://indexer.example.invalid",
        },
    )


def test_list_acquisition_providers_reuses_primary_root_readability_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    checked_paths: dict[str, int] = {}

    def _fake_is_readable_dir(path: Path) -> bool:
        key = path.as_posix()
        checked_paths[key] = checked_paths.get(key, 0) + 1
        return key == books_root.as_posix()

    monkeypatch.setattr(
        acquisition_provider_registry,
        "_is_readable_dir",
        _fake_is_readable_dir,
    )

    registry = acquisition_provider_registry.list_acquisition_providers(
        config={"ebooks_dir": str(books_root)}
    )

    providers = {provider.id: provider for provider in registry.providers}
    assert providers["local_epub"].available is True
    assert providers["local_epub"].default_eligible_media_kinds == ("book",)
    assert providers["nas_video"].available is False
    assert providers["nas_video"].default_eligible_media_kinds == ("video",)
    assert registry.default_provider_ids == {
        "book": ("local_epub",),
        "video": ("nas_video",),
    }
    assert checked_paths[books_root.as_posix()] == 1
    default_video_root = acquisition_provider_registry.DEFAULT_YOUTUBE_VIDEO_ROOT.as_posix()
    assert checked_paths[default_video_root] == 1


def test_provider_root_readability_uses_tolerant_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path / "books"
    regular_file = tmp_path / "notes.txt"
    directory.mkdir()
    regular_file.write_text("not a source root", encoding="utf-8")
    calls: list[str] = []

    def _fake_safe_stat(path: Path):
        calls.append(path.name)
        if path.name == "missing":
            return None
        if path.name == "synthetic-dir":
            return directory.stat()
        if path.name == "synthetic-file":
            return regular_file.stat()
        raise AssertionError("provider readiness should rely on safe_stat only")

    monkeypatch.setattr(acquisition_provider_registry, "safe_stat", _fake_safe_stat)

    assert acquisition_provider_registry._is_readable_dir(Path("/nas/synthetic-dir")) is True
    assert acquisition_provider_registry._is_readable_dir(Path("/nas/synthetic-file")) is False
    assert acquisition_provider_registry._is_readable_dir(Path("/nas/missing")) is False
    assert calls == ["synthetic-dir", "synthetic-file", "missing"]


def test_acquisition_provider_requires_download_station_credentials(monkeypatch) -> None:
    monkeypatch.delenv("SYNOLOGY_DOWNLOAD_STATION_ACCOUNT", raising=False)
    monkeypatch.delenv("SYNOLOGY_DOWNLOAD_STATION_USERNAME", raising=False)
    monkeypatch.delenv("EBOOK_DOWNLOAD_STATION_USERNAME", raising=False)
    monkeypatch.delenv("SYNOLOGY_DOWNLOAD_STATION_PASSWORD", raising=False)
    monkeypatch.delenv("EBOOK_DOWNLOAD_STATION_PASSWORD", raising=False)
    monkeypatch.setenv("SYNOLOGY_DOWNLOAD_STATION_URL", "https://nas.example.invalid")

    registry = list_acquisition_providers(config={})

    providers = {provider.id: provider for provider in registry.providers}
    download_station = providers["download_station"]
    assert download_station.status == "not_configured"
    assert download_station.available is False


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


def test_discover_local_epub_limit_keeps_newer_late_scan_candidate(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    for index in range(8):
        book = books_root / f"Old Copy {index}.epub"
        book.write_text("old", encoding="utf-8")
        old_mtime = datetime(2026, 6, index + 1, tzinfo=timezone.utc).timestamp()
        os.utime(book, (old_mtime, old_mtime))
    newest = books_root / "Zulu Fresh Copy.epub"
    newest.write_text("new", encoding="utf-8")
    newest_mtime = datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()
    os.utime(newest, (newest_mtime, newest_mtime))

    result = discover_acquisition_candidates(
        media_kind="book",
        query="",
        provider="local_epub",
        limit=1,
        config={"ebooks_dir": str(books_root)},
    )

    assert [candidate.local_path for candidate in result.candidates] == [
        "Zulu Fresh Copy.epub"
    ]


def test_default_book_discovery_fans_out_before_limit_so_manual_inbox_can_win(
    tmp_path: Path,
) -> None:
    books_root = tmp_path / "books"
    manual_root = tmp_path / "manual"
    books_root.mkdir()
    manual_root.mkdir()
    library_book = books_root / "Older Library Copy.epub"
    manual_book = manual_root / "Fresh Download Station Copy.epub"
    library_book.write_text("old", encoding="utf-8")
    manual_book.write_text("new", encoding="utf-8")
    old_mtime = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
    new_mtime = datetime(2026, 6, 25, tzinfo=timezone.utc).timestamp()
    os.utime(library_book, (old_mtime, old_mtime))
    os.utime(manual_book, (new_mtime, new_mtime))

    result = discover_acquisition_candidates(
        media_kind="book",
        query="",
        limit=1,
        config={
            "ebooks_dir": str(books_root),
            "manual_download_root": str(manual_root),
        },
    )

    assert result.providers_queried == ("local_epub", "manual_downloads")
    assert [candidate.local_path for candidate in result.candidates] == [
        manual_book.as_posix()
    ]
    assert result.candidates[0].provider == "manual_downloads"
    assert result.candidates[0].metadata["source_kind"] == "manual_download"


def test_backend_defaults_provider_id_uses_default_book_discovery_fanout(
    tmp_path: Path,
) -> None:
    books_root = tmp_path / "books"
    manual_root = tmp_path / "manual"
    books_root.mkdir()
    manual_root.mkdir()
    library_book = books_root / "Local Origin.epub"
    manual_book = manual_root / "Manual Origin.epub"
    library_book.write_text("local", encoding="utf-8")
    manual_book.write_text("manual", encoding="utf-8")

    result = discover_acquisition_candidates(
        media_kind="book",
        query="origin",
        provider=" BACKEND_DEFAULTS ",
        config={
            "ebooks_dir": str(books_root),
            "manual_download_root": str(manual_root),
        },
    )

    assert result.providers_queried == ("local_epub", "manual_downloads")
    assert {candidate.provider for candidate in result.candidates} == {
        "local_epub",
        "manual_downloads",
    }
    assert {candidate.title for candidate in result.candidates} == {
        "Local Origin",
        "Manual Origin",
    }


def test_default_discovery_keeps_local_limits_but_probes_remote_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int]] = []

    def _candidate(
        provider: str,
        index: int,
        *,
        modified_at: datetime | None = None,
    ) -> acquisition_discovery.AcquisitionCandidate:
        return acquisition_discovery.AcquisitionCandidate(
            candidate_id=f"{provider}:{index}",
            provider=provider,
            media_kind="book",
            title=f"{provider} {index}",
            rights="user_provided" if provider != "gutenberg" else "public_domain",
            capabilities=("metadata",),
            candidate_token=_candidate_token({"provider": provider, "index": index}),
            modified_at=modified_at,
        )

    def _fake_local_epubs(config, query, limit):
        calls.append(("local_epub", limit))
        return [
            _candidate("local_epub", index, modified_at=datetime(2026, 6, index + 1))
            for index in range(limit)
        ]

    def _fake_manual_downloads(config, media_kind, query, limit):
        calls.append(("manual_downloads", limit))
        return [
            _candidate(
                "manual_downloads",
                index,
                modified_at=datetime(2026, 7, index + 1),
            )
            for index in range(limit)
        ]

    def _fake_gutenberg(query, limit, *, language, session):
        calls.append(("gutenberg", limit))
        return [_candidate("gutenberg", index) for index in range(limit)]

    monkeypatch.setattr(
        acquisition_discovery,
        "default_discovery_provider_ids",
        lambda media_kind, config: ("local_epub", "manual_downloads", "gutenberg"),
    )
    monkeypatch.setattr(acquisition_discovery, "_discover_local_epubs", _fake_local_epubs)
    monkeypatch.setattr(
        acquisition_discovery,
        "_discover_manual_downloads",
        _fake_manual_downloads,
    )
    monkeypatch.setattr(acquisition_discovery, "_discover_gutenberg", _fake_gutenberg)

    result = discover_acquisition_candidates(
        media_kind="book",
        query="",
        limit=2,
        config={},
    )

    assert calls == [
        ("local_epub", 2),
        ("manual_downloads", 2),
        ("gutenberg", 1),
    ]
    assert result.providers_queried == ("local_epub", "manual_downloads", "gutenberg")
    assert [candidate.provider for candidate in result.candidates] == [
        "manual_downloads",
        "manual_downloads",
    ]


def test_discover_zero_limit_skips_provider_scan(tmp_path: Path, monkeypatch) -> None:
    def _fail_scan(*args, **kwargs):
        raise AssertionError("zero-limit discovery should not scan provider roots")

    monkeypatch.setattr(acquisition_discovery, "iter_visible_source_files", _fail_scan)

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


def test_discover_manual_download_epubs_uses_configured_roots(tmp_path: Path) -> None:
    manual_root = tmp_path / "manual"
    manual_root.mkdir()
    book_path = manual_root / "The Da Vinci Code.epub"
    book_path.write_text("demo", encoding="utf-8")

    result = discover_acquisition_candidates(
        media_kind="book",
        query="vinci",
        provider="manual_downloads",
        config={"manual_download_root": str(manual_root)},
    )

    assert result.providers_queried == ("manual_downloads",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "manual_downloads"
    assert candidate.media_kind == "book"
    assert candidate.local_path == book_path.as_posix()
    assert candidate.rights == "user_provided"
    assert candidate.metadata["source_root"] == manual_root.as_posix()


def test_discover_manual_download_epubs_limit_keeps_newer_late_root_candidate(
    tmp_path: Path,
) -> None:
    older_root = tmp_path / "older"
    newer_root = tmp_path / "newer"
    older_root.mkdir()
    newer_root.mkdir()
    older = older_root / "Alpha Older.epub"
    newer = newer_root / "Zulu Newer.epub"
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    older_mtime = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
    newer_mtime = datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()
    os.utime(older, (older_mtime, older_mtime))
    os.utime(newer, (newer_mtime, newer_mtime))

    result = discover_acquisition_candidates(
        media_kind="book",
        query="",
        provider="manual_downloads",
        limit=1,
        config={"manual_download_roots": [str(older_root), str(newer_root)]},
    )

    assert [candidate.local_path for candidate in result.candidates] == [
        newer.as_posix()
    ]


def test_discover_manual_download_epubs_limit_uses_title_tie_break(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    zulu = first_root / "Zulu Same Time.epub"
    alpha = second_root / "Alpha Same Time.epub"
    zulu.write_text("zulu", encoding="utf-8")
    alpha.write_text("alpha", encoding="utf-8")
    shared_mtime = datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()
    os.utime(zulu, (shared_mtime, shared_mtime))
    os.utime(alpha, (shared_mtime, shared_mtime))

    result = discover_acquisition_candidates(
        media_kind="book",
        query="same",
        provider="manual_downloads",
        limit=1,
        config={"manual_download_roots": [str(first_root), str(second_root)]},
    )

    assert [candidate.local_path for candidate in result.candidates] == [
        alpha.as_posix()
    ]


def test_discover_manual_download_epubs_reuses_video_download_root(tmp_path: Path) -> None:
    download_root = tmp_path / "download-station"
    download_root.mkdir()
    book_path = download_root / "Deception Point.epub"
    book_path.write_text("demo", encoding="utf-8")

    result = discover_acquisition_candidates(
        media_kind="book",
        query="deception",
        provider="manual_downloads",
        config={"youtube_video_root": str(download_root)},
    )

    assert result.providers_queried == ("manual_downloads",)
    assert len(result.candidates) == 1
    assert result.candidates[0].local_path == book_path.as_posix()


def test_discover_manual_download_videos_include_subtitle_hints(tmp_path: Path) -> None:
    manual_root = tmp_path / "manual"
    manual_root.mkdir()
    video_path = manual_root / "Demo Lecture.mp4"
    subtitle_path = manual_root / "Demo Lecture.en.srt"
    video_path.write_bytes(b"video")
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")

    result = discover_acquisition_candidates(
        media_kind="video",
        query="demo",
        provider="manual_downloads",
        config={"manual_download_root": str(manual_root)},
    )

    assert result.providers_queried == ("manual_downloads",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "manual_downloads"
    assert candidate.local_path == video_path.as_posix()
    assert candidate.subtitles[0].filename == subtitle_path.name


def test_discover_manual_download_videos_does_not_recover_partial_files(tmp_path: Path) -> None:
    manual_root = tmp_path / "manual"
    manual_root.mkdir()
    partial_path = manual_root / "Almost Ready.mp4.part"
    partial_path.write_bytes(b"partial-video")

    result = discover_acquisition_candidates(
        media_kind="video",
        query="ready",
        provider="manual_downloads",
        config={"manual_download_root": str(manual_root)},
    )

    assert result.providers_queried == ("manual_downloads",)
    assert result.candidates == ()
    assert partial_path.exists()
    assert not (manual_root / "Almost Ready.mp4").exists()


def test_discover_manual_download_videos_are_newest_first_across_roots(tmp_path: Path) -> None:
    old_root = tmp_path / "old-root"
    new_root = tmp_path / "new-root"
    old_root.mkdir()
    new_root.mkdir()
    old_video = old_root / "Old Download.mp4"
    new_video = new_root / "Fresh Download.mp4"
    old_video.write_bytes(b"old-video")
    new_video.write_bytes(b"new-video")
    old_mtime = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
    new_mtime = datetime(2026, 6, 25, tzinfo=timezone.utc).timestamp()
    os.utime(old_video, (old_mtime, old_mtime))
    os.utime(old_root, (old_mtime, old_mtime))
    os.utime(new_video, (new_mtime, new_mtime))
    os.utime(new_root, (new_mtime, new_mtime))

    result = discover_acquisition_candidates(
        media_kind="video",
        query="download",
        provider="manual_downloads",
        limit=1,
        config={"manual_download_roots": [str(old_root), str(new_root)]},
    )

    assert result.providers_queried == ("manual_downloads",)
    assert [candidate.local_path for candidate in result.candidates] == [
        new_video.as_posix()
    ]


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


def test_discover_nas_video_limit_keeps_newer_late_folder_candidate(tmp_path: Path) -> None:
    video_root = tmp_path / "videos"
    old_folder = video_root / "alpha-old"
    new_folder = video_root / "zulu-new"
    old_folder.mkdir(parents=True)
    new_folder.mkdir()
    old_video = old_folder / "Old Clip.mp4"
    new_video = new_folder / "Fresh Clip.mp4"
    old_video.write_bytes(b"old-video")
    new_video.write_bytes(b"new-video")
    old_mtime = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
    new_mtime = datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp()
    os.utime(old_video, (old_mtime, old_mtime))
    os.utime(old_folder, (old_mtime, old_mtime))
    os.utime(new_video, (new_mtime, new_mtime))
    os.utime(new_folder, (new_mtime, new_mtime))

    result = discover_acquisition_candidates(
        media_kind="video",
        query="",
        provider="nas_video",
        limit=1,
        config={"youtube_video_root": str(video_root)},
    )

    assert result.providers_queried == ("nas_video",)
    assert [candidate.local_path for candidate in result.candidates] == [
        new_video.as_posix()
    ]


def test_discover_nas_video_candidates_does_not_recover_partial_files(tmp_path: Path) -> None:
    video_root = tmp_path / "videos"
    video_root.mkdir()
    partial_path = video_root / "NAS Clip.mkv.part"
    partial_path.write_bytes(b"partial-video")

    result = discover_acquisition_candidates(
        media_kind="video",
        query="clip",
        provider="nas_video",
        config={"youtube_video_root": str(video_root)},
    )

    assert result.providers_queried == ("nas_video",)
    assert result.candidates == ()
    assert partial_path.exists()
    assert not (video_root / "NAS Clip.mkv").exists()


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


def test_discover_internet_archive_filters_plain_epub_candidates() -> None:
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

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if url.endswith("/advancedsearch.php"):
                return _FakeResponse(
                    {
                        "response": {
                            "docs": [
                                {
                                    "identifier": "demo_public_book",
                                    "title": "Demo Public Book",
                                    "creator": ["Archive Author"],
                                    "language": ["eng"],
                                    "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
                                    "downloads": 42,
                                },
                                {
                                    "identifier": "restricted_book",
                                    "title": "Restricted Book",
                                },
                            ]
                        }
                    }
                )
            if url.endswith("/demo_public_book"):
                return _FakeResponse(
                    {
                        "metadata": {
                            "title": "Demo Public Book",
                            "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
                        },
                        "files": [
                            {"name": "demo_public_book_encrypted.epub", "size": "100"},
                            {"name": "demo_public_book.epub", "size": "4567", "format": "EPUB"},
                        ],
                    }
                )
            return _FakeResponse(
                {
                    "metadata": {"access-restricted-item": "true"},
                    "files": [{"name": "restricted_book.epub", "size": "999"}],
                }
            )

    session = _FakeSession()

    result = discover_acquisition_candidates(
        media_kind="book",
        query="demo public",
        provider="internet_archive",
        language="English",
        limit=5,
        session=session,
    )

    assert result.providers_queried == ("internet_archive",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "internet_archive"
    assert candidate.rights == "public_domain"
    assert candidate.title == "Demo Public Book"
    assert candidate.contributors == ("Archive Author",)
    assert candidate.source_url == "https://archive.org/details/demo_public_book"
    assert candidate.cover_url == "https://archive.org/services/img/demo_public_book"
    assert candidate.size_bytes == 4567
    assert candidate.metadata["identifier"] == "demo_public_book"
    assert candidate.metadata["epub_file"] == "demo_public_book.epub"
    assert candidate.metadata["epub_url"] == "https://archive.org/download/demo_public_book/demo_public_book.epub"
    assert session.calls[0][0].endswith("/advancedsearch.php")
    assert "mediatype:texts" in session.calls[0][1]["params"]["q"]
    assert "-access-restricted-item:true" in session.calls[0][1]["params"]["q"]
    assert "language:en" in session.calls[0][1]["params"]["q"]


def test_discover_internet_archive_source_ids_bridge_openlibrary_ids() -> None:
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

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if url.endswith("/demo_public_book"):
                return _FakeResponse(
                    {
                        "metadata": {
                            "title": "Demo Public Book",
                            "creator": ["Archive Author"],
                            "language": ["eng"],
                            "date": "1910",
                            "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
                        },
                        "files": [
                            {"name": "demo_public_book_encrypted.epub", "size": "100"},
                            {"name": "demo_public_book.epub", "size": "4567"},
                        ],
                    }
                )
            return _FakeResponse(
                {
                    "metadata": {
                        "title": "Restricted Book",
                        "access-restricted-item": "true",
                    },
                    "files": [{"name": "restricted_book.epub", "size": "999"}],
                }
            )

    session = _FakeSession()

    result = discover_acquisition_candidates(
        media_kind="book",
        query="ignored when source ids are supplied",
        provider="internet_archive",
        source_ids=["demo_public_book", "restricted_book", "demo_public_book"],
        limit=5,
        session=session,
    )

    assert result.providers_queried == ("internet_archive",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.candidate_id == "internet_archive:demo_public_book"
    assert candidate.title == "Demo Public Book"
    assert candidate.year == 1910
    assert candidate.rights == "public_domain"
    assert candidate.metadata["identifier"] == "demo_public_book"
    assert candidate.metadata["epub_file"] == "demo_public_book.epub"
    assert [call[0].rsplit("/", 1)[-1] for call in session.calls] == [
        "demo_public_book",
        "restricted_book",
    ]
    assert not any(call[0].endswith("/advancedsearch.php") for call in session.calls)


def test_discover_internet_archive_source_ids_reject_unsafe_identifiers() -> None:
    with pytest.raises(ValueError, match="source_id"):
        discover_acquisition_candidates(
            media_kind="book",
            query="",
            provider="internet_archive",
            source_ids=["../secret"],
        )


def test_discover_openlibrary_normalizes_metadata_only_candidates() -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "docs": [
                    {
                        "key": "/works/OL45883W",
                        "title": "Demo Metadata Book",
                        "author_name": ["Metadata Author"],
                        "first_publish_year": 2003,
                        "language": ["eng"],
                        "cover_i": 12345,
                        "isbn": ["9780385504201"],
                        "edition_key": ["OL123M"],
                        "ia": ["demo_metadata_book"],
                        "has_fulltext": True,
                        "availability": {"status": "borrow_available"},
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
        query="demo metadata",
        provider="openlibrary",
        language="English",
        limit=5,
        session=session,
    )

    assert result.providers_queried == ("openlibrary",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "openlibrary"
    assert candidate.rights == "unknown"
    assert candidate.requires_confirmation is False
    assert candidate.capabilities == ("search", "metadata")
    assert candidate.local_path is None
    assert candidate.title == "Demo Metadata Book"
    assert candidate.contributors == ("Metadata Author",)
    assert candidate.language == "eng"
    assert candidate.year == 2003
    assert candidate.source_url == "https://openlibrary.org/works/OL45883W"
    assert candidate.cover_url == "https://covers.openlibrary.org/b/id/12345-L.jpg"
    assert candidate.metadata["source_kind"] == "openlibrary"
    assert candidate.metadata["book_title"] == "Demo Metadata Book"
    assert candidate.metadata["book_author"] == "Metadata Author"
    assert candidate.metadata["book_year"] == "2003"
    assert candidate.metadata["book_language"] == "eng"
    assert candidate.metadata["cover_url"] == "https://covers.openlibrary.org/b/id/12345-L.jpg"
    assert candidate.metadata["openlibrary_work_key"] == "/works/OL45883W"
    assert candidate.metadata["openlibrary_work_url"] == "https://openlibrary.org/works/OL45883W"
    assert candidate.metadata["openlibrary_book_key"] == "/books/OL123M"
    assert candidate.metadata["isbn"] == "9780385504201"
    assert candidate.metadata["book_isbn"] == "9780385504201"
    assert candidate.metadata["internet_archive_ids"] == ["demo_metadata_book"]
    assert candidate.metadata["media_metadata_lookup"]["provider"] == "openlibrary"
    assert candidate.metadata["media_metadata_lookup"]["book"]["title"] == "Demo Metadata Book"
    assert candidate.metadata["has_fulltext"] is True
    assert session.calls[0][0].endswith("/search.json")
    assert session.calls[0][1]["q"] == "demo metadata"
    assert session.calls[0][1]["language"] == "en"
    assert "availability" in session.calls[0][1]["fields"]


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
            "provider": " GUTENBERG ",
            "media_kind": " BOOK ",
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


def test_acquire_candidate_reserves_destination_with_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, *, chunk_size):
            yield b"new epub"

        def close(self) -> None:
            return None

    class _FakeSession:
        def get(self, url, *, stream, timeout, allow_redirects):
            return _FakeResponse()

    books_root = tmp_path / "books"
    books_root.mkdir()
    (books_root / "Frankenstein.epub").write_bytes(b"existing")
    original_exists = Path.exists

    def fail_books_root_exists(path: Path) -> bool:
        if books_root in path.parents or path == books_root:
            raise AssertionError("acquired EPUB reservation should use safe_stat instead of exists")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_books_root_exists)
    token = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "gutenberg_id": 84,
            "epub_url": "https://www.gutenberg.org/ebooks/84.epub3.images",
        }
    )

    artifact = acquire_acquisition_candidate(
        candidate_token=token,
        confirmed=True,
        filename="Frankenstein.epub",
        config={"ebooks_dir": str(books_root)},
        session=_FakeSession(),
    )

    assert artifact.status == "completed"
    assert artifact.local_path == "Frankenstein-1.epub"
    assert (books_root / "Frankenstein.epub").read_bytes() == b"existing"
    assert (books_root / "Frankenstein-1.epub").read_bytes() == b"new epub"


def test_acquire_candidate_verifies_downloaded_epub_with_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, *, chunk_size):
            yield b"new epub"

        def close(self) -> None:
            return None

    class _FakeSession:
        def get(self, url, *, stream, timeout, allow_redirects):
            return _FakeResponse()

    books_root = tmp_path / "books"
    token = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "gutenberg_id": 84,
            "epub_url": "https://www.gutenberg.org/ebooks/84.epub3.images",
        }
    )
    original_safe_stat = acquisition_acquire.safe_stat

    def fake_safe_stat(path: Path):
        if path == books_root / "Frankenstein.epub":
            return None
        return original_safe_stat(path)

    monkeypatch.setattr(acquisition_acquire, "safe_stat", fake_safe_stat)

    with pytest.raises(ValueError, match="downloaded EPUB could not be verified"):
        acquire_acquisition_candidate(
            candidate_token=token,
            confirmed=True,
            filename="Frankenstein.epub",
            config={"ebooks_dir": str(books_root)},
            session=_FakeSession(),
        )


def test_acquire_internet_archive_candidate_persists_epub_in_books_root(tmp_path: Path) -> None:
    class _FakeResponse:
        status_code = 200

        def __init__(self) -> None:
            self.closed = False

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, *, chunk_size):
            yield b"archive"
            yield b" epub"

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
            "provider": "internet_archive",
            "media_kind": "book",
            "identifier": "demo_public_book",
            "epub_url": "https://archive.org/download/demo_public_book/demo_public_book.epub",
        }
    )
    session = _FakeSession()

    artifact = acquire_acquisition_candidate(
        candidate_token=token,
        confirmed=True,
        config={"ebooks_dir": str(books_root)},
        session=session,
    )

    assert artifact.status == "completed"
    assert artifact.provider == "internet_archive"
    assert artifact.media_kind == "book"
    assert artifact.local_path == "demo_public_book.epub"
    assert (books_root / "demo_public_book.epub").read_bytes() == b"archive epub"
    assert artifact.metadata["identifier"] == "demo_public_book"
    assert session.calls == [
        ("https://archive.org/download/demo_public_book/demo_public_book.epub", True, 30, False)
    ]
    assert session.response.closed is True


def test_acquired_internet_archive_artifact_prepares_public_provenance(
    tmp_path: Path,
) -> None:
    class _FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, *, chunk_size):
            yield b"archive epub"

        def close(self) -> None:
            return None

    class _FakeSession:
        def get(self, url, *, stream, timeout, allow_redirects):
            return _FakeResponse()

    books_root = tmp_path / "books"
    source_url = "https://archive.org/download/demo_public_book/demo_public_book.epub"
    token = _candidate_token(
        {
            "provider": "internet_archive",
            "media_kind": "book",
            "identifier": "demo_public_book",
            "epub_url": source_url,
        }
    )

    artifact = acquire_acquisition_candidate(
        candidate_token=token,
        confirmed=True,
        config={"ebooks_dir": str(books_root)},
        session=_FakeSession(),
    )
    prepared = prepare_acquisition_artifact(
        artifact_id=artifact.artifact_id,
        config={"ebooks_dir": str(books_root)},
    )

    assert prepared.provider == "internet_archive"
    assert prepared.input_file == "demo_public_book.epub"
    assert prepared.metadata["source_provider"] == "internet_archive"
    assert prepared.metadata["acquisition_provider"] == "internet_archive"
    assert prepared.metadata["acquisition_candidate_id"] == "internet_archive:demo_public_book"
    assert prepared.metadata["identifier"] == "demo_public_book"
    assert prepared.metadata["source_url"] == source_url


def test_prepare_acquisition_artifact_resolves_local_epub_source(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    (books_root / "Origin.epub").write_text("demo", encoding="utf-8")
    artifact_id = _candidate_token(
        {
            "provider": " LOCAL_EPUB ",
            "media_kind": " BOOK ",
            "source_kind": " LOCAL_EPUB ",
            "path": "Origin.epub",
        }
    )

    prepared = prepare_acquisition_artifact(
        artifact_id=artifact_id,
        config={"ebooks_dir": str(books_root)},
    )

    assert prepared.provider == "local_epub"
    assert prepared.media_kind == "book"
    assert prepared.input_file == "Origin.epub"
    assert prepared.local_path == "Origin.epub"
    assert prepared.next_actions == ("create_book_job", "load_content_index")
    assert prepared.source_kind == "local_epub"
    assert prepared.metadata["source_kind"] == "local_epub"
    assert prepared.metadata["source_path"] == "Origin.epub"
    assert prepared.metadata["source_provider"] == "local_epub"
    assert prepared.metadata["acquisition_candidate_id"] == "local_epub:Origin.epub"


def test_prepare_acquisition_artifact_uses_safe_stat_for_local_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    source = books_root / "Origin.epub"
    source.write_text("demo", encoding="utf-8")
    artifact_id = _candidate_token(
        {
            "provider": "local_epub",
            "media_kind": "book",
            "path": "Origin.epub",
        }
    )

    def fail_exists(_path: Path) -> bool:
        raise AssertionError("prepared artifact checks should use safe_stat instead of exists")

    def fail_is_file(_path: Path) -> bool:
        raise AssertionError("prepared artifact checks should use safe_stat instead of is_file")

    monkeypatch.setattr(Path, "exists", fail_exists)
    monkeypatch.setattr(Path, "is_file", fail_is_file)
    monkeypatch.setattr(
        acquisition_acquire,
        "safe_stat",
        lambda path: source.stat() if path == source.resolve() else None,
    )

    prepared = prepare_acquisition_artifact(
        artifact_id=artifact_id,
        config={"ebooks_dir": str(books_root)},
    )

    assert prepared.input_file == "Origin.epub"
    assert prepared.metadata["source_path"] == "Origin.epub"


def test_prepare_acquisition_artifact_reports_vanished_local_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    source = books_root / "Origin.epub"
    source.write_text("demo", encoding="utf-8")
    artifact_id = _candidate_token(
        {
            "provider": "local_epub",
            "media_kind": "book",
            "path": "Origin.epub",
        }
    )

    monkeypatch.setattr(
        acquisition_acquire,
        "safe_stat",
        lambda path: None if path == source.resolve() else path.stat(),
    )

    with pytest.raises(ValueError, match="artifact path does not exist"):
        prepare_acquisition_artifact(
            artifact_id=artifact_id,
            config={"ebooks_dir": str(books_root)},
        )


def test_prepare_acquisition_artifact_resolves_acquired_public_epub(
    tmp_path: Path,
) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    (books_root / "Frankenstein.epub").write_text("demo", encoding="utf-8")
    artifact_id = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "path": "Frankenstein.epub",
            "gutenberg_id": 84,
            "source_url": "https://www.gutenberg.org/ebooks/84.epub3.images",
        }
    )

    prepared = prepare_acquisition_artifact(
        artifact_id=artifact_id,
        config={"ebooks_dir": str(books_root)},
    )

    assert prepared.provider == "gutenberg"
    assert prepared.input_file == "Frankenstein.epub"
    assert prepared.metadata["source_provider"] == "gutenberg"
    assert prepared.metadata["acquisition_candidate_id"] == "gutenberg:84"
    assert prepared.metadata["gutenberg_id"] == 84
    assert prepared.metadata["source_url"].startswith("https://www.gutenberg.org/")


def test_prepare_acquisition_artifact_preserves_explicit_candidate_id(
    tmp_path: Path,
) -> None:
    manual_root = tmp_path / "manual"
    manual_root.mkdir()
    video_path = manual_root / "Readable History.mkv"
    video_path.write_bytes(b"video")
    artifact_id = _candidate_token(
        {
            "provider": "manual_downloads",
            "media_kind": "video",
            "source_kind": "manual_download",
            "source_provider": "newznab_torznab",
            "acquisition_provider": "download_station",
            "path": video_path.as_posix(),
            "candidate_id": "newznab_torznab:readable-history",
        }
    )

    prepared = prepare_acquisition_artifact(
        artifact_id=artifact_id,
        config={"manual_download_root": str(manual_root)},
    )

    assert prepared.video_path == video_path.as_posix()
    assert prepared.source_kind == "manual_download"
    assert prepared.metadata["source_provider"] == "newznab_torznab"
    assert prepared.metadata["acquisition_provider"] == "download_station"
    assert prepared.metadata["acquisition_candidate_id"] == "newznab_torznab:readable-history"


def test_prepare_acquisition_artifact_rejects_path_escape(tmp_path: Path) -> None:
    books_root = tmp_path / "books"
    books_root.mkdir()
    outside = tmp_path / "outside.epub"
    outside.write_text("demo", encoding="utf-8")
    artifact_id = _candidate_token(
        {
            "provider": "local_epub",
            "media_kind": "book",
            "path": "../outside.epub",
        }
    )

    with pytest.raises(ValueError, match="outside configured source roots"):
        prepare_acquisition_artifact(
            artifact_id=artifact_id,
            config={"ebooks_dir": str(books_root)},
        )


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

    untrusted_archive_token = _candidate_token(
        {
            "provider": "internet_archive",
            "media_kind": "book",
            "identifier": "demo_public_book",
            "epub_url": "http://127.0.0.1/internal.epub",
        }
    )
    with pytest.raises(ValueError, match="allowed Internet Archive"):
        acquire_acquisition_candidate(
            candidate_token=untrusted_archive_token,
            confirmed=True,
            config={"ebooks_dir": str(tmp_path)},
        )


def test_acquire_candidate_rejects_unsigned_or_tampered_tokens(tmp_path: Path) -> None:
    unsigned_token = "eyJlcHViX3VybCI6Imh0dHBzOi8vd3d3Lmd1dGVuYmVyZy5vcmcvZWJvb2tzLzg0LmVwdWIzLmltYWdlcyIsImd1dGVuYmVyZ19pZCI6ODQsIm1lZGlhX2tpbmQiOiJib29rIiwicHJvdmlkZXIiOiJndXRlbmJlcmcifQ"
    with pytest.raises(ValueError, match="candidate_token is invalid"):
        acquire_acquisition_candidate(
            candidate_token=unsigned_token,
            confirmed=True,
            config={"ebooks_dir": str(tmp_path)},
        )

    signed_token = _candidate_token(
        {
            "provider": "gutenberg",
            "media_kind": "book",
            "gutenberg_id": 84,
            "epub_url": "https://www.gutenberg.org/ebooks/84.epub3.images",
        }
    )
    tampered_token = f"{signed_token[:-1]}{'A' if signed_token[-1] != 'A' else 'B'}"
    with pytest.raises(ValueError, match="candidate_token is invalid"):
        acquire_acquisition_candidate(
            candidate_token=tampered_token,
            confirmed=True,
            config={"ebooks_dir": str(tmp_path)},
        )


def test_acquisition_tokens_reject_secret_bearing_payloads() -> None:
    signed = _candidate_token(
        {
            "provider": "internet_archive",
            "media_kind": "book",
            "identifier": "demo_public_book",
            "epub_url": "https://archive.org/download/demo_public_book/demo_public_book.epub",
        }
    )
    assert decode_acquisition_token(signed)["identifier"] == "demo_public_book"

    with pytest.raises(ValueError, match="sensitive field"):
        encode_acquisition_token(
            {
                "provider": "newznab_torznab",
                "media_kind": "video",
                "api_key": "secret-indexer-key",
            }
        )

    with pytest.raises(ValueError, match="sensitive URL query field"):
        encode_acquisition_token(
            {
                "provider": "newznab_torznab",
                "media_kind": "video",
                "source_uri": "https://indexer.example.invalid/download/123?apikey=secret-indexer-key",
            }
        )

    for query_key in ("passkey", "authkey", "rsskey"):
        with pytest.raises(ValueError, match="sensitive URL query field"):
            encode_acquisition_token(
                {
                    "provider": "newznab_torznab",
                    "media_kind": "video",
                    "source_uri": f"https://indexer.example.invalid/download/123?{query_key}=secret-indexer-key",
                }
            )

    with pytest.raises(ValueError, match="URL credentials"):
        encode_acquisition_token(
            {
                "provider": "newznab_torznab",
                "media_kind": "video",
                "source_uri": "https://secret-user:secret-pass@indexer.example.invalid/download/123",
            }
        )

    with pytest.raises(ValueError, match="sensitive URL fragment field"):
        encode_acquisition_token(
            {
                "provider": "newznab_torznab",
                "media_kind": "video",
                "source_uri": "https://indexer.example.invalid/download/123#access_token=secret-fragment",
            }
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


def test_youtube_discovery_helpers_normalize_metadata_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert youtube_discovery.parse_youtube_url_or_id(
        "https://www.youtube.com/watch?v=AbC123_xYz9&t=42s"
    ) == "AbC123_xYz9"
    assert youtube_discovery.parse_youtube_url_or_id(
        "https://www.youtube.com/live/AbC123_xYz9?feature=share"
    ) == "AbC123_xYz9"
    assert youtube_discovery.parse_youtube_url_or_id("not-a-youtube-url") is None
    assert youtube_discovery.youtube_video_id(
        {"id": {"videoId": "AbC123_xYz9"}}
    ) == "AbC123_xYz9"
    assert youtube_discovery.youtube_thumbnail(
        {
            "thumbnails": {
                "default": {"url": "https://img.example/default.jpg"},
                "high": {"url": "https://img.example/high.jpg"},
            }
        }
    ) == "https://img.example/high.jpg"
    assert youtube_discovery.parse_iso8601_duration("P1DT2H3M4S") == 93784
    assert youtube_discovery.parse_iso8601_duration("not-duration") is None

    monkeypatch.setenv("EBOOK_YOUTUBE_API_KEY", "env-youtube-key")
    assert youtube_discovery.youtube_api_key({}) == "env-youtube-key"
    assert youtube_discovery.youtube_api_key(
        {"youtube_data_api_key": " config-youtube-key "}
    ) == "config-youtube-key"

    class _FakeErrorResponse:
        def json(self):
            return {
                "error": {
                    "errors": [
                        {
                            "reason": "quotaExceeded",
                            "message": "secret-youtube-key should not leak",
                        }
                    ]
                }
            }

    assert youtube_discovery.youtube_error_reason(_FakeErrorResponse()) == "quotaExceeded"


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


@pytest.mark.parametrize(
    ("query", "video_id"),
    [
        ("https://www.youtube.com/watch?v=AbC123_xYz9&t=42s", "AbC123_xYz9"),
        ("youtube.com/watch?v=AbC123_xYz9", "AbC123_xYz9"),
        ("https://youtu.be/AbC123_xYz9?si=demo", "AbC123_xYz9"),
        ("https://www.youtube.com/shorts/AbC123_xYz9", "AbC123_xYz9"),
        ("AbC123_xYz9", "AbC123_xYz9"),
    ],
)
def test_discover_youtube_url_normalizes_direct_handoff(query: str, video_id: str) -> None:
    result = discover_acquisition_candidates(
        media_kind="video",
        query=query,
        provider="youtube_url",
        config={},
    )

    assert result.providers_queried == ("youtube_url",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "youtube_url"
    assert candidate.candidate_id == f"youtube_url:{video_id}"
    assert candidate.source_url == f"https://www.youtube.com/watch?v={video_id}"
    assert candidate.requires_confirmation is True
    assert candidate.metadata == {
        "source_kind": "youtube",
        "youtube_video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
    }
    assert "video/subtitle acquisition is a separate reviewed step" in candidate.policy_notes[0]


def test_discover_youtube_url_requires_parseable_video_id() -> None:
    result = discover_acquisition_candidates(
        media_kind="video",
        query="https://example.invalid/not-youtube",
        provider="youtube_url",
        config={},
    )

    assert result.providers_queried == ("youtube_url",)
    assert result.candidates == ()


def test_discover_youtube_search_maps_quota_errors_without_secret() -> None:
    class _FakeResponse:
        status_code = 403

        def raise_for_status(self) -> None:
            error = requests.HTTPError("403 Client Error: quota")
            error.response = self
            raise error

        def json(self):
            return {
                "error": {
                    "errors": [
                        {
                            "reason": "quotaExceeded",
                            "message": "secret-youtube-key should not leak",
                        }
                    ]
                }
            }

    class _FakeSession:
        def get(self, url, *, params, timeout):
            return _FakeResponse()

    with pytest.raises(AcquisitionProviderDiscoveryError) as exc_info:
        discover_acquisition_candidates(
            media_kind="video",
            query="demo",
            provider="youtube_search",
            config={"youtube_api_key": "secret-youtube-key"},
            session=_FakeSession(),
        )

    message = str(exc_info.value)
    assert "quota" in message.casefold()
    assert "secret-youtube-key" not in message
    assert exc_info.value.reason == "quotaExceeded"


def test_indexer_discovery_helpers_normalize_config_urls_and_xml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROWLARR_URL", " https://env-indexer.example.invalid ")
    monkeypatch.setenv("TORZNAB_API_KEY", " env-indexer-key ")
    monkeypatch.setenv("TORZNAB_VIDEO_CATEGORY", " 5000 ")

    assert indexer_discovery.indexer_endpoint({}) == "https://env-indexer.example.invalid"
    assert indexer_discovery.indexer_endpoint(
        {"newznab_url": " https://config-indexer.example.invalid/root "}
    ) == "https://config-indexer.example.invalid/root"
    assert indexer_discovery.indexer_api_key({}) == "env-indexer-key"
    assert indexer_discovery.indexer_api_key(
        {"indexer_api_key": " config-indexer-key "}
    ) == "config-indexer-key"
    assert indexer_discovery.indexer_category({}) == "5000"
    assert indexer_discovery.indexer_category({"indexer_video_category": 2000}) == "2000"
    assert indexer_discovery.newznab_api_url(
        "https://indexer.example.invalid/feed?apikey=secret-indexer-key&cat=5000"
    ) == "https://indexer.example.invalid/feed/api?cat=5000"

    item = ET.fromstring(
        """
        <item xmlns:torznab="http://torznab.com/schemas/2015/feed">
          <title>Readable History S01E01 1080p</title>
          <pubDate>Thu, 25 Jun 2026 12:05:00 +0000</pubDate>
          <enclosure url="https://indexer.example.invalid/download/123" length="734003200" />
          <torznab:attr name="seeders" value="14" />
        </item>
        """
    )

    assert indexer_discovery.xml_child_text(item, "title") == "Readable History S01E01 1080p"
    assert indexer_discovery.torznab_attrs(item) == {"seeders": "14"}
    assert indexer_discovery.enclosure_length(item) == 734003200
    assert indexer_discovery.enclosure_url(item) == "https://indexer.example.invalid/download/123"
    parsed_date = indexer_discovery.parse_rfc2822_datetime(
        indexer_discovery.xml_child_text(item, "pubDate")
    )
    assert parsed_date is not None
    assert parsed_date.isoformat() == "2026-06-25T12:05:00+00:00"


def test_discover_newznab_torznab_normalizes_review_only_metadata_without_secret(
    tmp_path: Path,
) -> None:
    class _FakeResponse:
        text = """
        <rss xmlns:torznab="http://torznab.com/schemas/2015/feed">
          <channel>
            <item>
              <title>Readable History S01E01 1080p</title>
              <guid>https://indexer.example.invalid/details/123?apikey=secret-indexer-key</guid>
              <link>https://indexer.example.invalid/download/123?apikey=secret-indexer-key</link>
              <pubDate>Thu, 25 Jun 2026 12:05:00 +0000</pubDate>
              <category>TV HD</category>
              <enclosure url="https://indexer.example.invalid/download/123?apikey=secret-indexer-key" length="734003200" type="application/x-nzb" />
              <torznab:attr name="seeders" value="14" />
              <torznab:attr name="peers" value="21" />
              <torznab:attr name="grabs" value="5" />
            </item>
          </channel>
        </rss>
        """

        def raise_for_status(self) -> None:
            return None

    class _FakeSession:
        def __init__(self) -> None:
            self.calls = []

        def get(self, url, *, params, timeout):
            self.calls.append((url, dict(params), timeout))
            return _FakeResponse()

    session = _FakeSession()
    reference_root = tmp_path / "acquisition_refs"
    config = {
        "torznab_url": "https://indexer.example.invalid/feed/api?apikey=secret-indexer-key",
        "torznab_api_key": "secret-indexer-key",
        "indexer_label": "Demo Indexer",
        "indexer_video_category": 5000,
        "acquisition_reference_root": str(reference_root),
    }

    result = discover_acquisition_candidates(
        media_kind="video",
        query="readable history",
        provider="newznab_torznab",
        config=config,
        session=session,
    )

    assert result.providers_queried == ("newznab_torznab",)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "newznab_torznab"
    assert candidate.media_kind == "video"
    assert candidate.title == "Readable History S01E01 1080p"
    assert candidate.source_url is None
    assert candidate.requires_confirmation is True
    assert candidate.capabilities == ("search", "metadata", "acquire")
    assert candidate.size_bytes == 734003200
    assert candidate.metadata["indexer"] == "Demo Indexer"
    assert candidate.metadata["seeders"] == 14
    assert candidate.metadata["peers"] == 21
    assert candidate.metadata["grabs"] == 5
    assert candidate.metadata["has_download_url"] is True
    assert candidate.metadata["handoff_provider"] == "download_station"
    assert candidate.metadata["handoff_action"] == "confirm_acquisition"
    token_payload = decode_acquisition_token(candidate.candidate_token)
    assert token_payload["source_ref"]
    assert "source_uri" not in token_payload
    assert resolve_download_station_candidate_source_uri(
        candidate_token=candidate.candidate_token,
        config=config,
    ) == "https://indexer.example.invalid/download/123?apikey=secret-indexer-key"
    assert "secret-indexer-key" not in str(result)
    assert "secret-indexer-key" not in str(token_payload)
    assert any(reference_root.glob("*.json"))
    assert session.calls == [
        (
            "https://indexer.example.invalid/feed/api",
            {
                "t": "search",
                "q": "readable history",
                "limit": 20,
                "apikey": "secret-indexer-key",
                "cat": "5000",
            },
            15,
        )
    ]


def test_default_video_discovery_queries_configured_indexers_without_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeResponse:
        text = """
        <rss xmlns:torznab="http://torznab.com/schemas/2015/feed">
          <channel>
            <item>
              <title>Readable History S01E02 1080p</title>
              <guid>https://indexer.example.invalid/details/456?apikey=secret-indexer-key</guid>
              <link>https://indexer.example.invalid/download/456?apikey=secret-indexer-key</link>
              <enclosure url="https://indexer.example.invalid/download/456?apikey=secret-indexer-key" length="524288000" type="application/x-nzb" />
            </item>
          </channel>
        </rss>
        """

        def raise_for_status(self) -> None:
            return None

    class _FakeSession:
        def __init__(self) -> None:
            self.calls = []

        def get(self, url, *, params, timeout):
            self.calls.append((url, dict(params), timeout))
            return _FakeResponse()

    monkeypatch.setattr(
        acquisition_discovery,
        "list_downloaded_videos",
        lambda root, *, recover_partials=True, max_results=None: [],
    )
    session = _FakeSession()
    config = {
        "youtube_video_root": str(tmp_path / "missing-videos"),
        "torznab_url": "https://indexer.example.invalid/feed/api?apikey=secret-indexer-key",
        "torznab_api_key": "secret-indexer-key",
        "acquisition_reference_root": str(tmp_path / "acquisition_refs"),
    }

    result = discover_acquisition_candidates(
        media_kind="video",
        query="readable history",
        provider=None,
        config=config,
        session=session,
    )

    assert result.providers_queried == ("nas_video", "newznab_torznab")
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provider == "newznab_torznab"
    assert candidate.title == "Readable History S01E02 1080p"
    assert candidate.source_url is None
    assert candidate.requires_confirmation is True
    assert candidate.metadata["handoff_provider"] == "download_station"
    assert "secret-indexer-key" not in str(result)
    assert session.calls == [
        (
            "https://indexer.example.invalid/feed/api",
            {
                "t": "search",
                "q": "readable history",
                "limit": 20,
                "apikey": "secret-indexer-key",
            },
            15,
        )
    ]


def test_default_video_discovery_keeps_local_candidates_when_remote_provider_fails(
    tmp_path: Path,
) -> None:
    class _FakeResponse:
        status_code = 403
        text = "secret-indexer-key"

        def raise_for_status(self) -> None:
            error = requests.HTTPError("403 Client Error: secret-indexer-key")
            error.response = self
            raise error

    class _FakeSession:
        def __init__(self) -> None:
            self.calls = []

        def get(self, url, *, params, timeout):
            self.calls.append((url, dict(params), timeout))
            return _FakeResponse()

    video_root = tmp_path / "videos"
    video_root.mkdir()
    video_path = video_root / "Readable History S01E01.mp4"
    video_path.write_bytes(b"video")
    session = _FakeSession()

    result = discover_acquisition_candidates(
        media_kind="video",
        query="readable history",
        provider=None,
        config={
            "youtube_video_root": str(video_root),
            "newznab_url": "https://indexer.example.invalid/api",
            "newznab_api_key": "secret-indexer-key",
        },
        session=session,
    )

    assert result.providers_queried == ("nas_video", "newznab_torznab")
    assert [candidate.provider for candidate in result.candidates] == ["nas_video"]
    assert result.candidates[0].local_path == video_path.as_posix()
    assert any(
        "newznab_torznab unavailable during Default sources" in note
        and "authorized" in note.casefold()
        for note in result.policy_notes
    )
    assert "secret-indexer-key" not in str(result)
    assert session.calls == [
        (
            "https://indexer.example.invalid/api",
            {
                "t": "search",
                "q": "readable history",
                "limit": 19,
                "apikey": "secret-indexer-key",
            },
            15,
        )
    ]


def test_discover_newznab_torznab_maps_auth_errors_without_secret() -> None:
    class _FakeResponse:
        status_code = 403
        text = "secret-indexer-key"

        def raise_for_status(self) -> None:
            error = requests.HTTPError("403 Client Error: secret-indexer-key")
            error.response = self
            raise error

    class _FakeSession:
        def get(self, url, *, params, timeout):
            return _FakeResponse()

    with pytest.raises(AcquisitionProviderDiscoveryError) as exc_info:
        discover_acquisition_candidates(
            media_kind="video",
            query="demo",
            provider="newznab_torznab",
            config={
                "newznab_url": "https://indexer.example.invalid/api",
                "newznab_api_key": "secret-indexer-key",
            },
            session=_FakeSession(),
        )

    assert exc_info.value.provider == "newznab_torznab"
    assert exc_info.value.reason == "unauthorized"
    assert "authorized" in str(exc_info.value).casefold()
    assert "secret-indexer-key" not in str(exc_info.value)


def test_enqueue_download_station_task_uses_reviewed_uri_without_leaking_credentials() -> None:
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

        def get(self, url, *, params, timeout, verify):
            self.calls.append(("GET", url, dict(params), timeout, verify))
            if params["api"] == "SYNO.API.Info":
                return _FakeResponse(
                    {
                        "success": True,
                        "data": {
                            "SYNO.API.Auth": {"path": "auth.cgi", "maxVersion": 2},
                            "SYNO.DownloadStation.Task": {
                                "path": "DownloadStation/task.cgi",
                                "maxVersion": 1,
                            },
                        },
                    }
                )
            if params["method"] == "login":
                return _FakeResponse({"success": True, "data": {"sid": "secret-sid"}})
            return _FakeResponse({"success": True})

        def post(self, url, *, params, timeout, verify):
            self.calls.append(("POST", url, dict(params), timeout, verify))
            return _FakeResponse({"success": True, "data": {"task_id": "dbid_001"}})

    session = _FakeSession()

    job = enqueue_download_station_task(
        source_uri="magnet:?xt=urn:btih:abc123",
        confirmed=True,
        destination="downloads",
        config={
            "download_station_url": "https://nas.example.invalid",
            "download_station_username": "nas-user",
            "download_station_password": "nas-secret",
            "download_station_verify_tls": False,
        },
        session=session,
    )

    assert job.provider == "download_station"
    assert job.status == "submitted"
    assert job.task_id == "dbid_001"
    create_call = next(call for call in session.calls if call[0] == "POST")
    assert create_call[2]["uri"] == "magnet:?xt=urn:btih:abc123"
    assert create_call[2]["destination"] == "downloads"
    assert create_call[4] is False
    serialized = str(job)
    assert "nas-user" not in serialized
    assert "nas-secret" not in serialized
    assert "secret-sid" not in serialized


def test_enqueue_download_station_rejects_unconfirmed_or_invalid_uri() -> None:
    config = {
        "download_station_url": "https://nas.example.invalid",
        "download_station_username": "nas-user",
        "download_station_password": "nas-secret",
    }
    with pytest.raises(ValueError, match="confirmation"):
        enqueue_download_station_task(
            source_uri="https://example.test/file.torrent",
            confirmed=False,
            config=config,
        )
    with pytest.raises(ValueError, match="http"):
        enqueue_download_station_task(
            source_uri="file:///tmp/file.torrent",
            confirmed=True,
            config=config,
        )


def test_poll_download_station_task_maps_completed_files_without_secret(tmp_path: Path) -> None:
    completed_root = tmp_path / "downloads"
    completed_root.mkdir()

    class _FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class _FakeSession:
        def get(self, url, *, params, timeout, verify):
            if params["api"] == "SYNO.API.Info":
                return _FakeResponse(
                    {
                        "success": True,
                        "data": {
                            "SYNO.API.Auth": {"path": "auth.cgi", "maxVersion": 2},
                            "SYNO.DownloadStation.Task": {
                                "path": "DownloadStation/task.cgi",
                                "maxVersion": 1,
                            },
                        },
                    }
                )
            if params["method"] == "login":
                return _FakeResponse({"success": True, "data": {"sid": "secret-sid"}})
            if params["method"] == "getinfo":
                return _FakeResponse(
                    {
                        "success": True,
                        "data": {
                            "tasks": [
                                {
                                    "id": "dbid_001",
                                    "title": "Demo",
                                    "status": "finished",
                                    "size": "100",
                                    "size_downloaded": "100",
                                    "additional": {
                                        "file": [
                                            {"filename": "Demo.mkv"},
                                            {"filename": "/outside/Other.mkv"},
                                            {
                                                "filename": (
                                                    "https://indexer.example.invalid/"
                                                    "download?id=7&apikey=secret"
                                                )
                                            },
                                            {"filename": "../escape.mkv"},
                                        ],
                                    },
                                }
                            ]
                        },
                    }
                )
            return _FakeResponse({"success": True})

    job = poll_download_station_task(
        task_id="dbid_001",
        config={
            "download_station_url": "https://nas.example.invalid",
            "download_station_username": "nas-user",
            "download_station_password": "nas-secret",
            "download_station_completed_root": completed_root.as_posix(),
        },
        session=_FakeSession(),
    )

    completed_file = (completed_root / "Demo.mkv").as_posix()
    assert job.status == "completed"
    assert job.progress == 1.0
    assert job.completed_files == (completed_file,)
    assert job.metadata["source_kind"] == "download_station"
    assert job.metadata["completed_files"] == [completed_file]
    assert job.metadata["files"] == [completed_file]
    assert job.metadata["completed_file"] == completed_file
    assert job.next_actions == ("discover_manual_downloads", "import_local")
    assert "nas-secret" not in str(job)
    assert "secret" not in str(job)
