from __future__ import annotations

from pathlib import Path

from modules import audio_video_generator as av_gen


class _Result:
    returncode = 0
    stdout = b""
    stderr = b""


def test_persist_batch_preview_creates_expected_assets(tmp_path, monkeypatch):
    video_dir = tmp_path / "outputs" / "batch_0001"
    video_dir.mkdir(parents=True, exist_ok=True)
    final_video = video_dir / "video.mp4"
    final_video.write_bytes(b"dummy")

    def fake_run(cmd, stdout=None, stderr=None):  # noqa: D401 - simple stub
        preview_target = Path(cmd[-1])
        preview_target.parent.mkdir(parents=True, exist_ok=True)
        preview_target.write_bytes(b"preview")
        return _Result()

    monkeypatch.setattr(av_gen.subprocess, "run", fake_run)

    created = av_gen._persist_batch_preview(str(final_video), slide_index=1)

    preview_image = video_dir / "video_0001.png"
    assert preview_image.exists(), "expected extracted preview alongside video"

    assert created == [str(preview_image)], "persisted preview should only include the colocated image"
