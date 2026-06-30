from __future__ import annotations

from pathlib import Path

import pytest

from modules.services.file_locator import FileLocator
from modules.services.job_manager.source_persistence import persist_source_file
from modules.services.pipeline_service import PipelineInput, PipelineRequest

pytestmark = pytest.mark.services


def _request_for_input(input_file: str) -> PipelineRequest:
    return PipelineRequest(
        config={},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=PipelineInput(
            input_file=input_file,
            base_output_file="output",
            input_language="en",
            target_languages=["fr"],
            sentences_per_output_file=1,
            start_sentence=0,
            end_sentence=None,
            stitch_full=False,
            generate_audio=False,
            audio_mode="tts",
            written_mode="text",
            selected_voice="voice",
            output_html=False,
            output_pdf=False,
            add_images=False,
            include_transliteration=False,
            tempo=1.0,
        ),
    )


def test_persist_source_file_uses_safe_stat_for_source_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_root = tmp_path / "storage"
    selected = tmp_path / "books" / "latest.epub"
    selected.parent.mkdir()
    selected.write_bytes(b"epub bytes")
    selected_resolved = selected.resolve()
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs):
        if path == selected_resolved:
            raise AssertionError("source persistence should use safe_stat instead of exists")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path == selected_resolved:
            raise AssertionError("source persistence should use safe_stat instead of is_file")
        return original_is_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    relative_path = persist_source_file(
        "job-source",
        _request_for_input(str(selected_resolved)),
        FileLocator(storage_dir=storage_root),
    )

    assert relative_path == "data/latest.epub"
    mirrored = storage_root / "job-source" / "data" / "latest.epub"
    assert original_exists(mirrored)
    assert mirrored.read_bytes() == b"epub bytes"
