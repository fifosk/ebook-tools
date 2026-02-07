from __future__ import annotations

from pathlib import Path

import pytest
from pydub import AudioSegment

from modules.config.loader import RenderingConfig
from modules.core.rendering.exporters import (
    BatchExportContext,
    BatchExportRequest,
    BatchExporter,
)


@pytest.fixture(autouse=True)
def disable_rendering_ramdisk(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure exporter tests do not rely on the host RAM disk."""

    def _fake_config() -> RenderingConfig:
        return RenderingConfig(
            video_concurrency=1,
            audio_concurrency=1,
            text_concurrency=1,
            video_backend="ffmpeg",
            audio_backend="polly",
            ramdisk_enabled=False,
            ramdisk_path=str(tmp_path / "render"),
            video_backend_settings={},
        )

    monkeypatch.setattr(
        "modules.core.rendering.exporters.get_rendering_config",
        _fake_config,
    )


def _build_context(tmp_path: Path) -> BatchExportContext:
    return BatchExportContext(
        base_dir=str(tmp_path),
        base_name="Agatha_Christie_The_Man_in_the_Brown_Suit_EN_AR",
        cover_image=None,
        book_author="Agatha Christie",
        book_title="The Man in the Brown Suit",
        global_cumulative_word_counts=[0],
        total_book_words=0,
        macos_reading_speed=100,
        input_language="English",
        total_sentences=100,
        tempo=1.0,
        sync_ratio=0.9,
        word_highlighting=True,
        highlight_granularity="word",
        selected_voice="macOS-auto-male",
        voice_name="macOS-auto-male",
    )


def test_build_sentence_metadata_respects_existing_gate_values(tmp_path: Path) -> None:
    exporter = BatchExporter(_build_context(tmp_path))
    block = "Sentence 1\nOriginal content\nTranslated content"

    result = exporter._build_sentence_metadata(  # type: ignore[attr-defined]
        block=block,
        audio_segment=AudioSegment.silent(duration=0),
        sentence_number=1,
        original_phase_duration=0.0,
        translation_phase_duration=0.0,
        gap_before_translation=0.0,
        gap_after_translation=0.0,
        word_meta={"startGate": 1.0, "endGate": 2.75},
    )

    assert result["startGate"] == pytest.approx(1.0)
    assert result["endGate"] == pytest.approx(2.75)


def test_exporter_handles_basic_batch_without_audio(tmp_path: Path) -> None:
    exporter = BatchExporter(_build_context(tmp_path))
    block = "Sentence 1\nOriginal content\nTranslated content"
    request = BatchExportRequest(
        start_sentence=1,
        end_sentence=1,
        written_blocks=[block],
        target_language="Arabic",
        output_html=True,
        output_pdf=False,
        generate_audio=False,
        audio_segments=[],
        sentence_blocks=[block],
        sentence_metadata=[{"sentence_number": 1}],
    )

    result = exporter.export(request)

    assert result.chunk_id
    html_path = Path(result.artifacts["html"])
    assert html_path.exists()
