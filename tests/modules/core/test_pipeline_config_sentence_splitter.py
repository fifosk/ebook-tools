from __future__ import annotations

from modules.config_manager import RuntimeContext
from modules.core.config import build_pipeline_config


def _context(tmp_path):
    return RuntimeContext(
        working_dir=tmp_path / "work",
        output_dir=tmp_path / "out",
        tmp_dir=tmp_path / "tmp",
        books_dir=tmp_path / "books",
        ffmpeg_path="ffmpeg",
        ollama_url="http://localhost:11434",
        llm_source="local",
        local_ollama_url="http://localhost:11434",
        cloud_ollama_url="https://ollama.example",
        lmstudio_url="http://localhost:1234",
        lmstudio_macstudio_url="http://studio.local:1234",
        lmstudio_macbook_url="http://macbook.local:1234",
        thread_count=1,
        queue_size=1,
        pipeline_enabled=True,
    )


def test_pipeline_config_reads_sentence_splitter_mode_from_config(tmp_path):
    config = build_pipeline_config(
        _context(tmp_path),
        config={"sentence_splitter_mode": "modern"},
    )

    assert config.sentence_splitter_mode == "modern"


def test_pipeline_config_env_overrides_sentence_splitter_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("EBOOK_SENTENCE_SPLITTER_MODE", "modern")

    config = build_pipeline_config(
        _context(tmp_path),
        config={"sentence_splitter_mode": "regex"},
    )

    assert config.sentence_splitter_mode == "modern"


def test_pipeline_config_rejects_unknown_sentence_splitter_mode(tmp_path):
    config = build_pipeline_config(
        _context(tmp_path),
        config={"sentence_splitter_mode": "future-mode"},
    )

    assert config.sentence_splitter_mode == "regex"
