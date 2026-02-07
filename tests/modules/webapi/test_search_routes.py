from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from modules.library import LibraryService
from modules.services.file_locator import FileLocator
from modules.webapi import dependencies
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_file_locator,
    get_library_service,
    get_library_sync,
    get_pipeline_service,
)
from modules.services.job_manager import PipelineJob, PipelineJobStatus


class _StubPipelineService:
    def __init__(self, jobs: Iterable[PipelineJob]) -> None:
        self._jobs = {job.job_id: job for job in jobs}

    def get_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:  # pragma: no cover - mirrors real behaviour
            raise exc


class _StubLibrarySync:
    def get_item(self, job_id: str):
        return None

    def serialize_item(self, entry):
        return {}

    def search(self, **_kwargs):
        return SimpleNamespace(total=0, page=1, limit=0, view='flat', items=[], groups=None)


class _StubLibraryService:
    def __init__(self) -> None:
        self.sync = _StubLibrarySync()

    def refresh_metadata(self, entry_id: str):
        raise NotImplementedError

    def rebuild_index(self) -> int:
        return 0

    def get_library_overview(self):
        return None

    def import_book(self, source_path):
        raise NotImplementedError

    def export_entry(self, entry_id, *, destination=None):
        raise NotImplementedError


@pytest.fixture()
def api_app(tmp_path):
    app = create_app()
    file_locator = FileLocator(storage_dir=tmp_path, base_url="https://example.invalid/jobs")

    dependencies.get_library_service.cache_clear()
    dependencies.get_library_sync.cache_clear()
    dependencies.get_library_repository.cache_clear()

    app.dependency_overrides[get_file_locator] = lambda: file_locator
    yield app, file_locator
    app.dependency_overrides.clear()


def test_search_returns_matching_snippet(api_app) -> None:
    app, file_locator = api_app
    job_id = "search-job"
    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    job.resume_context = {
        "inputs": {
            "base_output_file": "/storage/ebooks/Example Book.epub",
        }
    }

    job_root = file_locator.resolve_path(job_id)
    text_dir = job_root / "media" / "chunk-001"
    text_dir.mkdir(parents=True, exist_ok=True)

    html_path = text_dir / "sample.html"
    html_path.write_text(
        "<html><body><p>The quick brown fox discovers a fortune cookie on the table.</p></body></html>",
        encoding="utf-8",
    )

    audio_path = text_dir / "sample.mp3"
    audio_path.write_bytes(b"\x00\x01")

    video_path = text_dir / "sample.mp4"
    video_path.write_bytes(b"\x00\x01\x02")

    generated_files = {
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "range_fragment": "0001-0010",
                "start_sentence": 1,
                "end_sentence": 10,
                "files": [
                    {
                        "type": "html",
                        "relative_path": "media/chunk-001/sample.html",
                        "path": str(html_path),
                    },
                    {
                        "type": "audio",
                        "relative_path": "media/chunk-001/sample.mp3",
                        "path": str(audio_path),
                    },
                    {
                        "type": "video",
                        "relative_path": "media/chunk-001/sample.mp4",
                        "path": str(video_path),
                    },
                ],
            }
        ]
    }
    job.generated_files = generated_files

    # Write metadata/job.json so MetadataLoader can find it
    metadata_dir = job_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    job_metadata = {
        "job_id": job_id,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "generated_files": generated_files,
        "resume_context": job.resume_context,
    }
    (metadata_dir / "job.json").write_text(json.dumps(job_metadata), encoding="utf-8")

    service = _StubPipelineService([job])
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync()
    app.dependency_overrides[get_library_service] = lambda: _StubLibraryService()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/pipelines/search",
            params={"query": "fortune", "job_id": job_id},
        )

    app.dependency_overrides.pop(get_pipeline_service, None)
    app.dependency_overrides.pop(get_library_sync, None)
    app.dependency_overrides.pop(get_library_service, None)
    app.dependency_overrides.pop(get_library_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["query"] == "fortune"
    assert payload["count"] == 1
    assert payload["limit"] == 20

    result = payload["results"][0]
    assert result["job_id"] == job_id
    assert result["job_label"] == "Example Book"
    assert result["base_id"] == "sample"
    assert result["match_start"] == 32
    assert result["match_end"] == 39
    assert result["text_length"] == 60
    assert result["offset_ratio"] == pytest.approx(32 / 60, rel=1e-3)
    assert result["approximate_time_seconds"] == pytest.approx((60 / 15.0) * (32 / 60), rel=1e-3)
    assert "fortune cookie" in result["snippet"].lower()

    media = result["media"]
    assert "text" in media
    text_entry = media["text"][0]
    assert text_entry["relative_path"] == "chunk-001/sample.html"
    assert text_entry["source"] == "completed"
    assert text_entry["url"].endswith("chunk-001/sample.html")

    assert "audio" in media
    audio_entry = media["audio"][0]
    assert audio_entry["relative_path"] == "chunk-001/sample.mp3"

    assert "video" in media
    video_entry = media["video"][0]
    assert video_entry["relative_path"] == "chunk-001/sample.mp4"


def test_search_returns_404_for_unknown_job(api_app) -> None:
    app, file_locator = api_app
    file_locator  # unused but keeps fixture pattern consistent
    service = _StubPipelineService([])
    app.dependency_overrides[get_pipeline_service] = lambda: service
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync()
    app.dependency_overrides[get_library_service] = lambda: _StubLibraryService()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/pipelines/search",
            params={"query": "fortune", "job_id": "missing-job"},
        )

    app.dependency_overrides.pop(get_pipeline_service, None)
    app.dependency_overrides.pop(get_library_sync, None)
    app.dependency_overrides.pop(get_library_service, None)
    assert response.status_code == 404, response.text
    assert response.json() == {"detail": "Job not found"}


def test_search_uses_library_metadata_when_pipeline_job_missing(api_app, tmp_path) -> None:
    app, file_locator = api_app
    library_root = tmp_path / "library"
    library_service = LibraryService(
        library_root=library_root,
        file_locator=file_locator,
    )
    library_sync = library_service.sync

    job_id = "library-only-job"
    queue_root = file_locator.resolve_path(job_id)
    media_root = queue_root / "media" / "chunk-001"
    media_root.mkdir(parents=True, exist_ok=True)
    metadata_dir = queue_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    html_path = media_root / "sample.html"
    html_path.write_text(
        "<html><body><p>A hidden fortune awaits those who seek knowledge.</p></body></html>",
        encoding="utf-8",
    )
    audio_path = media_root / "sample.mp3"
    audio_path.write_bytes(b"\x00\x01")
    video_path = media_root / "sample.mp4"
    video_path.write_bytes(b"\x00\x01\x02")

    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "job_id": job_id,
        "author": "Library Author",
        "book_title": "Library Fortune",
        "language": "en",
        "status": "finished",
        "created_at": now,
        "updated_at": now,
        "generated_files": {
            "chunks": [
                {
                    "chunk_id": "chunk-001",
                    "range_fragment": "0001-0010",
                    "start_sentence": 1,
                    "end_sentence": 5,
                    "files": [
                        {
                            "type": "html",
                            "relative_path": "media/chunk-001/sample.html",
                            "path": str(html_path),
                            "source": "completed",
                        },
                        {
                            "type": "audio",
                            "relative_path": "media/chunk-001/sample.mp3",
                            "path": str(audio_path),
                            "source": "completed",
                        },
                        {
                            "type": "video",
                            "relative_path": "media/chunk-001/sample.mp4",
                            "path": str(video_path),
                            "source": "completed",
                        },
                    ],
                }
            ]
        },
    }

    metadata_path = metadata_dir / "job.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    library_sync.move_to_library(job_id, status_override="finished")

    dependencies.get_library_service.cache_clear()
    dependencies.get_library_sync.cache_clear()
    dependencies.get_pipeline_service.cache_clear()
    app.dependency_overrides[get_library_service] = lambda: library_service
    app.dependency_overrides[get_library_sync] = lambda: library_sync
    app.dependency_overrides[get_pipeline_service] = lambda: _StubPipelineService([])

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/pipelines/search",
            params={"query": "fortune", "job_id": job_id},
        )

    app.dependency_overrides.pop(get_library_service, None)
    app.dependency_overrides.pop(get_library_sync, None)
    app.dependency_overrides.pop(get_pipeline_service, None)
    dependencies.get_library_service.cache_clear()
    dependencies.get_library_sync.cache_clear()
    dependencies.get_pipeline_service.cache_clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] == 1
    result = payload["results"][0]
    assert result["job_id"] == job_id
    assert result["job_label"] == "Library Fortune"
    assert result["source"] == "library"
    assert "fortune" in result["snippet"].lower()

    media = result.get("media", {})
    assert isinstance(media, dict)


def test_search_recovers_library_entry_when_index_missing(api_app, tmp_path) -> None:
    app, file_locator = api_app
    library_root = tmp_path / "library"
    library_service = LibraryService(
        library_root=library_root,
        file_locator=file_locator,
    )
    library_sync = library_service.sync

    job_id = "library-missing-index"
    queue_root = file_locator.resolve_path(job_id)
    media_root = queue_root / "media" / "chunk-001"
    media_root.mkdir(parents=True, exist_ok=True)
    metadata_dir = queue_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    html_path = media_root / "sample.html"
    html_path.write_text(
        "<html><body><p>A hidden treasure reveals itself to the curious mind.</p></body></html>",
        encoding="utf-8",
    )

    metadata_payload = {
        "job_id": job_id,
        "author": "Offline Author",
        "book_title": "Recovered Treasure",
        "language": "en",
        "status": "finished",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "generated_files": {
            "chunks": [
                {
                    "chunk_id": "chunk-001",
                    "range_fragment": "0001-0010",
                    "start_sentence": 1,
                    "end_sentence": 3,
                    "files": [
                        {
                            "type": "html",
                            "relative_path": "media/chunk-001/sample.html",
                            "path": str(html_path),
                            "source": "completed",
                        }
                    ],
                }
            ]
        },
    }
    (metadata_dir / "job.json").write_text(json.dumps(metadata_payload), encoding="utf-8")

    library_sync.move_to_library(job_id, status_override="finished")
    library_sync._repository.delete_entry(job_id)
    library_sync._library_job_cache.pop(job_id, None)

    dependencies.get_library_service.cache_clear()
    dependencies.get_library_sync.cache_clear()
    dependencies.get_pipeline_service.cache_clear()
    app.dependency_overrides[get_library_service] = lambda: library_service
    app.dependency_overrides[get_library_sync] = lambda: library_sync
    app.dependency_overrides[get_pipeline_service] = lambda: _StubPipelineService([])

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/pipelines/search",
            params={"query": "treasure", "job_id": job_id},
        )

    app.dependency_overrides.pop(get_library_service, None)
    app.dependency_overrides.pop(get_library_sync, None)
    app.dependency_overrides.pop(get_pipeline_service, None)
    dependencies.get_library_service.cache_clear()
    dependencies.get_library_sync.cache_clear()
    dependencies.get_pipeline_service.cache_clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] == 1
    result = payload["results"][0]
    assert result["job_id"] == job_id
    assert result["job_label"] == "Recovered Treasure"
    assert "treasure" in result["snippet"].lower()
