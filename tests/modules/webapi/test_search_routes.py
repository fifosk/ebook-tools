from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

import pytest
from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_file_locator, get_pipeline_service
from modules.webapi.jobs import PipelineJob, PipelineJobStatus


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


@pytest.fixture()
def api_app(tmp_path):
    app = create_app()
    file_locator = FileLocator(storage_dir=tmp_path, base_url="https://example.invalid/jobs")

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
            "base_output_file": "/books/Example Book.epub",
        }
    }

    job_root = file_locator.resolve_path(job_id)
    text_dir = job_root / "chunk-001"
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

    job.generated_files = {
        "chunks": [
            {
                "chunk_id": "chunk-001",
                "range_fragment": "0001-0010",
                "start_sentence": 1,
                "end_sentence": 10,
                "files": [
                    {
                        "type": "html",
                        "relative_path": "chunk-001/sample.html",
                        "path": str(html_path),
                    },
                    {
                        "type": "audio",
                        "relative_path": "chunk-001/sample.mp3",
                        "path": str(audio_path),
                    },
                    {
                        "type": "video",
                        "relative_path": "chunk-001/sample.mp4",
                        "path": str(video_path),
                    },
                ],
            }
        ]
    }

    service = _StubPipelineService([job])
    app.dependency_overrides[get_pipeline_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/pipelines/search",
            params={"query": "fortune", "job_id": job_id},
        )

    app.dependency_overrides.pop(get_pipeline_service, None)

    assert response.status_code == 200
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

    with TestClient(app) as client:
        response = client.get(
            "/pipelines/search",
            params={"query": "fortune", "job_id": "missing-job"},
        )

    app.dependency_overrides.pop(get_pipeline_service, None)
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
