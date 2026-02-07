from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
STUB_DIR = ROOT_DIR / "tests" / "stubs"

sys.path.insert(0, str(STUB_DIR))
sys.path.insert(0, str(ROOT_DIR))

from tests.helpers.job_manager_stubs import install_job_manager_stubs

install_job_manager_stubs()

import pytest

persistence = import_module("modules.jobs.persistence")
job_manager_module = import_module("modules.services.job_manager")
PipelineJobMetadata = job_manager_module.PipelineJobMetadata
PipelineJobStatus = job_manager_module.PipelineJobStatus


@pytest.fixture
def storage_dir(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "storage"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(path))
    # Ensure load_all_jobs only sees the temp directory, not project storage/
    monkeypatch.setattr(persistence, "_candidate_storage_dirs", lambda: [path])
    return path


def _build_metadata(job_id: str) -> PipelineJobMetadata:
    now = datetime.now(timezone.utc)
    return PipelineJobMetadata(
        job_id=job_id,
        job_type="pipeline",
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
                "media_metadata": {"title": "Example", "author": "Tester"},
            },
        },
        resume_context={"resume": True, "order": ["second", "first"]},
        user_id="test-user",
        user_role="user",
    )


def test_save_and_load_job_roundtrip(storage_dir: Path):
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
    assert loaded.user_id == metadata.user_id
    assert loaded.user_role == metadata.user_role


def test_load_all_jobs_returns_all(storage_dir: Path):
    first = _build_metadata("job-a")
    second = _build_metadata("job-b")
    persistence.save_job(first)
    persistence.save_job(second)

    loaded = persistence.load_all_jobs()
    assert set(loaded) == {"job-a", "job-b"}
    assert loaded["job-a"] == first
    assert loaded["job-b"] == second
    assert loaded["job-a"].user_id == first.user_id


def test_delete_job_removes_file(storage_dir: Path):
    metadata = _build_metadata("job-delete")
    path = persistence.save_job(metadata)
    assert path.exists()

    persistence.delete_job(metadata.job_id)
    assert not path.exists()
    job_root = persistence._job_root(metadata.job_id)
    assert not job_root.exists()
    assert metadata.job_id not in persistence.load_all_jobs()


def test_save_job_accepts_mapping(storage_dir: Path):
    metadata = _build_metadata("job-mapping")
    payload = metadata.to_dict()

    persistence.save_job(payload)
    raw = persistence.load_job("job-mapping")
    assert raw.job_id == "job-mapping"
    assert json.loads(raw.to_json()) == json.loads(metadata.to_json())
    assert raw.user_id == metadata.user_id


def test_save_job_rejects_unknown_payload_type(storage_dir: Path):
    with pytest.raises(TypeError):
        persistence.save_job(object())


def test_save_job_cleans_up_temporary_files_on_failure(storage_dir: Path, monkeypatch):
    metadata = _build_metadata("job-failure")

    def _fake_replace(src: Path | str, dst: Path | str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(persistence.os, "replace", _fake_replace)

    with pytest.raises(RuntimeError):
        persistence.save_job(metadata)

    assert list(storage_dir.rglob("*.json")) == []


def test_save_job_sanitizes_filename(storage_dir: Path):
    metadata = _build_metadata("job/with*unsafe?chars")
    path = persistence.save_job(metadata)

    assert path.parent == storage_dir / "job_with_unsafe_chars" / "metadata"
    assert path.name == "job.json"
    loaded = persistence.load_job(metadata.job_id)
    assert loaded.job_id == metadata.job_id
