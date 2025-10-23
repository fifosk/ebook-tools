from __future__ import annotations

from datetime import datetime, timezone

import pytest

from modules.services.job_manager import (
    JobStore,
    PipelineJobManager,
    PipelineJobMetadata,
    PipelineJobStatus,
)


class _InMemoryJobStore(JobStore):
    """Simple :class:`JobStore` implementation used for persistence tests."""

    def __init__(self, records: dict[str, PipelineJobMetadata] | None = None) -> None:
        self._records: dict[str, PipelineJobMetadata] = dict(records or {})
        self.saved: list[PipelineJobMetadata] = []
        self.updated: list[PipelineJobMetadata] = []

    def save(self, metadata: PipelineJobMetadata) -> None:
        self._records[metadata.job_id] = metadata
        self.saved.append(metadata)

    def update(self, metadata: PipelineJobMetadata) -> None:
        self._records[metadata.job_id] = metadata
        self.updated.append(metadata)

    def get(self, job_id: str) -> PipelineJobMetadata:
        try:
            metadata = self._records[job_id]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(job_id) from exc
        return PipelineJobMetadata.from_dict(metadata.to_dict())

    def list(self) -> dict[str, PipelineJobMetadata]:
        return {
            job_id: PipelineJobMetadata.from_dict(metadata.to_dict())
            for job_id, metadata in self._records.items()
        }


def _build_metadata(job_id: str, status: PipelineJobStatus) -> PipelineJobMetadata:
    now = datetime.now(timezone.utc)
    return PipelineJobMetadata(
        job_id=job_id,
        status=status,
        created_at=now,
        started_at=now,
        completed_at=None,
        error_message=None,
        last_event=None,
        result=None,
        request_payload={"config": {}, "inputs": {"input_file": "book.epub"}},
        resume_context={"config": {}, "inputs": {"input_file": "book.epub"}},
    )


@pytest.fixture
def job_manager_factory():
    managers: list[PipelineJobManager] = []

    def factory(store: JobStore) -> PipelineJobManager:
        manager = PipelineJobManager(max_workers=1, store=store)
        managers.append(manager)
        return manager

    yield factory

    for manager in managers:
        manager._executor.shutdown(wait=False)


def test_restore_pauses_inflight_jobs(job_manager_factory):
    metadata = _build_metadata("job-restore", PipelineJobStatus.RUNNING)
    store = _InMemoryJobStore({metadata.job_id: metadata})

    manager = job_manager_factory(store)

    restored = store.get(metadata.job_id)
    assert restored.status == PipelineJobStatus.PAUSED

    job = manager.get(metadata.job_id)
    assert job.status == PipelineJobStatus.PAUSED


def test_pause_resume_and_cancel_persist_updates(job_manager_factory):
    metadata = _build_metadata("job-control", PipelineJobStatus.PENDING)
    store = _InMemoryJobStore({metadata.job_id: metadata})

    manager = job_manager_factory(store)

    paused = manager.pause_job(metadata.job_id)
    assert paused.status == PipelineJobStatus.PAUSED
    assert store.get(metadata.job_id).status == PipelineJobStatus.PAUSED

    resumed = manager.resume_job(metadata.job_id)
    assert resumed.status == PipelineJobStatus.PENDING
    assert store.get(metadata.job_id).status == PipelineJobStatus.PENDING

    cancelled = manager.cancel_job(metadata.job_id)
    assert cancelled.status == PipelineJobStatus.CANCELLED
    stored = store.get(metadata.job_id)
    assert stored.status == PipelineJobStatus.CANCELLED
    assert stored.completed_at is not None


def test_finish_job_persists_terminal_state(job_manager_factory):
    metadata = _build_metadata("job-finish", PipelineJobStatus.PENDING)
    store = _InMemoryJobStore({metadata.job_id: metadata})

    manager = job_manager_factory(store)

    result_payload = {"success": True}
    finished = manager.finish_job(
        metadata.job_id,
        status=PipelineJobStatus.COMPLETED,
        result_payload=result_payload,
    )

    assert finished.status == PipelineJobStatus.COMPLETED
    stored = store.get(metadata.job_id)
    assert stored.status == PipelineJobStatus.COMPLETED
    assert stored.completed_at is not None
    assert stored.result == result_payload
