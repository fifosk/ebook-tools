from __future__ import annotations

from pathlib import Path

import pytest

from modules import config_manager as cfg
from modules.core.config import PipelineConfig
from modules.services import pipeline_service as pipeline_service_module
from modules.services.pipeline_service import (
    PipelineInput,
    PipelineRequest,
    PipelineResponse,
    PipelineService,
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from modules.services.pipeline_types import ConfigPhaseResult, PipelineMetadata

pytestmark = pytest.mark.services


def _runtime_context(tmp_path: Path) -> cfg.RuntimeContext:
    return cfg.RuntimeContext(
        working_dir=tmp_path,
        output_dir=tmp_path / "out",
        tmp_dir=tmp_path / "tmp",
        books_dir=tmp_path / "books",
        ffmpeg_path="ffmpeg",
        ollama_url="http://localhost:11434",
        llm_source="ollama_local",
        local_ollama_url="http://localhost:11434",
        cloud_ollama_url="http://localhost:11434",
        lmstudio_url="http://localhost:1234",
        lmstudio_macstudio_url="http://localhost:1234",
        lmstudio_macbook_url="http://localhost:1234",
        thread_count=1,
        queue_size=1,
        pipeline_enabled=True,
    )


def _pipeline_input(*, media_metadata: object | None = None) -> PipelineInput:
    return PipelineInput(
        input_file="book.epub",
        base_output_file="output",
        input_language="en",
        target_languages=["nl"],
        sentences_per_output_file=10,
        start_sentence=1,
        end_sentence=None,
        stitch_full=False,
        generate_audio=True,
        audio_mode="tts",
        written_mode="text",
        selected_voice="voice",
        output_html=False,
        output_pdf=False,
        add_images=False,
        include_transliteration=False,
        tempo=1.0,
        media_metadata=media_metadata if media_metadata is not None else {},
    )


def test_pipeline_input_normalizes_discovery_metadata_identifiers() -> None:
    pipeline_input = _pipeline_input(
        media_metadata=PipelineMetadata.from_mapping(
            {
                "acquisition_provider": " OpenLibrary ",
                "source_kind": " LOCAL_EPUB ",
                "acquisition_candidate_id": "OpenLibrary:/works/OL45883W",
                "media_metadata_lookup": {
                    "provider": " Internet_Archive ",
                    "candidate_id": "InternetArchive:MixedCase",
                },
            }
        )
    )

    metadata = pipeline_input.media_metadata.as_dict()

    assert metadata["acquisition_provider"] == "openlibrary"
    assert metadata["source_kind"] == "local_epub"
    assert metadata["media_metadata_lookup"]["provider"] == "internet_archive"
    assert metadata["acquisition_candidate_id"] == "OpenLibrary:/works/OL45883W"
    assert metadata["media_metadata_lookup"]["candidate_id"] == "InternetArchive:MixedCase"


def test_pipeline_serializers_normalize_discovery_metadata_identifiers() -> None:
    request = PipelineRequest(
        config={},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=_pipeline_input(
            media_metadata={
                "source_provider": " Manual_Downloads ",
                "source_url": "HTTPS://Example.test/Book.EPUB",
            }
        ),
    )
    response = PipelineResponse(
        success=True,
        metadata=PipelineMetadata.from_mapping(
            {
                "source_kind": " NAS_VIDEO ",
                "youtube": {"provider": " Youtube_Search "},
                "source_url": "HTTPS://Example.test/Video.MP4",
            }
        ),
    )

    request_payload = serialize_pipeline_request(request)
    response_payload = serialize_pipeline_response(response)

    assert (
        request_payload["inputs"]["media_metadata"]["source_provider"]
        == "manual_downloads"
    )
    assert (
        request_payload["inputs"]["media_metadata"]["source_url"]
        == "HTTPS://Example.test/Book.EPUB"
    )
    assert response_payload["media_metadata"]["source_kind"] == "nas_video"
    assert response_payload["media_metadata"]["youtube"]["provider"] == "youtube_search"
    assert response_payload["media_metadata"]["source_url"] == "HTTPS://Example.test/Video.MP4"


def test_submission_metadata_merge_and_inference_normalize_identifiers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_infer_metadata(
        input_file: str,
        *,
        existing_metadata: dict[str, object],
        force_refresh: bool,
    ):
        assert input_file == "book.epub"
        assert force_refresh is False
        assert existing_metadata["source_kind"] == "local_epub"
        assert existing_metadata["media_metadata_lookup"]["provider"] == "openlibrary"
        return {
            **existing_metadata,
            "source_provider": " Internet_Archive ",
            "media_metadata_lookup": {
                **existing_metadata["media_metadata_lookup"],
                "selected_provider": " Gutenberg ",
            },
        }

    def fake_prepare_configuration(
        _request: PipelineRequest, context: cfg.RuntimeContext
    ) -> ConfigPhaseResult:
        return ConfigPhaseResult(
            pipeline_config=PipelineConfig(
                context=context,
                working_dir=context.working_dir,
                output_dir=context.output_dir,
                tmp_dir=context.tmp_dir,
                books_dir=context.books_dir,
                max_words=10,
            ),
            generate_audio=True,
            audio_mode="tts",
        )

    monkeypatch.setattr(
        pipeline_service_module.metadata_manager,
        "infer_metadata",
        fake_infer_metadata,
    )
    monkeypatch.setattr(
        pipeline_service_module.config_phase,
        "prepare_configuration",
        fake_prepare_configuration,
    )
    monkeypatch.setattr(
        pipeline_service_module.ingestion,
        "get_refined_sentences",
        lambda *_args, **_kwargs: (["One sentence."], False),
    )

    request = PipelineRequest(
        config={
            "media_metadata": {
                "source_kind": " LOCAL_EPUB ",
                "media_metadata_lookup": {"provider": " OpenLibrary "},
            }
        },
        context=_runtime_context(tmp_path),
        environment_overrides={},
        pipeline_overrides={},
        inputs=_pipeline_input(media_metadata={}),
    )

    service = PipelineService(job_manager=object())  # type: ignore[arg-type]
    snapshot = service._prepare_submission_metadata(request)

    assert snapshot is not None
    assert snapshot.media_metadata["source_kind"] == "local_epub"
    assert snapshot.media_metadata["source_provider"] == "internet_archive"
    assert snapshot.media_metadata["media_metadata_lookup"]["provider"] == "openlibrary"
    assert snapshot.media_metadata["media_metadata_lookup"]["selected_provider"] == "gutenberg"
    assert request.inputs.media_metadata.as_dict() == snapshot.media_metadata
