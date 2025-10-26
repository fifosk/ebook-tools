import types
from pathlib import Path

from modules.audio.backends import get_default_backend_name
from modules.config_manager.runtime import RuntimeContext
from modules.core.config import build_pipeline_config


def _build_runtime_context(tmp_path: Path) -> RuntimeContext:
    working_dir = tmp_path / "work"
    output_dir = tmp_path / "out"
    tmp_dir = tmp_path / "tmp"
    books_dir = tmp_path / "books"
    for directory in (working_dir, output_dir, tmp_dir, books_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return RuntimeContext(
        working_dir=working_dir,
        output_dir=output_dir,
        tmp_dir=tmp_dir,
        books_dir=books_dir,
        ffmpeg_path="ffmpeg",
        ollama_url="http://localhost",
        llm_source="local",
        local_ollama_url="http://localhost",
        cloud_ollama_url="http://cloud",
        thread_count=1,
        queue_size=1,
        pipeline_enabled=True,
    )


def test_build_pipeline_config_defaults_missing_backends(tmp_path, monkeypatch):
    context = _build_runtime_context(tmp_path)

    # Ensure legacy settings without explicit backends don't break resolution.
    monkeypatch.setattr(
        "modules.config_manager.cfg.get_settings",
        lambda: types.SimpleNamespace(tts_backend=None, tts_executable_path=None),
        raising=False,
    )

    config = {}
    pipeline_config = build_pipeline_config(context, config, {})

    assert pipeline_config.tts_backend == get_default_backend_name()
    assert pipeline_config.video_backend == "ffmpeg"


def test_build_pipeline_config_converts_auto_backend(tmp_path):
    context = _build_runtime_context(tmp_path)

    pipeline_config = build_pipeline_config(context, {"tts_backend": "auto"}, {})

    assert pipeline_config.tts_backend == get_default_backend_name()
