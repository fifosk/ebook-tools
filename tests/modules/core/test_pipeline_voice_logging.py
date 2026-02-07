from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from unittest.mock import MagicMock

from modules.core.config import PipelineConfig
from modules.core.rendering.pipeline import PipelineState, RenderPipeline
from modules.config_manager.runtime import RuntimeContext


def _build_runtime_context(base_dir: Path) -> RuntimeContext:
    return RuntimeContext(
        working_dir=base_dir,
        output_dir=base_dir,
        tmp_dir=base_dir,
        books_dir=base_dir,
        ffmpeg_path="ffmpeg",
        ollama_url="http://localhost",
        llm_source="local",
        local_ollama_url="http://localhost",
        cloud_ollama_url="http://cloud",
        lmstudio_url="http://localhost:1234",
        thread_count=1,
        queue_size=1,
        pipeline_enabled=True,
        is_tmp_ramdisk=False,
    )


def _build_pipeline(tmp_path: Path) -> RenderPipeline:
    context = _build_runtime_context(tmp_path)
    config = PipelineConfig(
        context=context,
        working_dir=tmp_path,
        output_dir=tmp_path,
        tmp_dir=tmp_path,
        books_dir=tmp_path,
    )
    return RenderPipeline(pipeline_config=config, transliterator=MagicMock())


def test_update_voice_metadata_logs_unique_roles(monkeypatch, tmp_path) -> None:
    pipeline = _build_pipeline(tmp_path)
    state = PipelineState()

    calls: List[Tuple[object, Tuple[object, ...], Dict[str, Any]]] = []

    def _capture(message: object, *args: object, **kwargs: Any) -> None:
        calls.append((message, args, kwargs))

    monkeypatch.setattr("modules.core.rendering.pipeline.console_info", _capture)

    metadata = {
        "source": {"English": "Fiona"},
        "translation": {"Spanish": "Lucia"},
    }

    pipeline._update_voice_metadata(state, metadata)

    assert state.voice_metadata == {
        "source": {"English": {"Fiona"}},
        "translation": {"Spanish": {"Lucia"}},
    }

    assert len(calls) == 2
    first_message, first_args, first_kwargs = calls[0]
    assert first_message == "%s (%s): %s"
    assert first_args == ("Source voice", "English", "Fiona")
    assert first_kwargs.get("extra", {}).get("event") == "render.voice.detected"
    assert first_kwargs.get("extra", {}).get("attributes") == {
        "role": "source",
        "language": "English",
        "voice": "Fiona",
    }

    second_message, second_args, second_kwargs = calls[1]
    assert second_message == "%s (%s): %s"
    assert second_args == ("Translation voice", "Spanish", "Lucia")
    assert second_kwargs.get("extra", {}).get("attributes") == {
        "role": "translation",
        "language": "Spanish",
        "voice": "Lucia",
    }

    pipeline._update_voice_metadata(state, metadata)
    assert len(calls) == 2
