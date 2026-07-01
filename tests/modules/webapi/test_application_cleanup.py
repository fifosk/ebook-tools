import os
from pathlib import Path
import time

from modules.webapi import application
from modules.webapi.application import (
    _cleanup_empty_job_folders,
    _cleanup_stale_exports,
    _resolve_static_assets_config,
)

import pytest

pytestmark = pytest.mark.webapi


def test_cleanup_empty_job_folders_prunes_only_empty_dirs(tmp_path: Path) -> None:
    empty_job = tmp_path / "empty-job"
    empty_job.mkdir()

    populated_job = tmp_path / "populated-job"
    populated_job.mkdir()
    media_dir = populated_job / "media"
    media_dir.mkdir()
    (media_dir / "clip.mp4").write_bytes(b"\x00")

    removed = _cleanup_empty_job_folders(storage_root=tmp_path)

    assert removed == 1
    assert not empty_job.exists()
    assert populated_job.exists()


def test_cleanup_empty_job_folders_uses_safe_stat_for_path_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty_job = tmp_path / "empty-job"
    empty_job.mkdir()

    def fail_path_probe(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("cleanup should use safe_stat instead of direct Path probes")

    monkeypatch.setattr(Path, "exists", fail_path_probe)
    monkeypatch.setattr(Path, "is_dir", fail_path_probe)
    monkeypatch.setattr(Path, "is_file", fail_path_probe)
    monkeypatch.setattr(application, "safe_stat", lambda path: os.stat(path))

    removed = _cleanup_empty_job_folders(storage_root=tmp_path)

    assert removed == 1
    assert not os.path.exists(empty_job)


def test_cleanup_stale_exports_uses_safe_stat_for_path_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_dir = tmp_path / "stale-export"
    stale_dir.mkdir()
    old_time = time.time() - 100
    os.utime(stale_dir, (old_time, old_time))

    def fail_path_probe(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("export cleanup should use safe_stat instead of direct Path probes")

    monkeypatch.setattr(Path, "exists", fail_path_probe)
    monkeypatch.setattr(Path, "is_dir", fail_path_probe)
    monkeypatch.setattr(Path, "stat", fail_path_probe)
    monkeypatch.setattr(application, "safe_stat", lambda path: os.stat(path))

    removed = _cleanup_stale_exports(exports_root=tmp_path, max_age_seconds=1)

    assert removed == 1
    assert not os.path.exists(stale_dir)


def test_static_assets_config_uses_safe_stat_for_path_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index_file = tmp_path / "index.html"
    index_file.write_text("<!doctype html>", encoding="utf-8")

    def fail_path_probe(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("static config should use safe_stat instead of direct Path probes")

    monkeypatch.setenv("EBOOK_API_STATIC_ROOT", str(tmp_path))
    monkeypatch.setenv("EBOOK_API_STATIC_INDEX", "index.html")
    monkeypatch.setattr(Path, "is_dir", fail_path_probe)
    monkeypatch.setattr(Path, "is_file", fail_path_probe)
    monkeypatch.setattr(application, "safe_stat", lambda path: os.stat(path))

    config = _resolve_static_assets_config()

    assert config is not None
    assert config.directory == tmp_path
    assert config.index_file == "index.html"
