from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from modules.services.youtube_dubbing import video_utils

import pytest

pytestmark = pytest.mark.services


def test_video_utils_uses_safe_stat_for_file_probes() -> None:
    source = Path(video_utils.__file__).read_text(encoding="utf-8")

    assert ".exists(" not in source
    assert ".is_file(" not in source
    assert "_path_exists(" in source


def test_resolve_batch_output_path_uses_safe_stat_for_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_output = tmp_path / "dubbed.mp4"
    first_collision = tmp_path / "00-00-12-dubbed.mp4"
    second_collision = tmp_path / "00-00-12-dubbed-2.mp4"
    first_collision.write_bytes(b"existing")
    second_collision.write_bytes(b"existing")
    guarded_paths = {first_collision, second_collision}
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path in guarded_paths:
            raise AssertionError("batch output collisions should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def fake_safe_stat(path: Path):
        try:
            return os.stat(path)
        except FileNotFoundError:
            return None

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(video_utils, "safe_stat", fake_safe_stat)

    assert video_utils._resolve_batch_output_path(base_output, 12.0) == tmp_path / "00-00-12-dubbed-3.mp4"


def test_resolve_temp_output_path_uses_safe_stat_for_temp_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_output = tmp_path / "dubbed.mp4"
    temp_root = tmp_path / "tmp"
    temp_root.mkdir()
    first_collision = temp_root / "dubbed.mp4"
    first_collision.write_bytes(b"existing")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == first_collision:
            raise AssertionError("temp output collisions should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def fake_safe_stat(path: Path):
        try:
            return os.stat(path)
        except FileNotFoundError:
            return None

    monkeypatch.setattr(video_utils, "_TEMP_DIR", temp_root)
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(video_utils, "safe_stat", fake_safe_stat)

    assert video_utils._resolve_temp_output_path(base_output) == temp_root / "dubbed-2.mp4"


def test_downscale_forces_ios_friendly_h264_aac(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "input.mp4"
    source.write_bytes(b"not-a-real-mp4")
    destination = tmp_path / "output.mp4"

    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append([str(part) for part in cmd])
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def fake_probe_height(path: Path):
        if path == source:
            return 720
        return 480

    monkeypatch.setattr(video_utils.subprocess, "run", fake_run)
    monkeypatch.setattr(video_utils, "_probe_video_height", fake_probe_height)

    resolved = video_utils._downscale_video(
        source,
        target_height=480,
        preserve_aspect_ratio=True,
        output_path=destination,
    )

    assert resolved == destination
    assert calls, "Expected ffmpeg subprocess invocation"
    cmd = " ".join(calls[0])
    assert "-c:v libx264" in cmd
    assert "-profile:v main" in cmd
    assert "-level:v 4.1" in cmd
    assert "-pix_fmt yuv420p" in cmd
    assert "-c:a aac" in cmd
    assert "-movflags +faststart" in cmd
    assert "frag_keyframe" not in cmd
    assert "empty_moov" not in cmd
    assert "-c:a copy" not in cmd
    assert ",format=yuv420p" in cmd


def test_mux_forces_ios_friendly_h264_aac(monkeypatch, tmp_path: Path) -> None:
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"video")
    dubbed_audio = tmp_path / "dub.wav"
    dubbed_audio.write_bytes(b"audio")
    output = tmp_path / "muxed.mp4"

    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append([str(part) for part in cmd])
        output.write_bytes(b"out")
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(video_utils.subprocess, "run", fake_run)
    monkeypatch.setattr(video_utils, "_has_audio_stream", lambda _path: True)

    video_utils._mux_audio_track(
        source_video,
        dubbed_audio,
        output,
        "en",
        include_source_audio=False,
    )

    assert calls, "Expected ffmpeg subprocess invocation"
    cmd = " ".join(calls[0])
    assert "-c:v libx264" in cmd
    assert "-profile:v main" in cmd
    assert "-level:v 4.1" in cmd
    assert "-pix_fmt yuv420p" in cmd
    assert "-c:a aac" in cmd
    assert "-movflags +faststart" in cmd
    assert "frag_keyframe" not in cmd
