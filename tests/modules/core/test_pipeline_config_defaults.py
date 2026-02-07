import os
from pathlib import Path

import pytest

from modules.audio.backends import get_default_backend_name
from modules.config_manager.runtime import RuntimeContext
from modules.core.config import build_pipeline_config
from modules.core.rendering.pipeline import PipelineState, RenderPipeline
from modules.render.backends.polly import PollyAudioSynthesizer

pytestmark = pytest.mark.config


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
        lmstudio_url="http://localhost:1234",
        thread_count=1,
        queue_size=1,
        pipeline_enabled=True,
    )


def test_build_pipeline_config_defaults_missing_backends(tmp_path):
    context = _build_runtime_context(tmp_path)

    # When no explicit backend is provided, build_pipeline_config should
    # resolve to the platform default.
    config = {}
    pipeline_config = build_pipeline_config(context, config, {})

    assert pipeline_config.tts_backend == get_default_backend_name()


def test_build_pipeline_config_converts_auto_backend(tmp_path):
    context = _build_runtime_context(tmp_path)

    pipeline_config = build_pipeline_config(context, {"tts_backend": "auto"}, {})

    assert pipeline_config.tts_backend == get_default_backend_name()


def test_apply_runtime_settings_exports_audio_api_env(tmp_path, monkeypatch):
    context = _build_runtime_context(tmp_path)
    pipeline_config = build_pipeline_config(
        context,
        {
            "audio_api_base_url": "https://audio.example",
            "audio_api_timeout_seconds": 30,
            "audio_api_poll_interval_seconds": 0.5,
        },
        {},
    )

    monkeypatch.setattr(
        "modules.core.config.llm_client_manager.configure_default_client",
        lambda **kwargs: None,
    )
    sentinel_client = object()
    monkeypatch.setattr(
        "modules.core.config.create_client",
        lambda **kwargs: sentinel_client,
    )
    for key in (
        "EBOOK_AUDIO_API_BASE_URL",
        "EBOOK_AUDIO_API_TIMEOUT_SECONDS",
        "EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)

    pipeline_config.apply_runtime_settings()

    assert os.environ["EBOOK_AUDIO_API_BASE_URL"] == "https://audio.example"
    assert os.environ["EBOOK_AUDIO_API_TIMEOUT_SECONDS"] == "30.0"
    assert os.environ["EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS"] == "0.5"
    assert pipeline_config.translation_client is sentinel_client

    for key in (
        "EBOOK_AUDIO_API_BASE_URL",
        "EBOOK_AUDIO_API_TIMEOUT_SECONDS",
        "EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)


def test_apply_runtime_settings_clears_audio_api_env_when_unset(tmp_path, monkeypatch):
    context = _build_runtime_context(tmp_path)
    pipeline_config = build_pipeline_config(context, {}, {})
    pipeline_config.audio_api_base_url = None
    pipeline_config.audio_api_timeout_seconds = None
    pipeline_config.audio_api_poll_interval_seconds = None

    monkeypatch.setattr(
        "modules.core.config.llm_client_manager.configure_default_client",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "modules.core.config.create_client",
        lambda **kwargs: object(),
    )

    monkeypatch.setenv("EBOOK_AUDIO_API_BASE_URL", "stale")
    monkeypatch.setenv("EBOOK_AUDIO_API_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS", "1")

    pipeline_config.apply_runtime_settings()

    assert "EBOOK_AUDIO_API_BASE_URL" not in os.environ
    assert "EBOOK_AUDIO_API_TIMEOUT_SECONDS" not in os.environ
    assert "EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS" not in os.environ


def test_render_pipeline_passes_audio_api_configuration(tmp_path):
    context = _build_runtime_context(tmp_path)
    pipeline_config = build_pipeline_config(
        context,
        {
            "audio_api_base_url": "https://audio.example",
            "audio_api_timeout_seconds": 12,
            "audio_api_poll_interval_seconds": 0.75,
        },
        {},
    )

    # Verify pipeline_config stores audio API settings that will be
    # forwarded to PollyAudioSynthesizer at runtime.
    assert pipeline_config.audio_api_base_url == "https://audio.example"
    assert pipeline_config.audio_api_timeout_seconds == 12.0
    assert pipeline_config.audio_api_poll_interval_seconds == 0.75

    synth = PollyAudioSynthesizer(
        base_url=pipeline_config.audio_api_base_url,
        timeout=pipeline_config.audio_api_timeout_seconds,
        poll_interval=pipeline_config.audio_api_poll_interval_seconds,
    )
    assert synth._client_base_url == "https://audio.example"
    assert synth._client_timeout == 12.0
    assert synth._client_poll_interval == 0.75


def test_build_pipeline_config_applies_image_style_template_defaults(tmp_path):
    context = _build_runtime_context(tmp_path)

    pipeline_config = build_pipeline_config(context, {}, {"image_style_template": "wire frame"})

    assert pipeline_config.image_style_template == "wireframe"
    assert pipeline_config.image_steps == 12
    assert pipeline_config.image_cfg_scale == 6.5
