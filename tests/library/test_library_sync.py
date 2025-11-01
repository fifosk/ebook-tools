from __future__ import annotations

from pathlib import Path

import pytest

from modules.library.library_sync import LibraryError
from modules.library.sync import file_ops, metadata as metadata_utils, remote_sync, utils


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
