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

    preview_image = video_dir / "video.png"
    assert preview_image.exists(), "expected extracted preview alongside video"

    slides_root = video_dir / "slides"
    primary_dir = slides_root / "batch_0001_video"
    assert (primary_dir / "0001.png").exists(), "primary batch slide missing"

    unique_named = slides_root / "batch_0001_video_0001.png"
    assert unique_named.exists(), "unique slide alias missing"

    parent_dir = slides_root / "batch_0001"
    assert (parent_dir / "0001.png").exists(), "parent slide alias missing"

    default_slide = slides_root / "0001.png"
    assert default_slide.exists(), "default slide alias missing"

    stem_alias = slides_root / "video_0001.png"
    assert stem_alias.exists(), "stem slide alias missing"

    stem_subdir = slides_root / "video" / "0001.png"
    assert stem_subdir.exists(), "stem-specific directory slide missing"

    root_alias = video_dir / "0001.png"
    assert root_alias.exists(), "root-level slide alias missing"

    expected = {
        str(preview_image),
        str((primary_dir / "0001.png")),
        str(unique_named),
        str(parent_dir / "0001.png"),
        str(default_slide),
        str(stem_alias),
        str(stem_subdir),
        str(root_alias),
    }

    assert set(created) == expected, "persisted preview paths did not match expected aliases"
