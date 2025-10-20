from types import SimpleNamespace as Namespace

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
        llm_source=None,
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


def test_resolve_slide_worker_count_defaults_to_threads():
    assert (
        pipeline_runner._resolve_slide_worker_count("thread", None, 5) == 5
    )
    assert (
        pipeline_runner._resolve_slide_worker_count("process", 3, 5) == 3
    )
    assert pipeline_runner._resolve_slide_worker_count("off", 8, 5) == 0


@pytest.mark.parametrize(
    "thread_count, slide_workers, job_workers, queue_size",
    [
        (2, 0, 1, 20),
        (4, 2, 2, 50),
        (8, 6, 4, 100),
    ],
)
def test_estimate_required_file_descriptors_scales(
    thread_count, slide_workers, job_workers, queue_size
):
    result = pipeline_runner._estimate_required_file_descriptors(
        thread_count=thread_count,
        slide_workers=slide_workers,
        job_workers=job_workers,
        queue_size=queue_size,
    )
    assert result >= 1024

    larger = pipeline_runner._estimate_required_file_descriptors(
        thread_count=thread_count + 2,
        slide_workers=slide_workers + 2,
        job_workers=job_workers + 1,
        queue_size=queue_size + 10,
    )
    assert larger > result
