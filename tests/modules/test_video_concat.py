"""Tests for FFmpeg concatenation fallback logic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import subprocess

import pytest

from modules import config_manager as cfg
from modules.audio_video_generator import generate_video_slides_ffmpeg
from pydub import AudioSegment


@pytest.fixture(autouse=True)
def _force_single_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cfg, "get_thread_count", lambda: 1)


def _create_dummy_sentence_video(output_dir: Path, sentence_number: int) -> str:
    path = output_dir / f"sentence_{sentence_number}.mp4"
    path.write_bytes(b"video-data")
    return str(path)


def test_generate_video_slides_ffmpeg_retries_with_transcode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text_blocks = ["Target - Translation"]
    audio_segments = [AudioSegment.silent(duration=1000)]

    def fake_generate_sentence_video(*args, **kwargs) -> str:  # type: ignore[override]
        sentence_number = kwargs.get("sentence_number") or (args[2] if len(args) > 2 else 1)
        path = _create_dummy_sentence_video(tmp_path, sentence_number)
        return path

    monkeypatch.setattr(
        "modules.audio_video_generator.generate_word_synced_sentence_video",
        fake_generate_sentence_video,
    )

    run_calls: List[List[str]] = []

    def fake_run(cmd, stdout=None, stderr=None):  # noqa: ANN001
        run_calls.append(cmd)
        if len(run_calls) == 1:
            return subprocess.CompletedProcess(cmd, 183, stdout=b"", stderr=b"File exists")
        final_path = Path(cmd[-1])
        final_path.write_bytes(b"merged-video")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr("modules.audio_video_generator.subprocess.run", fake_run)

    final_path = generate_video_slides_ffmpeg(
        text_blocks,
        audio_segments,
        str(tmp_path),
        batch_start=1,
        batch_end=1,
        base_no_ext="output",
        cover_img=None,
        book_author="Author",
        book_title="Title",
        cumulative_word_counts=[0],
        total_word_count=10,
        macos_reading_speed=100,
        input_language="en",
        total_sentences=1,
        tempo=1.0,
        sync_ratio=1.0,
        word_highlighting=False,
        cleanup=False,
    )

    assert len(run_calls) == 2
    assert run_calls[0][-2:] == ["copy", final_path]
    assert "libx264" in run_calls[1]
    assert os.path.exists(final_path)
    assert not (tmp_path / "concat_1-1.txt").exists()


def test_generate_video_slides_ffmpeg_succeeds_without_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text_blocks = ["Target - Translation"]
    audio_segments = [AudioSegment.silent(duration=500)]

    def fake_generate_sentence_video(*args, **kwargs) -> str:  # type: ignore[override]
        sentence_number = kwargs.get("sentence_number") or (args[2] if len(args) > 2 else 1)
        return _create_dummy_sentence_video(tmp_path, sentence_number)

    monkeypatch.setattr(
        "modules.audio_video_generator.generate_word_synced_sentence_video",
        fake_generate_sentence_video,
    )

    def fake_run(cmd, stdout=None, stderr=None):  # noqa: ANN001
        final_path = Path(cmd[-1])
        final_path.write_bytes(b"merged-video")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr("modules.audio_video_generator.subprocess.run", fake_run)

    final_path = generate_video_slides_ffmpeg(
        text_blocks,
        audio_segments,
        str(tmp_path),
        batch_start=1,
        batch_end=1,
        base_no_ext="output",
        cover_img=None,
        book_author="Author",
        book_title="Title",
        cumulative_word_counts=[0],
        total_word_count=10,
        macos_reading_speed=100,
        input_language="en",
        total_sentences=1,
        tempo=1.0,
        sync_ratio=1.0,
        word_highlighting=False,
        cleanup=False,
    )

    assert os.path.exists(final_path)
    assert (tmp_path / "concat_1-1.txt").exists() is False
