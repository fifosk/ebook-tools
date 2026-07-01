from __future__ import annotations

from pathlib import Path

import pytest

from modules.config_manager import paths

pytestmark = pytest.mark.config


def test_resolve_file_path_uses_tolerant_stat_for_base_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    selected = books_dir / "latest.epub"
    selected.write_bytes(b"epub")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == selected.resolve():
            raise AssertionError("resolve_file_path should use tolerant stat instead of exists")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert paths.resolve_file_path("latest.epub", books_dir) == selected.resolve()


def test_resolve_file_path_uses_tolerant_stat_for_library_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_root = tmp_path / "repo"
    library_root = tmp_path / "library"
    selected = library_root / "books" / "latest.epub"
    selected.parent.mkdir(parents=True)
    selected.write_bytes(b"epub")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == selected.resolve():
            raise AssertionError("resolve_file_path should use tolerant stat instead of exists")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(paths, "SCRIPT_DIR", script_root)
    monkeypatch.setattr(paths, "DEFAULT_LIBRARY_ROOT", library_root)
    monkeypatch.setattr("modules.config_manager.get_library_root", lambda create=False: library_root)
    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert paths.resolve_file_path("books/latest.epub") == selected.resolve()


def test_resolve_directory_cleanup_uses_tolerant_stat_for_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "storage"
    target.write_text("not a directory", encoding="utf-8")
    original_exists = Path.exists
    original_is_dir = Path.is_dir
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs):
        if path == target:
            raise AssertionError("resolve_directory cleanup should use tolerant stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_dir(path: Path, *args, **kwargs):
        if path == target:
            raise AssertionError("resolve_directory cleanup dirs should use tolerant stat")
        return original_is_dir(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path == target:
            raise AssertionError("resolve_directory cleanup files should use tolerant stat")
        return original_is_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    resolved = paths.resolve_directory(target, tmp_path / "fallback")

    assert resolved == target
    assert original_is_dir(target)


def test_resolve_directory_fallback_existing_dir_uses_tolerant_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "readonly"
    target.mkdir()
    original_mkdir = Path.mkdir
    original_exists = Path.exists
    original_is_dir = Path.is_dir

    def failing_mkdir(path: Path, *args, **kwargs):
        if path == target:
            raise OSError("simulated transient mkdir failure")
        return original_mkdir(path, *args, **kwargs)

    def guarded_exists(path: Path, *args, **kwargs):
        if path == target:
            raise AssertionError("resolve_directory fallback should use tolerant stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_dir(path: Path, *args, **kwargs):
        if path == target:
            raise AssertionError("resolve_directory fallback dirs should use tolerant stat")
        return original_is_dir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)

    assert paths.resolve_directory(target, tmp_path / "fallback") == target
