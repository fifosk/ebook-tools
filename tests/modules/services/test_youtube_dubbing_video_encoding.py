from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from modules.services.youtube_dubbing import video_utils


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
