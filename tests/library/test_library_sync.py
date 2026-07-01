from __future__ import annotations

from pathlib import Path

import pytest

from modules.library.library_sync import LibraryError
from modules.library.sync import file_ops, metadata as metadata_utils, remote_sync, utils

pytestmark = pytest.mark.library


def test_normalize_status_accepts_known_values() -> None:
    assert utils.normalize_status("Finished", error_cls=LibraryError) == "finished"
    assert utils.normalize_status("paused", error_cls=LibraryError) == "paused"
    with pytest.raises(LibraryError):
        utils.normalize_status("bogus", error_cls=LibraryError)


def test_resolve_library_path_sanitizes_segments(tmp_path: Path) -> None:
    metadata = {
        "author": "Jane Doe",
        "book_title": " My Book! ",
        "language": "en-US",
    }
    result = file_ops.resolve_library_path(tmp_path, metadata, "job-123")
    expected = tmp_path / "Jane Doe" / "My Book" / "en-US" / "job-123"
    assert result == expected


def test_metadata_build_entry_applies_defaults(tmp_path: Path) -> None:
    metadata_payload = {
        "job_id": "job-001",
        "author": "Author",
        "book_title": "Title",
        "status": "finished",
    }

    entry = metadata_utils.build_entry(
        metadata_payload,
        tmp_path,
        error_cls=LibraryError,
        normalize_status=lambda value: utils.normalize_status(value, error_cls=LibraryError),
        current_timestamp=lambda: "2024-01-01T00:00:00+00:00",
    )

    assert entry.id == "job-001"
    assert entry.language == "unknown"
    assert entry.library_path == str(tmp_path.resolve())
    assert entry.metadata.data["status"] == "finished"


def test_apply_isbn_metadata_normalizes_and_sets_timestamp() -> None:
    metadata_payload: dict[str, str] = {}

    updated = remote_sync.apply_isbn_metadata(
        metadata_payload,
        isbn="978-1-4028-9462-6",
        error_cls=LibraryError,
        current_timestamp=lambda: "now",
    )

    assert updated["isbn"] == "9781402894626"
    assert updated["updated_at"] == "now"


def test_refresh_metadata_uses_safe_stat_for_source_epub(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMetadataManager:
        def __init__(self) -> None:
            self.epub_calls: list[Path] = []

        def infer_metadata_from_epub(self, epub_path, *, existing_metadata, force_refresh):
            self.epub_calls.append(epub_path)
            return {
                "book_title": "Loaded Title",
                "book_author": "Loaded Author",
                "book_language": "en",
            }

        def fetch_metadata_from_isbn(self, _isbn):
            return {}

        def merge_metadata_payloads(self, *payloads):
            merged = {}
            for payload in payloads:
                merged.update({key: value for key, value in payload.items() if value})
            return merged

    job_root = tmp_path / "job-1"
    source_path = job_root / "data" / "source.epub"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("epub", encoding="utf-8")
    metadata = {"input_file": "data/source.epub", "media_metadata": {}}
    manager = FakeMetadataManager()
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == source_path:
            raise AssertionError("library remote metadata EPUBs should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(remote_sync, "enrich_media_metadata", lambda metadata, force: type(
        "NoEnrichment",
        (),
        {"enriched": False},
    )())

    updated = remote_sync.refresh_metadata(
        "job-1",
        job_root,
        metadata,
        manager,
        error_cls=LibraryError,
        current_timestamp=lambda: "now",
        enrich_from_external=True,
    )

    assert manager.epub_calls == [source_path]
    assert updated["book_title"] == "Loaded Title"
    assert updated["author"] == "Loaded Author"
    assert updated["updated_at"] == "now"


def test_refresh_metadata_missing_source_uses_safe_stat_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMetadataManager:
        def infer_metadata_from_epub(self, *_args, **_kwargs):
            raise AssertionError("missing EPUB should not be loaded")

        def fetch_metadata_from_isbn(self, _isbn):
            return {}

    job_root = tmp_path / "job-1"
    source_path = job_root / "data" / "missing.epub"
    metadata = {"input_file": "data/missing.epub", "media_metadata": {}}
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == source_path:
            raise AssertionError("library remote metadata missing EPUBs should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    with pytest.raises(LibraryError, match="Unable to locate"):
        remote_sync.refresh_metadata(
            "job-1",
            job_root,
            metadata,
            FakeMetadataManager(),
            error_cls=LibraryError,
            current_timestamp=lambda: "now",
            enrich_from_external=False,
        )
