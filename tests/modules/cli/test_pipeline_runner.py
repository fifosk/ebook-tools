from argparse import Namespace

import pytest

from modules.cli import pipeline_runner


def test_calculate_end_sentence_handles_offsets():
    config = {}
    result = pipeline_runner._calculate_end_sentence(config, 5, "+3")
    assert result == 8
    result = pipeline_runner._calculate_end_sentence(config, 5, "10")
    assert result == 10
    assert pipeline_runner._calculate_end_sentence(config, 5, None) is None


def test_build_environment_overrides_reads_namespace(monkeypatch):
    monkeypatch.setenv("EBOOKS_DIR", "/tmp/books")
    args = Namespace(
        ebooks_dir=None,
        working_dir="/work",
        output_dir=None,
        tmp_dir=None,
        ffmpeg_path="/usr/bin/ffmpeg",
        ollama_url=None,
        thread_count=4,
    )
    overrides = pipeline_runner.build_environment_overrides(args)
    assert overrides["ebooks_dir"] == "/tmp/books"
    assert overrides["working_dir"] == "/work"
    assert overrides["thread_count"] == 4


def test_prepare_output_path_creates_directory(tmp_path):
    active_context = Namespace(output_dir=str(tmp_path))
    result = pipeline_runner._prepare_output_path(
        None,
        ["Arabic", "French"],
        "sample.epub",
        active_context,
    )
    assert (tmp_path / "Arabic_French_sample" / "Arabic_French_sample.html").exists()
    assert result.endswith("Arabic_French_sample.html")
