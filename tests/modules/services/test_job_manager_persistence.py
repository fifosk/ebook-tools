from __future__ import annotations

import json
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
            media_metadata=PipelineMetadata.from_mapping({"title": "Test"}),
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
                        "sentences": [
                            {
                                "sentence_number": 1,
                                "original": {"text": "Hello", "tokens": ["Hello"]},
                                "timeline": [],
                                "counts": {"original": 1},
                            }
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
                    "sentences": [
                        {
                            "sentence_number": 1,
                            "original": {"text": "Hello", "tokens": ["Hello"]},
                            "timeline": [],
                            "counts": {"original": 1},
                        }
                    ],
                    "timing_tracks": {
                        "translation": [
                            {
                                "start": 1.5,
                                "end": 2.0,
                                "sentenceIdx": "1",
                                "text": "مرحبا",
                            }
                        ],
                        "mix": [
                            {
                                "start": 1.0,
                                "end": 2.5,
                                "sentenceIdx": "1",
                                "lane": "mix",
                            }
                        ],
                    },
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
    metadata_root = locator.metadata_root(job_id)
    chunk_file = metadata_root / "chunk_0000.json"
    assert chunk_file.is_file()
    chunk_payload = json.loads(chunk_file.read_text(encoding="utf-8"))
    assert chunk_payload.get("sentences")
    first_sentence = chunk_payload["sentences"][0]
    assert first_sentence.get("original", {}).get("text") == "Hello"
    timing_tracks = chunk_payload.get("timingTracks")
    assert isinstance(timing_tracks, dict)
    assert timing_tracks["translation"][0]["start"] == 1.5

    chunk_entries = metadata.generated_files.get("chunks")
    assert isinstance(chunk_entries, list)
    manifest_entry = chunk_entries[0]
    assert manifest_entry.get("metadata_path") == "metadata/chunk_0000.json"
    assert manifest_entry.get("sentence_count") == 1
    assert "sentences" not in manifest_entry

    assert not (metadata_root / "timing_index.json").exists()
    assert metadata.result is not None
    assert "timing_tracks" not in metadata.result

    restored = persistence.build_job(metadata)

    assert restored.job_id == job.job_id
    assert restored.status == job.status
    assert restored.request_payload == metadata.request_payload
    assert restored.result_payload == metadata.result
    assert restored.generated_files == metadata.generated_files
    assert restored.last_event == job.last_event


def test_snapshot_mirrors_cover_asset(tmp_path: Path) -> None:
    locator = FileLocator(storage_dir=tmp_path, base_url="https://cdn.example.invalid")
    persistence = PipelineJobPersistence(locator)

    job_id = "job-cover"
    cover_source = tmp_path / "covers" / "original-cover.jpg"
    cover_source.parent.mkdir(parents=True, exist_ok=True)
    cover_source.write_bytes(b"cover-bytes")

    request = _build_request()
    response = PipelineResponse(
        success=True,
        metadata=PipelineMetadata.from_mapping({"book_cover_file": str(cover_source)}),
    )

    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        request=request,
        result=response,
    )

    metadata = persistence.snapshot(job)

    metadata_root = locator.metadata_root(job_id)
    stored_cover = metadata_root / "cover.jpg"
    assert stored_cover.is_file()
    assert stored_cover.read_bytes() == b"cover-bytes"

    assert metadata.result is not None
    book_metadata = metadata.result.get("media_metadata")
    assert isinstance(book_metadata, dict)
    assert book_metadata.get("job_cover_asset") == "metadata/cover.jpg"
    assert job.result is not None
    assert job.result.metadata.get("job_cover_asset") == "metadata/cover.jpg"


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
    assert generated_files["chunks"][0].get("metadata_path") is not None
