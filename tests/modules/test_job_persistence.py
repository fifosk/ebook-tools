from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from modules.jobs import persistence
from modules.services.job_manager import PipelineJobMetadata, PipelineJobStatus


@pytest.fixture(autouse=True)
def _isolate_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_STORAGE_DIR", str(tmp_path))
    yield


def _build_metadata(job_id: str) -> PipelineJobMetadata:
    now = datetime.now(timezone.utc)
    return PipelineJobMetadata(
        job_id=job_id,
        status=PipelineJobStatus.PENDING,
        created_at=now,
        started_at=now,
        completed_at=None,
        error_message=None,
        last_event={
            "event_type": "progress",
            "timestamp": 123.456,
            "metadata": {"stage": "ingestion", "b": 2, "a": 1},
            "error": None,
            "snapshot": {
                "completed": 2,
                "total": 10,
                "elapsed": 1.23,
                "speed": 1.5,
                "eta": 5.4,
            },
        },
        result={"b": 2, "a": 1},
        request_payload={
            "config": {"z": 1, "a": 2},
            "inputs": {
                "input_file": "book.epub",
                "target_languages": ["ar", "en"],
                "book_metadata": {"title": "Example", "author": "Tester"},
            },
        },
        resume_context={"resume": True, "order": ["second", "first"]},
    )


def test_save_and_load_job_roundtrip():
    metadata = _build_metadata("job-1")
    path = persistence.save_job(metadata)
    raw = path.read_text(encoding="utf-8")
    assert "\"resume_context\"" in raw
    assert raw == metadata.to_json()

    # Writing the same payload again should not change the stored representation.
    persistence.save_job(metadata)
    assert path.read_text(encoding="utf-8") == raw

    loaded = persistence.load_job(metadata.job_id)
    assert loaded == metadata


def test_load_all_jobs_returns_all():
    first = _build_metadata("job-a")
    second = _build_metadata("job-b")
    persistence.save_job(first)
    persistence.save_job(second)

    loaded = persistence.load_all_jobs()
    assert set(loaded) == {"job-a", "job-b"}
    assert loaded["job-a"] == first
    assert loaded["job-b"] == second


def test_delete_job_removes_file():
    metadata = _build_metadata("job-delete")
    path = persistence.save_job(metadata)
    assert path.exists()

    persistence.delete_job(metadata.job_id)
    assert not path.exists()
    assert metadata.job_id not in persistence.load_all_jobs()


def test_save_job_accepts_mapping():
    metadata = _build_metadata("job-mapping")
    payload = metadata.to_dict()

    persistence.save_job(payload)
    raw = persistence.load_job("job-mapping")
    assert raw.job_id == "job-mapping"
    assert json.loads(raw.to_json()) == json.loads(metadata.to_json())

