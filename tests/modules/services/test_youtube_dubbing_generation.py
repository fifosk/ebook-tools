from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.services.youtube_dubbing import generation

pytestmark = pytest.mark.services


def test_generate_dubbed_video_validates_inputs_with_safe_stat(
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
            raise AssertionError("YouTube dubbing generation inputs should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path in guarded_paths:
            raise AssertionError("YouTube dubbing generation inputs should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    def fake_safe_stat(path: Path):
        if path in guarded_paths:
            safe_stat_calls.append(path)
        return os.stat(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(generation, "safe_stat", fake_safe_stat)

    with pytest.raises(ValueError, match="Subtitle must be an ASS, SRT, SUB, or VTT file"):
        generation.generate_dubbed_video(video_path, subtitle_path)

    assert safe_stat_calls == [video_path, subtitle_path]
