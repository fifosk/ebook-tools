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
