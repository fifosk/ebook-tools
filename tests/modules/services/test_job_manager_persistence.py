from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from modules.progress_tracker import ProgressEvent, ProgressSnapshot
from modules.services.file_locator import FileLocator
from modules.services.job_manager.job import PipelineJob, PipelineJobStatus
from modules.services.job_manager.persistence import PipelineJobPersistence
from modules.services.pipeline_service import PipelineInput, PipelineRequest, PipelineResponse
from modules.services.pipeline_types import PipelineMetadata


def _build_request() -> PipelineRequest:
    return PipelineRequest(
        config={"auto_metadata": False},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=PipelineInput(
            input_file="input.epub",
            base_output_file="output",
            input_language="en",
            target_languages=["en"],
            sentences_per_output_file=10,
            start_sentence=0,
            end_sentence=None,
            stitch_full=False,
            generate_audio=True,
            audio_mode="tts",
            written_mode="text",
            selected_voice="voice",
            output_html=False,
            output_pdf=False,
            generate_video=False,
            include_transliteration=False,
            tempo=1.0,
            book_metadata=PipelineMetadata.from_mapping({"title": "Test"}),
        ),
    )


def _progress_event() -> ProgressEvent:
    return ProgressEvent(
        event_type="file_chunk_generated",
        snapshot=ProgressSnapshot(
            completed=1,
            total=10,
            elapsed=1.0,
            speed=1.0,
            eta=9.0,
        ),
        timestamp=123.456,
        metadata={
            "stage": "render",
            "chunk_id": "chunk-1",
            "generated_files": {
                "chunks": [
                    {
                        "chunk_id": "chunk-1",
                        "files": [
                            {"type": "audio", "relative_path": "chunk-1/audio.mp3"},
                        ],
                    }
                ]
            },
        },
    )


def test_snapshot_round_trip(tmp_path: Path) -> None:
    locator = FileLocator(storage_dir=tmp_path, base_url="https://cdn.example.invalid")
    persistence = PipelineJobPersistence(locator)

    job_id = "job-123"
    job_root = locator.resolve_path(job_id)
    media_path = job_root / "chunk-1" / "audio.mp3"
    media_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_bytes(b"data")

    request = _build_request()
    response = PipelineResponse(success=True, metadata=PipelineMetadata.from_mapping({"title": "Test"}))

    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        request=request,
        result=response,
        resume_context=None,
        user_id="user",
        user_role="role",
        generated_files={
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "files": [
                        {"type": "audio", "path": str(media_path)},
                        {"type": "text", "relative_path": "chunk-1/transcript.txt"},
                    ],
                }
            ]
        },
    )
    job.last_event = _progress_event()

    metadata = persistence.snapshot(job)

    assert metadata.request_payload is not None
    assert metadata.result is not None
    assert metadata.last_event is not None
    assert metadata.generated_files is not None

    restored = persistence.build_job(metadata)

    assert restored.job_id == job.job_id
    assert restored.status == job.status
    assert restored.request_payload == metadata.request_payload
    assert restored.result_payload == metadata.result
    assert restored.generated_files == metadata.generated_files
    assert restored.last_event == job.last_event


def test_apply_event_updates_generated_files(tmp_path: Path) -> None:
    locator = FileLocator(storage_dir=tmp_path, base_url="https://cdn.example.invalid")
    persistence = PipelineJobPersistence(locator)

    job_id = "job-apply"
    request = _build_request()
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
        request=request,
    )

    event = _progress_event()
    metadata = persistence.apply_event(job, event)

    assert metadata.last_event is not None
    assert metadata.generated_files is not None
    assert job.last_event == event
    assert job.generated_files == metadata.generated_files

    # Ensure URLs are derived from the locator when possible.
    generated_files = metadata.generated_files
    assert generated_files is not None
    chunk_files = generated_files["chunks"][0]["files"]
    assert chunk_files[0]["path"].startswith(str(locator.resolve_path(job_id)))
    assert chunk_files[0]["url"].startswith(locator.base_url)
