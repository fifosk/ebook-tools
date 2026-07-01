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
