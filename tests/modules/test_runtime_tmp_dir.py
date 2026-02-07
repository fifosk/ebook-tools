"""Tests for runtime temporary directory preservation helpers."""

from pathlib import Path

from modules.config_manager import runtime


def _build_context(tmp_dir: Path, *, is_ramdisk: bool) -> runtime.RuntimeContext:
    return runtime.RuntimeContext(
        working_dir=tmp_dir,
        output_dir=tmp_dir,
        tmp_dir=tmp_dir,
        books_dir=tmp_dir,
        ffmpeg_path="ffmpeg",
        ollama_url="http://localhost",
        llm_source="local",
        local_ollama_url="http://localhost",
        cloud_ollama_url="http://cloud",
        lmstudio_url="http://localhost",
        thread_count=1,
        queue_size=1,
        pipeline_enabled=False,
        is_tmp_ramdisk=is_ramdisk,
    )


def test_cleanup_environment_skips_when_singleton_mounted(monkeypatch, tmp_path):
    """cleanup_environment is a no-op when the singleton RAMDisk is active."""
    tmp_dir = tmp_path / "ram"
    tmp_dir.mkdir()

    called = False

    def _fake_teardown(path: str) -> None:  # pragma: no cover
        nonlocal called
        called = True

    monkeypatch.setattr(runtime.ramdisk_manager, "teardown_ramdisk", _fake_teardown)
    monkeypatch.setattr(runtime.ramdisk_manager, "is_mounted", lambda: True)

    context = _build_context(tmp_dir, is_ramdisk=True)
    runtime.cleanup_environment(context)

    assert called is False


def test_cleanup_environment_skips_preserved_ramdisk(monkeypatch, tmp_path):
    """cleanup_environment skips teardown for preserved paths (fallback guard)."""
    tmp_dir = tmp_path / "ram"
    tmp_dir.mkdir()

    called = False

    def _fake_teardown(path: str) -> None:  # pragma: no cover
        nonlocal called
        called = True

    monkeypatch.setattr(runtime.ramdisk_manager, "teardown_ramdisk", _fake_teardown)
    monkeypatch.setattr(runtime.ramdisk_manager, "is_mounted", lambda: False)

    context = _build_context(tmp_dir, is_ramdisk=True)
    runtime.register_tmp_dir_preservation(tmp_dir)
    runtime.cleanup_environment(context)
    runtime.release_tmp_dir_preservation(tmp_dir)

    assert called is False


def test_cleanup_environment_tears_down_unmanaged_ramdisk(monkeypatch, tmp_path):
    """cleanup_environment tears down when no singleton and not preserved."""
    tmp_dir = tmp_path / "ram"
    tmp_dir.mkdir()

    called = False

    def _fake_teardown(path: str) -> None:  # pragma: no cover
        nonlocal called
        called = True

    monkeypatch.setattr(runtime.ramdisk_manager, "teardown_ramdisk", _fake_teardown)
    monkeypatch.setattr(runtime.ramdisk_manager, "is_mounted", lambda: False)

    context = _build_context(tmp_dir, is_ramdisk=True)
    runtime.cleanup_environment(context)

    assert called is True
