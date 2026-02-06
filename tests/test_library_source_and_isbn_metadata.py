from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.library import LibraryError, LibraryNotFoundError, LibraryRepository, LibrarySync
from modules.services.file_locator import FileLocator


class TrackingJobManager:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_job(self, job_id: str, **_kwargs) -> None:
        self.deleted.append(job_id)


def build_job_metadata(job_id: str) -> dict:
    return {
        "job_id": job_id,
        "author": "Jane Doe",
        "book_title": "Sample Book",
        "genre": "Fiction",
        "language": "en",
        "status": "completed",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "media_completed": True,
        "generated_files": {"chunks": [], "files": [], "complete": True},
        "sources": [],
        "artifacts": {},
    }


def write_metadata(job_root: Path, payload: dict) -> None:
    metadata_dir = job_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "job.json").write_text(json.dumps(payload), encoding="utf-8")


def create_service(tmp_path: Path) -> tuple[LibrarySync, FileLocator, Path, TrackingJobManager]:
    queue_root = tmp_path / "queue"
    library_root = tmp_path / "library"
    locator = FileLocator(storage_dir=queue_root)
    repository = LibraryRepository(library_root)
    job_manager = TrackingJobManager()
    service = LibrarySync(
        library_root=library_root,
        file_locator=locator,
        repository=repository,
        job_manager=job_manager,
    )
    return service, locator, library_root, job_manager


def test_reupload_source_refreshes_metadata(tmp_path, monkeypatch):
    service, locator, _library_root, _job_manager = create_service(tmp_path)

    job_id = "job-reupload"
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)

    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    original_source = source_dir / "original.epub"
    original_source.write_text("original", encoding="utf-8")

    metadata = build_job_metadata(job_id)
    metadata["input_file"] = str(original_source)
    write_metadata(queue_root, metadata)

    cover_asset = tmp_path / "cover.jpg"
    cover_asset.write_bytes(b"cover")

    def fake_infer_metadata(path: str, *, existing_metadata=None, force_refresh=False):  # noqa: ARG001
        return {
            "book_title": "Updated Title",
            "book_author": "Updated Author",
            "book_language": "en",
            "book_cover_file": str(cover_asset),
        }

    monkeypatch.setattr("modules.metadata_manager.infer_metadata", fake_infer_metadata)

    service.move_to_library(job_id, status_override="finished")

    replacement_source = source_dir / "replacement.epub"
    replacement_source.write_text("replacement", encoding="utf-8")

    updated = service.reupload_source_from_path(job_id, replacement_source)

    job_root = Path(updated.library_path)
    data_dir = job_root / "data"
    data_files = list(data_dir.glob("*.epub"))
    assert len(data_files) == 1
    assert data_files[0].name.startswith("replacement")

    metadata_payload = json.loads((job_root / "metadata" / "job.json").read_text(encoding="utf-8"))
    assert metadata_payload.get("book_title") == "Updated Title"
    assert metadata_payload.get("source_path") == data_files[0].relative_to(job_root).as_posix()


def test_reupload_source_handles_refresh_failure(tmp_path, monkeypatch):
    service, locator, _library_root, _job_manager = create_service(tmp_path)

    job_id = "job-reupload-fallback"
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)

    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    original_source = source_dir / "original.epub"
    original_source.write_text("original", encoding="utf-8")

    metadata = build_job_metadata(job_id)
    metadata["input_file"] = str(original_source)
    write_metadata(queue_root, metadata)

    service.move_to_library(job_id, status_override="finished")

    replacement_source = source_dir / "replacement.epub"
    replacement_source.write_text("replacement", encoding="utf-8")

    def failing_refresh(*_args, **_kwargs):
        raise LibraryError("boom")

    monkeypatch.setattr(
        "modules.library.library_sync.LibrarySync.refresh_metadata",
        failing_refresh,
    )

    updated = service.reupload_source_from_path(job_id, replacement_source)

    job_root = Path(updated.library_path)
    data_dir = job_root / "data"
    assert any(data_dir.iterdir())
    assert updated.source_path is not None


def test_refresh_metadata_uses_isbn_when_source_missing(tmp_path, monkeypatch):
    service, locator, _library_root, _job_manager = create_service(tmp_path)

    job_id = "job-isbn-refresh"
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)

    metadata = build_job_metadata(job_id)
    metadata["isbn"] = "9780316769488"
    metadata["media_metadata"] = {"isbn": "9780316769488"}
    write_metadata(queue_root, metadata)

    cover_asset = tmp_path / "isbn-cover.jpg"
    cover_asset.write_bytes(b"cover")

    def fake_fetch_metadata(isbn: str):  # noqa: ARG001
        return {
            "isbn": "9780316769488",
            "book_title": "Remote Title",
            "book_author": "Remote Author",
            "book_language": "fr",
            "book_cover_file": str(cover_asset),
        }

    monkeypatch.setattr("modules.metadata_manager.fetch_metadata_from_isbn", fake_fetch_metadata)
    monkeypatch.setattr("modules.metadata_manager.infer_metadata", lambda *args, **kwargs: {})

    service.move_to_library(job_id, status_override="finished")

    updated = service.refresh_metadata(job_id)

    assert updated.book_title == "Remote Title"
    assert updated.author == "Remote Author"
    assert updated.language == "fr"
    assert updated.isbn == "9780316769488"

    job_root = Path(updated.library_path)
    metadata_payload = json.loads((job_root / "metadata" / "job.json").read_text(encoding="utf-8"))
    assert metadata_payload.get("isbn") == "9780316769488"


def test_apply_isbn_metadata_validates_input(tmp_path):
    service, locator, _library_root, _job_manager = create_service(tmp_path)

    job_id = "job-invalid-isbn"
    queue_root = locator.job_root(job_id)
    queue_root.mkdir(parents=True)

    metadata = build_job_metadata(job_id)
    write_metadata(queue_root, metadata)

    service.move_to_library(job_id, status_override="finished")

    with pytest.raises(LibraryError):
        service.apply_isbn_metadata(job_id, "invalid-isbn")

    with pytest.raises(LibraryNotFoundError):
        service.apply_isbn_metadata("missing", "9780316769488")
