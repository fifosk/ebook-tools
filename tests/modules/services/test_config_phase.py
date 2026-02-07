from __future__ import annotations

from pathlib import Path

from modules.config_manager.runtime import RuntimeContext
from modules.services.pipeline_phases.config_phase import prepare_configuration
from modules.services.pipeline_service import PipelineInput, PipelineRequest
from modules.audio.backends import MacOSSayBackend


def _context(tmp_path: Path) -> RuntimeContext:
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


def _inputs(selected_voice: str) -> PipelineInput:
    return PipelineInput(
        input_file="book.epub",
        base_output_file="out.html",
        input_language="English",
        target_languages=["Slovenian"],
        sentences_per_output_file=1,
        start_sentence=1,
        end_sentence=None,
        stitch_full=False,
        generate_audio=True,
        audio_mode="4",
        written_mode="4",
        selected_voice=selected_voice,
        output_html=False,
        output_pdf=False,
        include_transliteration=True,
        tempo=1.0,
    )


def test_prepare_configuration_forces_macos_backend_for_macos_voice(tmp_path):
    context = _context(tmp_path)
    request = PipelineRequest(
        config={"tts_backend": "gtts"},
        context=context,
        environment_overrides={},
        pipeline_overrides={},
        inputs=_inputs("macOS-auto"),
    )

    result = prepare_configuration(request, context)

    assert result.pipeline_config.tts_backend == MacOSSayBackend.name
    assert result.pipeline_config.selected_voice == "macOS-auto"


def test_prepare_configuration_forces_macos_backend_for_voice_override(tmp_path):
    context = _context(tmp_path)
    request = PipelineRequest(
        config={"tts_backend": "gtts"},
        context=context,
        environment_overrides={},
        pipeline_overrides={},
        inputs=_inputs("gTTS"),
    )
    # Inject macOS override for target language
    request.inputs.voice_overrides = {"sl": "macOS-auto"}

    result = prepare_configuration(request, context)

    assert result.pipeline_config.tts_backend == MacOSSayBackend.name
    assert result.pipeline_config.voice_overrides == {"sl": "macOS-auto"}
