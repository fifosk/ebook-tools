from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.services.youtube_dubbing import service as service_module

pytestmark = pytest.mark.services


def test_resolve_partial_video_uses_safe_stat_for_completed_download(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    partial_path = tmp_path / "episode.mp4.part"
    completed_path = tmp_path / "episode.mp4"
    completed_path.write_bytes(b"video")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == completed_path:
            raise AssertionError("completed .part recovery should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(service_module, "safe_stat", lambda path: os.stat(path))

    assert service_module._resolve_partial_video(partial_path) == completed_path


def test_youtube_dubbing_service_validates_inputs_with_safe_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_path = tmp_path / "source.mp4"
    subtitle_path = tmp_path / "source.txt"
    video_path.write_bytes(b"video")
    subtitle_path.write_text("not a timed subtitle", encoding="utf-8")
    guarded_paths = {video_path, subtitle_path}
    safe_stat_calls: list[Path] = []
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs):
        if path in guarded_paths:
            raise AssertionError("YouTube dubbing enqueue inputs should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path in guarded_paths:
            raise AssertionError("YouTube dubbing enqueue inputs should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    def fake_safe_stat(path: Path):
        if path in guarded_paths:
            safe_stat_calls.append(path)
        return os.stat(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(service_module, "safe_stat", fake_safe_stat)

    service = service_module.YoutubeDubbingService(job_manager=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="subtitle_path must reference an ASS, SRT, SUB, or VTT subtitle file"):
        service.enqueue(
            video_path,
            subtitle_path,
            target_language="nl",
            voice="gTTS",
            tempo=1.0,
            macos_reading_speed=100,
            output_dir=None,
        )

    assert safe_stat_calls == [video_path, subtitle_path]
