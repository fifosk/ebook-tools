from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.library.library_sync import LibraryError, LibrarySync
from modules.library.sync import metadata as metadata_utils
from modules.services.file_locator import FileLocator


def _write_job_metadata(job_root: Path, payload: dict) -> None:
    metadata_dir = job_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "job.json").write_text(json.dumps(payload), encoding="utf-8")


def _subtitle_job_payload(*, job_id: str, generate_audio_book: bool) -> dict:
    return {
        "job_id": job_id,
        "job_type": "subtitle",
        "status": "completed",
        "request": {
            "original_name": "example.srt",
            "options": {
                "generate_audio_book": generate_audio_book,
                "target_language": "en",
            },
        },
        "result": {
            "subtitle": {"metadata": {"generate_audio_book": generate_audio_book}},
            "media_metadata": {
                "book_title": "Example",
                "book_author": "Subtitles",
                "book_genre": "Subtitles",
                "book_language": "en",
            },
        },
    }


def test_infer_item_type_for_narrated_subtitles() -> None:
    narrated = _subtitle_job_payload(job_id="job-1", generate_audio_book=True)
    assert metadata_utils.is_narrated_subtitle_job(narrated) is True
    assert metadata_utils.infer_item_type(narrated) == "narrated_subtitle"

    translated_only = _subtitle_job_payload(job_id="job-2", generate_audio_book=False)
    assert metadata_utils.is_narrated_subtitle_job(translated_only) is False
    assert metadata_utils.infer_item_type(translated_only) == "book"


def test_move_to_library_blocks_translated_subtitles(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    library_root = tmp_path / "library"
    locator = FileLocator(storage_dir=queue_root)

    job_id = "job-translated"
    job_root = locator.job_root(job_id)
    job_root.mkdir(parents=True, exist_ok=True)
    _write_job_metadata(job_root, _subtitle_job_payload(job_id=job_id, generate_audio_book=False))

    sync = LibrarySync(library_root=library_root, file_locator=locator)

    with pytest.raises(LibraryError, match="Only narrated subtitle jobs"):
        sync.move_to_library(job_id, status_override="finished")


def test_move_to_library_accepts_narrated_subtitles(tmp_path: Path) -> None:
    queue_root = tmp_path / "queue"
    library_root = tmp_path / "library"
    locator = FileLocator(storage_dir=queue_root)

    job_id = "job-narrated"
    job_root = locator.job_root(job_id)
    job_root.mkdir(parents=True, exist_ok=True)
    _write_job_metadata(job_root, _subtitle_job_payload(job_id=job_id, generate_audio_book=True))

    sync = LibrarySync(library_root=library_root, file_locator=locator)

    entry = sync.move_to_library(job_id, status_override="finished")
    assert entry.item_type == "narrated_subtitle"
    assert entry.author == "Subtitles"
    assert entry.book_title == "Example"
    assert entry.language == "en"

    moved_root = Path(entry.library_path)
    assert moved_root.exists()
    moved_metadata_path = moved_root / "metadata" / "job.json"
    assert moved_metadata_path.exists()
    persisted = json.loads(moved_metadata_path.read_text(encoding="utf-8"))
    assert persisted.get("item_type") == "narrated_subtitle"
