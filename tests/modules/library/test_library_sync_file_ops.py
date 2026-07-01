from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.library.sync import file_ops

pytestmark = pytest.mark.library


def test_load_metadata_uses_safe_stat_for_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    metadata_path = job_root / "metadata" / "job.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps({"job_id": "job-1"}), encoding="utf-8")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == metadata_path:
            raise AssertionError("library metadata manifest should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert file_ops.load_metadata(job_root) == {"job_id": "job-1"}


def test_resolve_epub_candidate_uses_safe_stat_for_source_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    source_path = job_root / "data" / "Source.epub"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("epub", encoding="utf-8")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == source_path:
            raise AssertionError("library source paths should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert file_ops.resolve_epub_candidate("Source.epub", job_root) == source_path
    assert file_ops.resolve_epub_candidate(source_path.as_posix(), job_root) == source_path


def test_resolve_source_relative_uses_safe_stat_for_data_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    data_root = job_root / "data"
    source_path = data_root / "Source.epub"
    data_root.mkdir(parents=True, exist_ok=True)
    source_path.write_text("epub", encoding="utf-8")
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == data_root:
            raise AssertionError("library source data roots should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs) -> bool:
        if path == source_path:
            raise AssertionError("library source data files should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    assert file_ops.resolve_source_relative({}, job_root) == "data/Source.epub"


def test_next_source_candidate_uses_safe_stat_for_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "Source.epub"
    first_collision = tmp_path / "Source-1.epub"
    destination.write_text("epub", encoding="utf-8")
    first_collision.write_text("epub", encoding="utf-8")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path in {destination, first_collision}:
            raise AssertionError("library source collisions should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert file_ops.next_source_candidate(destination) == tmp_path / "Source-2.epub"


def test_resolve_cover_source_uses_safe_stat_for_cover_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    cover_path = job_root / "metadata" / "cover.jpg"
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    cover_path.write_bytes(b"cover")
    original_is_file = Path.is_file

    def guarded_is_file(path: Path, *args, **kwargs) -> bool:
        if path == cover_path:
            raise AssertionError("library cover sources should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    assert file_ops.resolve_cover_source(job_root, "metadata/cover.jpg") == cover_path


def test_extract_cover_path_uses_safe_stat_for_metadata_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    cover_path = job_root / "metadata" / "cover.png"
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    cover_path.write_bytes(b"cover")
    original_is_file = Path.is_file

    def guarded_is_file(path: Path, *args, **kwargs) -> bool:
        if path == cover_path:
            raise AssertionError("library cover metadata scans should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    assert file_ops.extract_cover_path({}, job_root) == "metadata/cover.png"


def test_normalize_cover_path_uses_safe_stat_for_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    cover_path = job_root / "metadata" / "cover.webp"
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    cover_path.write_bytes(b"cover")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == cover_path:
            raise AssertionError("library cover path candidates should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert file_ops.normalize_cover_path("cover.webp", job_root) == "metadata/cover.webp"


def test_compact_metadata_generated_files_uses_safe_stat_for_chunk_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    chunk_path = job_root / "metadata" / "chunk_0001.json"
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_path.write_text(
        json.dumps({"sentences": [{"sentence_number": 1, "text": "Loaded"}]}),
        encoding="utf-8",
    )
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == chunk_path:
            raise AssertionError("library chunk payloads should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    payload, changed = file_ops.compact_metadata_generated_files(
        {
            "generated_files": {
                "chunks": [
                    {
                        "metadata_path": "metadata/chunk_0001.json",
                        "sentences": [{"sentence_number": 1, "text": "Inline"}],
                    }
                ]
            }
        },
        job_root,
    )

    assert changed is True
    assert "sentences" not in payload["generated_files"]["chunks"][0]


def test_build_media_record_stats_use_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    media_path = job_root / "media" / "audio.mp3"
    media_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_bytes(b"audio")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == media_path:
            raise AssertionError("library media stats should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    record, category, signature = file_ops.build_media_record(
        "job-1",
        {"path": media_path.as_posix(), "type": "audio"},
        job_root,
        include_stats=True,
        fast_paths=True,
    )

    assert category == "audio"
    assert signature[0] == "audio"
    assert record is not None
    assert record["size"] == 5
    assert record["updated_at"]


def test_serialize_media_entries_loader_manifest_uses_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_root = tmp_path / "job-1"
    manifest_path = job_root / "metadata" / "job.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}", encoding="utf-8")
    original_exists = Path.exists
    loader_calls: list[Path] = []

    class FakeMetadataLoader:
        def __init__(self, loaded_root: Path) -> None:
            loader_calls.append(loaded_root)

        def load_chunk(self, chunk: dict, *, include_sentences: bool = True) -> dict:
            loaded = dict(chunk)
            loaded["sentences"] = [{"sentence_number": 1, "text": "Loaded"}]
            loaded["sentence_count"] = 1
            return loaded

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == manifest_path:
            raise AssertionError("library media loader manifests should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(file_ops, "MetadataLoader", FakeMetadataLoader)
    monkeypatch.setattr(Path, "exists", guarded_exists)

    _media_map, chunk_records, _complete = file_ops.serialize_media_entries(
        "job-1",
        {
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "metadata_path": "metadata/chunk_0001.json",
                    "files": [{"relative_path": "media/audio.mp3", "type": "audio"}],
                }
            ]
        },
        job_root,
        include_stats=False,
        include_chunk_sentences=True,
        include_chunk_metadata=True,
        fast_paths=True,
    )

    assert loader_calls == [job_root]
    assert chunk_records[0]["sentences"] == [{"sentence_number": 1, "text": "Loaded"}]
