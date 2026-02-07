import errno
import shutil
from pathlib import Path

import pytest

from modules import config_manager as cfg
from modules.render.context import RenderBatchContext
from modules.render.output_writer import DeferredBatchWriter

pytestmark = pytest.mark.render


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


def test_context_uses_runtime_tmp_dir_for_relative_ramdisk(tmp_path):
    working_dir = tmp_path / "work"
    output_dir = tmp_path / "out"
    books_dir = tmp_path / "books"
    runtime_tmp = tmp_path / "runtime-tmp"
    for path in (working_dir, output_dir, books_dir, runtime_tmp):
        path.mkdir(parents=True, exist_ok=True)

    runtime_context = cfg.RuntimeContext(
        working_dir=working_dir,
        output_dir=output_dir,
        tmp_dir=runtime_tmp,
        books_dir=books_dir,
        ffmpeg_path="ffmpeg",
        ollama_url="http://localhost",
        llm_source="local",
        local_ollama_url="http://localhost",
        cloud_ollama_url="http://localhost",
        lmstudio_url="http://localhost",
        thread_count=1,
        queue_size=1,
        pipeline_enabled=True,
        is_tmp_ramdisk=True,
    )

    previous_context = cfg.get_runtime_context(None)
    cfg.set_runtime_context(runtime_context)
    try:
        manifest = {
            "batch_id": "batch-7",
            "ramdisk_enabled": True,
            "ramdisk_path": "render",
        }
        context = RenderBatchContext(manifest=manifest, media={})
        expected_dir = runtime_tmp / "render" / "batch-7"
        assert context.temp_dir == expected_dir
    finally:
        if previous_context is not None:
            cfg.set_runtime_context(previous_context)
        else:
            cfg.clear_runtime_context()
