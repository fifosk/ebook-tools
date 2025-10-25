import errno
import shutil
from pathlib import Path

import pytest

from modules.render.context import RenderBatchContext
from modules.render.output_writer import DeferredBatchWriter


def _build_context(ramdisk_enabled: bool, ramdisk_path: Path, batch_id: str = "batch-1") -> RenderBatchContext:
    manifest = {
        "batch_id": batch_id,
        "ramdisk_enabled": ramdisk_enabled,
        "ramdisk_path": str(ramdisk_path),
    }
    return RenderBatchContext(manifest=manifest, media={})


def test_deferred_writer_commits_to_final_directory(tmp_path):
    ramdisk_root = tmp_path / "ramdisk"
    final_dir = tmp_path / "final"
    context = _build_context(True, ramdisk_root)
    writer = DeferredBatchWriter(final_dir, context)

    staged_file = writer.work_dir / "sample.txt"
    staged_file.write_text("hello", encoding="utf-8")

    final_path = writer.stage(staged_file)
    assert final_path == final_dir / "sample.txt"

    writer.commit()

    assert final_path.exists()
    assert final_path.read_text(encoding="utf-8") == "hello"
    assert not writer.work_dir.exists()


def test_deferred_writer_cleans_up_on_disk_full(monkeypatch, tmp_path):
    ramdisk_root = tmp_path / "ramdisk"
    final_dir = tmp_path / "final"
    context = _build_context(True, ramdisk_root)
    writer = DeferredBatchWriter(final_dir, context)

    staged_file = writer.work_dir / "sample.txt"
    staged_file.write_text("data", encoding="utf-8")
    writer.stage(staged_file)

    def _raise_disk_full(src: str, dst: str) -> None:  # pragma: no cover - patched behaviour
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(shutil, "move", _raise_disk_full)

    with pytest.raises(OSError):
        writer.commit()

    writer.rollback()

    assert not (final_dir / "sample.txt").exists()
    assert not writer.work_dir.exists()
