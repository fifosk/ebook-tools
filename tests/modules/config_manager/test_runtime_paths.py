from __future__ import annotations

from pathlib import Path

import pytest

from modules.config_manager import runtime

pytestmark = pytest.mark.config


def test_try_smb_directory_uses_tolerant_stat_for_existing_books_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_root = tmp_path / "Books"
    books_root.mkdir()
    original_exists = Path.exists
    original_is_dir = Path.is_dir

    def guarded_exists(path: Path, *args, **kwargs):
        if path == books_root.resolve():
            raise AssertionError("SMB books root existence should be probed via tolerant stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_dir(path: Path, *args, **kwargs):
        if path == books_root.resolve():
            raise AssertionError("SMB books root directory status should be probed via tolerant stat")
        return original_is_dir(path, *args, **kwargs)

    monkeypatch.setattr(runtime, "DEFAULT_SMB_BOOKS_PATH", str(books_root))
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)

    resolved = runtime._try_smb_directory(books_root, require_write=False)

    assert resolved == books_root.resolve()


def test_try_smb_directory_uses_tolerant_stat_for_creatable_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_root = tmp_path / "Books"
    books_root.mkdir()
    candidate = books_root / "Output"
    original_exists = Path.exists
    original_is_dir = Path.is_dir

    def guarded_exists(path: Path, *args, **kwargs):
        if path in {candidate.resolve(strict=False), books_root.resolve()}:
            raise AssertionError("SMB child existence should be probed via tolerant stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_dir(path: Path, *args, **kwargs):
        if path in {candidate.resolve(strict=False), books_root.resolve()}:
            raise AssertionError("SMB child directory status should be probed via tolerant stat")
        return original_is_dir(path, *args, **kwargs)

    monkeypatch.setattr(runtime, "DEFAULT_SMB_BOOKS_PATH", str(books_root))
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)

    resolved = runtime._try_smb_directory(candidate, require_write=False)

    assert resolved == candidate.resolve()
    assert original_is_dir(candidate)


def test_try_smb_directory_uses_tolerant_stat_for_missing_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_root = tmp_path / "Books"
    books_root.mkdir()
    missing_parent = tmp_path / "Missing"
    candidate = missing_parent / "Output"
    original_exists = Path.exists
    original_is_dir = Path.is_dir

    def guarded_exists(path: Path, *args, **kwargs):
        if path in {candidate.resolve(strict=False), missing_parent.resolve(strict=False)}:
            raise AssertionError("SMB missing paths should be probed via tolerant stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_dir(path: Path, *args, **kwargs):
        if path in {candidate.resolve(strict=False), missing_parent.resolve(strict=False)}:
            raise AssertionError("SMB missing dirs should be probed via tolerant stat")
        return original_is_dir(path, *args, **kwargs)

    monkeypatch.setattr(runtime, "DEFAULT_SMB_BOOKS_PATH", str(books_root))
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)

    assert runtime._try_smb_directory(candidate, require_write=False) is None
