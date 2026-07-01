from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_file_locator,
    get_pipeline_service,
    get_request_user,
)
from modules.webapi.media_routes import router as legacy_media_router
from modules.webapi.routes.media import media_list
from modules.services.job_manager import PipelineJob, PipelineJobStatus

pytestmark = pytest.mark.webapi


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)


class _StubPipelineService:
    def __init__(self, job: PipelineJob | None = None, *, error: Exception | None = None) -> None:
        self._job = job
        self._error = error
        self.calls: list[tuple[str, str | None, str | None]] = []

    def get_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        self.calls.append((job_id, user_id, user_role))
        if self._error is not None:
            raise self._error
        if self._job is None:
            raise KeyError(job_id)
        return self._job


class _TrackerStub:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = payload

    def get_generated_files(self) -> Mapping[str, Any]:
        return self._payload


@pytest.fixture
def api_app(tmp_path):
    app = create_app()
    file_locator = FileLocator(storage_dir=tmp_path, base_url="https://example.invalid/jobs")

    def _override_locator() -> FileLocator:
        return file_locator

    app.dependency_overrides[get_file_locator] = _override_locator
    yield app, file_locator
    app.dependency_overrides.clear()


def test_get_job_media_returns_completed_entries(api_app) -> None:
    app, file_locator = api_app
    job_id = "job-media"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    job_root = file_locator.resolve_path(job_id)
    file_path = job_root / "media" / "chunk-001" / "sample.mp3"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"hello world")

    expected_mtime = datetime(2024, 1, 1, tzinfo=timezone.utc)
    os.utime(file_path, (expected_mtime.timestamp(), expected_mtime.timestamp()))

    job.generated_files = {
        "files": [
            {
                "type": "audio",
                "relative_path": "media/chunk-001/sample.mp3",
            }
        ]
    }

    service = _StubPipelineService(job)

    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    payload = response.json()

    assert response.status_code == 200
    assert "audio" in payload["media"]
    assert "chunks" in payload
    assert isinstance(payload["chunks"], list)
    assert "complete" in payload
    assert payload["diagnostics"] == {
        "mediaFileCount": 1,
        "chunkCount": 0,
        "chunkFileCount": 0,
        "audioFileCount": 1,
        "imageFileCount": 0,
        "chunksWithAudio": 0,
        "chunksWithTiming": 0,
        "chunksWithImages": 0,
        "chunksWithoutFiles": 0,
        "chunksWithoutMetadata": 0,
        "filesWithoutUrl": 0,
        "filesWithoutSize": 0,
    }
    entry = payload["media"]["audio"][0]
    assert entry["name"] == "sample.mp3"
    assert entry["size"] == file_path.stat().st_size
    assert entry["source"] == "completed"
    assert entry["url"].endswith("media/chunk-001/sample.mp3")
    assert datetime.fromisoformat(entry["updated_at"]) == expected_mtime


def test_stream_chunk_audio_track_uses_safe_stat_for_audio_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(legacy_media_router)
    file_locator = FileLocator(storage_dir=tmp_path, base_url="https://example.invalid/jobs")
    job_id = "job-stream-audio"
    chunk_id = "chunk-001"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )
    audio_path = file_locator.resolve_path(job_id, "media/chunk-001/translation.mp3")
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"audio bytes")
    job.generated_files = {
        "chunks": [
            {
                "chunk_id": chunk_id,
                "audioTracks": {
                    "translation": "media/chunk-001/translation.mp3",
                },
            }
        ],
    }
    service = _StubPipelineService(job)
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs):
        if path == audio_path:
            raise AssertionError("chunk audio streaming should use safe_stat instead of exists")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path == audio_path:
            raise AssertionError("chunk audio streaming should use safe_stat instead of is_file")
        return original_is_file(path, *args, **kwargs)

    app.dependency_overrides[get_file_locator] = lambda: file_locator
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="test",
        user_role="admin",
    )
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    with TestClient(app) as client:
        response = client.get(f"/api/media/{job_id}/{chunk_id}?track=translation")

    assert response.status_code == 200
    assert response.content == b"audio bytes"
    assert response.headers["Accept-Ranges"] == "bytes"


def test_get_job_media_uses_manifest_size_when_file_is_remote(api_app) -> None:
    app, _file_locator = api_app
    job_id = "job-remote-media"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )
    job.generated_files = {
        "files": [
            {
                "type": "audio",
                "name": "remote-track.mp3",
                "url": "https://cdn.example.invalid/jobs/job-remote-media/remote-track.mp3",
                "size_bytes": 4096,
            }
        ],
        "complete": True,
    }
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    assert response.status_code == 200
    payload = response.json()
    entry = payload["media"]["audio"][0]
    assert entry["name"] == "remote-track.mp3"
    assert entry["url"] == "https://cdn.example.invalid/jobs/job-remote-media/remote-track.mp3"
    assert entry["size"] == 4096
    assert payload["diagnostics"]["filesWithoutUrl"] == 0
    assert payload["diagnostics"]["filesWithoutSize"] == 0


def test_get_job_media_uses_safe_stat_for_local_media_size(
    api_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, file_locator = api_app
    job_id = "job-media-safe-stat"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    job_root = file_locator.resolve_path(job_id)
    file_path = job_root / "media" / "chunk-001" / "sample.mp3"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"hello world")

    job.generated_files = {
        "files": [
            {
                "type": "audio",
                "relative_path": "media/chunk-001/sample.mp3",
            }
        ],
        "complete": True,
    }
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    safe_stat_calls: list[Path] = []
    original_safe_stat = media_list.safe_stat

    def recording_safe_stat(path: Path) -> os.stat_result | None:
        safe_stat_calls.append(path)
        return original_safe_stat(path)

    monkeypatch.setattr(media_list, "safe_stat", recording_safe_stat)

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    assert response.status_code == 200
    assert response.json()["media"]["audio"][0]["size"] == len(b"hello world")
    assert file_path in safe_stat_calls


def test_get_job_media_lazy_chunk_loader_uses_safe_stat_for_manifest_check(
    api_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _file_locator = api_app
    job_id = "job-media-chunk-safe-stat"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )
    job.generated_files = {
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "range_fragment": "00001-00002",
                "start_sentence": 1,
                "end_sentence": 2,
                "files": [
                    {
                        "type": "audio",
                        "name": "translation-1.mp3",
                        "url": "https://cdn.example.invalid/translation-1.mp3",
                    }
                ],
            }
        ],
        "complete": True,
    }
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    safe_stat_calls: list[Path] = []
    original_safe_stat = media_list.safe_stat

    def recording_safe_stat(path: Path) -> os.stat_result | None:
        safe_stat_calls.append(path)
        return original_safe_stat(path)

    monkeypatch.setattr(media_list, "safe_stat", recording_safe_stat)

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    assert response.status_code == 200
    payload = response.json()
    assert payload["chunks"][0]["chunkId"] == "chunk-001"
    assert payload["chunks"][0]["sentenceCount"] == 1
    assert any(
        path.name == "job.json" and path.parent.name == "metadata"
        for path in safe_stat_calls
    )


def test_get_job_media_sorts_chunks_by_sentence_range(api_app) -> None:
    app, _file_locator = api_app
    job_id = "job-out-of-order-chunks"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )
    job.generated_files = {
        "complete": True,
        "chunks": [
            {
                "chunk_id": "chunk-2230",
                "range_fragment": "02230-02239",
                "start_sentence": 2230,
                "end_sentence": 2240,
                "files": [
                    {
                        "type": "audio",
                        "name": "translation-2230.mp3",
                        "url": "https://cdn.example.invalid/translation-2230.mp3",
                    }
                ],
            },
            {
                "chunk_id": "chunk-2210",
                "range_fragment": "02210-02219",
                "start_sentence": 2210,
                "end_sentence": 2220,
                "files": [
                    {
                        "type": "audio",
                        "name": "translation-2210.mp3",
                        "url": "https://cdn.example.invalid/translation-2210.mp3",
                    }
                ],
            },
            {
                "chunk_id": "chunk-2220",
                "range_fragment": "02220-02229",
                "start_sentence": 2220,
                "end_sentence": 2230,
                "files": [
                    {
                        "type": "audio",
                        "name": "translation-2220.mp3",
                        "url": "https://cdn.example.invalid/translation-2220.mp3",
                    }
                ],
            },
        ],
    }
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    assert response.status_code == 200
    payload = response.json()
    assert [chunk["chunkId"] for chunk in payload["chunks"]] == [
        "chunk-2210",
        "chunk-2220",
        "chunk-2230",
    ]
    assert [chunk["startSentence"] for chunk in payload["chunks"]] == [2210, 2220, 2230]


def test_get_job_media_records_safe_timing(
    api_app,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, file_locator = api_app
    job_id = "sensitive-media-job-id"
    user_id = "sensitive-user-id"
    logger = _RecordingLogger()
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    job_root = file_locator.resolve_path(job_id)
    file_path = job_root / "media" / "chunk-001" / "sample.mp3"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"hello world")

    job.generated_files = {
        "files": [
            {
                "type": "audio",
                "relative_path": "media/chunk-001/sample.mp3",
            }
        ],
        "complete": True,
    }
    service = _StubPipelineService(job)
    monkeypatch.setattr(media_list, "logger", logger)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            f"/pipelines/jobs/{job_id}/media",
            headers={"X-User-Id": user_id, "X-User-Role": "editor"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline media manifest" in rendered_logs
    assert "operation=job_media" in rendered_logs
    assert "result=success" in rendered_logs
    assert "source=completed" in rendered_logs
    assert "categories=1" in rendered_logs
    assert "files=1" in rendered_logs
    assert "chunks=0" in rendered_logs
    assert "complete=True" in rendered_logs
    assert job_id not in rendered_logs
    assert user_id not in rendered_logs
    assert "sample.mp3" not in rendered_logs

    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_response.text)
    }
    metric = families["ebook_tools_media_route_duration_seconds"]
    assert any(
        sample.labels.get("operation") == "job_media"
        and sample.labels.get("result") == "success"
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )


def test_get_job_media_normalizes_padded_job_id(api_app) -> None:
    app, file_locator = api_app
    job_id = "job-media-padded"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )
    job_root = file_locator.resolve_path(job_id)
    file_path = job_root / "media" / "chunk-001" / "sample.mp3"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"hello world")
    job.generated_files = {
        "files": [
            {
                "type": "audio",
                "relative_path": "media/chunk-001/sample.mp3",
            }
        ],
        "complete": True,
    }
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/pipelines/jobs/%20%20job-media-padded%20%20/media")

    assert response.status_code == 200
    assert response.json()["media"]["audio"][0]["name"] == "sample.mp3"
    assert service.calls == [(job_id, None, None)]


def test_get_job_media_rejects_blank_job_id_without_service_lookup(api_app) -> None:
    app, _file_locator = api_app
    service = _StubPipelineService()
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/pipelines/jobs/%20%20%20/media")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    assert service.calls == []


def test_get_job_media_permission_error_uses_generic_detail(api_app) -> None:
    app, _file_locator = api_app
    service = _StubPipelineService(
        error=PermissionError("alice cannot read /Volumes/Data/private/job-media-secret")
    )
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/pipelines/jobs/%20%20job-media-secret%20%20/media",
            headers={"X-User-Id": "alice", "X-User-Role": "editor"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access job media"}
    rendered = response.text
    assert "alice cannot read" not in rendered
    assert "/Volumes/Data/private" not in rendered
    assert service.calls == [("job-media-secret", "alice", "editor")]


def test_get_job_media_chunk_normalizes_padded_job_id(api_app) -> None:
    app, file_locator = api_app
    job_id = "job-chunk-padded"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )
    metadata_path = file_locator.resolve_path(job_id, "metadata/chunk_0001.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        """
        {
          "sentences": [
            {
              "sentence_number": 1,
              "original": {"text": "Hello", "tokens": ["Hello"]},
              "translation": {"text": "Hola", "tokens": ["Hola"]},
              "timeline": [
                {
                  "duration": 1.0,
                  "original_index": 1,
                  "translation_index": 1,
                  "transliteration_index": 1
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    job.generated_files = {
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "metadata_path": "metadata/chunk_0001.json",
                "files": [],
            }
        ]
    }
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/pipelines/jobs/%20%20job-chunk-padded%20%20/media/chunks/chunk-001"
        )

    assert response.status_code == 200
    assert response.json()["sentences"][0]["original"]["text"] == "Hello"
    assert service.calls == [(job_id, None, None)]


def test_get_job_media_populates_sentence_count_from_range(api_app) -> None:
    """sentenceCount must be derived from start/end when not explicitly set.

    During in-progress jobs the tracker may supply chunks with metadata_path
    but without an explicit sentence_count.  The media endpoint must fall back
    to computing the count from start_sentence / end_sentence so the frontend
    can gate interactive playback correctly.
    """
    app, file_locator = api_app
    job_id = "job-progress"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )

    # Create a minimal chunk file on disk so the metadata_path resolves.
    job_root = file_locator.resolve_path(job_id)
    chunk_file = job_root / "metadata" / "chunk_0001.json"
    chunk_file.parent.mkdir(parents=True, exist_ok=True)
    chunk_file.write_text('{"version": 3, "sentence_count": 0}')

    audio_path = job_root / "media" / "chunk-001" / "audio.mp3"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"\x00" * 64)

    # Tracker payload mirrors what ProgressTracker emits: chunks with
    # start/end but no sentence_count, and a metadata_path present.
    tracker_payload: dict[str, Any] = {
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "range_fragment": "001-010",
                "start_sentence": 1,
                "end_sentence": 11,
                "metadata_path": "metadata/chunk_0001.json",
                # Note: no 'sentence_count' key here
                "files": [
                    {"type": "audio", "path": str(audio_path)},
                ],
            }
        ],
    }

    job.tracker = _TrackerStub(tracker_payload)
    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media")

    payload = response.json()
    assert response.status_code == 200
    assert len(payload["chunks"]) == 1

    chunk = payload["chunks"][0]
    # The critical assertion: sentenceCount must be populated (11 - 1 = 10)
    assert chunk["sentenceCount"] == 10
    assert chunk["startSentence"] == 1
    assert chunk["endSentence"] == 11
    assert payload["diagnostics"] == {
        "mediaFileCount": 1,
        "chunkCount": 1,
        "chunkFileCount": 1,
        "audioFileCount": 1,
        "imageFileCount": 0,
        "chunksWithAudio": 1,
        "chunksWithTiming": 0,
        "chunksWithImages": 0,
        "chunksWithoutFiles": 0,
        "chunksWithoutMetadata": 0,
        "filesWithoutUrl": 0,
        "filesWithoutSize": 0,
    }


def test_get_job_media_live_prefers_tracker_snapshot(api_app) -> None:
    app, file_locator = api_app
    job_id = "job-live"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )

    job_root = file_locator.resolve_path(job_id)
    live_path = job_root / "media" / "chunk-002" / "live.html"
    live_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text("<p>content</p>")

    os.utime(live_path, (live_path.stat().st_mtime, live_path.stat().st_mtime))

    tracker_payload = {
        "files": [
            {
                "type": "html",
                "path": str(live_path),
            }
        ]
    }

    job.tracker = _TrackerStub(tracker_payload)
    job.generated_files = {
        "files": [
            {
                "type": "html",
                "relative_path": "media/stale/live.html",
            }
        ]
    }

    service = _StubPipelineService(job)
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/pipelines/jobs/{job_id}/media/live")

    payload = response.json()

    assert response.status_code == 200
    assert "html" in payload["media"]
    assert "chunks" in payload
    assert isinstance(payload["chunks"], list)
    assert "complete" in payload
    assert payload["diagnostics"]["mediaFileCount"] == 1
    assert payload["diagnostics"]["chunkCount"] == 0
    assert payload["diagnostics"]["filesWithoutUrl"] == 0
    entry = payload["media"]["html"][0]
    assert entry["name"] == "live.html"
    assert entry["source"] == "live"
    assert entry["url"].endswith("media/chunk-002/live.html")
    assert entry["size"] == live_path.stat().st_size
