from __future__ import annotations

from pathlib import Path

import pytest

from modules.services.youtube_dubbing import stitching

pytestmark = pytest.mark.services


def test_resolve_stitched_output_path_uses_safe_stat_for_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_output = tmp_path / "clip.mp4"
    first_collision = tmp_path / "clip.full.mp4"
    second_collision = tmp_path / "clip.full-2.mp4"
    first_collision.write_bytes(b"existing")
    second_collision.write_bytes(b"existing")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path in {first_collision, second_collision}:
            raise AssertionError("stitched output collisions should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(stitching, "_is_stitched_video_valid", lambda _path: True)

    assert stitching._resolve_stitched_output_path(base_output) == tmp_path / "clip.full-3.mp4"


def test_stitch_dub_batches_uses_safe_stat_for_batch_and_subtitle_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_batch = tmp_path / "batch-001.mp4"
    second_batch = tmp_path / "batch-002.mp4"
    subtitle_path = first_batch.with_suffix(".vtt")
    first_batch.write_bytes(b"video")
    second_batch.write_bytes(b"video")
    subtitle_path.write_text("WEBVTT", encoding="utf-8")
    base_output = tmp_path / "dubbed.mp4"
    stitched_output = tmp_path / "dubbed.full.mp4"
    parsed_subtitles: list[Path] = []
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs):
        if path in {first_batch, second_batch, subtitle_path}:
            raise AssertionError("stitched input paths should be probed via safe_stat")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path in {first_batch, second_batch, subtitle_path}:
            raise AssertionError("stitched input files should be probed via safe_stat")
        return original_is_file(path, *args, **kwargs)

    def fake_concat_video_segments_copy(_ordered, destination: Path) -> None:
        destination.write_bytes(b"stitched")

    def fake_parse_dialogues(path: Path):
        parsed_subtitles.append(path)
        return []

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(stitching, "_segments_safe_for_stream_copy_concat", lambda _ordered: True)
    monkeypatch.setattr(stitching, "_concat_video_segments_copy", fake_concat_video_segments_copy)
    monkeypatch.setattr(stitching, "_validate_stitched_video", lambda _path: None)
    monkeypatch.setattr(stitching, "_probe_duration_seconds", lambda _path: 1.0)
    monkeypatch.setattr(stitching, "_parse_dialogues", fake_parse_dialogues)
    monkeypatch.setattr(stitching, "_write_webvtt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stitching, "render_ass_for_block", lambda *_args, **_kwargs: None)

    result = stitching.stitch_dub_batches(
        [first_batch, second_batch],
        base_output=base_output,
        language_code="en",
        include_transliteration=False,
        transliterator=None,
    )

    assert result == (stitched_output, stitched_output.with_suffix(".vtt"), stitched_output.with_suffix(".ass"))
    assert parsed_subtitles == [subtitle_path]
