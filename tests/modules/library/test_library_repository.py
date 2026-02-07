from __future__ import annotations

import json
from pathlib import Path

from modules.library import LibraryEntry, LibraryRepository, MetadataSnapshot

import pytest

pytestmark = pytest.mark.library


def make_entry(library_root: Path, job_id: str, **overrides) -> LibraryEntry:
    return LibraryEntry(
        id=job_id,
        author=overrides.get("author", "Author"),
        book_title=overrides.get("book_title", "Title"),
        item_type=overrides.get("item_type", "book"),
        genre=overrides.get("genre"),
        language=overrides.get("language", "en"),
        status=overrides.get("status", "finished"),
        created_at=overrides.get("created_at", "2024-01-01T00:00:00+00:00"),
        updated_at=overrides.get("updated_at", "2024-01-02T00:00:00+00:00"),
        library_path=str(library_root / job_id),
        cover_path=overrides.get("cover_path"),
        isbn=overrides.get("isbn"),
        source_path=overrides.get("source_path"),
        metadata=MetadataSnapshot(metadata=overrides.get("metadata", {})),
    )


def test_add_and_get_entry(tmp_path: Path) -> None:
    repository = LibraryRepository(tmp_path)
    entry = make_entry(tmp_path, "job-1", metadata={"media_completed": True})

    repository.add_entry(entry)
    fetched = repository.get_entry_by_id("job-1")

    assert fetched is not None
    assert fetched.id == "job-1"
    assert fetched.metadata.data.get("media_completed") is True


def test_sync_from_filesystem(tmp_path: Path) -> None:
    repository = LibraryRepository(tmp_path)
    job_root = tmp_path / "Author" / "Book" / "en" / "job-2"
    metadata_dir = job_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_payload = {
        "job_id": "job-2",
        "author": "Shelf Author",
        "book_title": "Shelf Title",
        "item_type": "book",
        "language": "en",
        "status": "finished",
        "created_at": "2024-01-05T00:00:00+00:00",
        "updated_at": "2024-01-05T00:00:00+00:00",
        "generated_files": {"files": []},
    }
    (metadata_dir / "job.json").write_text(json.dumps(metadata_payload), encoding="utf-8")

    indexed = repository.sync_from_filesystem(tmp_path)
    assert indexed == 1
    stored = repository.get_entry_by_id("job-2")
    assert stored is not None
    assert stored.book_title == "Shelf Title"
    assert stored.metadata.data["job_id"] == "job-2"
