from __future__ import annotations

from pathlib import Path

import pytest

from modules.library.library_metadata import LibraryMetadataManager


def test_normalize_and_apply_isbn(tmp_path: Path) -> None:
    manager = LibraryMetadataManager(tmp_path)
    metadata = {"media_metadata": {}}
    normalized = manager.normalize_isbn("978-0-321-87758-1")
    assert normalized == "9780321877581"

    manager.apply_isbn(metadata, normalized)
    assert metadata["isbn"] == "9780321877581"
    book_meta = metadata["media_metadata"]
    assert book_meta["isbn"] == "9780321877581"
    assert book_meta["book_isbn"] == "9780321877581"


def test_merge_metadata_prioritizes_non_placeholder(tmp_path: Path) -> None:
    manager = LibraryMetadataManager(tmp_path)
    base = {"book_title": "Untitled", "book_author": "Unknown"}
    override = {"book_title": "Updated", "book_author": "Unknown"}
    merged = manager.merge_metadata_payloads(base, override)
    assert merged["book_title"] == "Updated"
    assert merged["book_author"] == "Unknown"


def test_mirror_cover_asset(tmp_path: Path) -> None:
    manager = LibraryMetadataManager(tmp_path)
    job_root = tmp_path / "job"
    cover_source = tmp_path / "cover.png"
    cover_source.write_bytes(b"cover")

    mirrored = manager.mirror_cover_asset(job_root, str(cover_source))
    assert mirrored is not None
    target_path = job_root / mirrored
    assert target_path.exists()


@pytest.mark.parametrize("raw,expected", [
    ("", None),
    ("12345", None),
    ("0-201-53082-1", "0201530821"),
    ("978 0 13 235088 4", "9780132350884"),
])
def test_extract_and_normalize_isbn(tmp_path: Path, raw: str, expected: str | None) -> None:
    manager = LibraryMetadataManager(tmp_path)
    metadata = {"isbn": raw}
    assert manager.extract_isbn(metadata) == expected
