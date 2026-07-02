from __future__ import annotations

from datetime import datetime, timezone

import pytest

from modules.services.job_manager.job import PipelineJobStatus
from modules.services.job_manager.metadata import PipelineJobMetadata
from modules.services.job_manager.stores import BatchingJobStore, InMemoryJobStore

pytestmark = pytest.mark.services


class _RecordingInMemoryJobStore(InMemoryJobStore):
    def __init__(self) -> None:
        super().__init__()
        self.count_calls = 0
        self.list_ids_calls = 0

    def count(self) -> int:
        self.count_calls += 1
        return super().count()

    def list_ids(self) -> list[str]:
        self.list_ids_calls += 1
        return super().list_ids()


def _metadata(job_id: str) -> PipelineJobMetadata:
    return PipelineJobMetadata(
        job_id=job_id,
        job_type="pipeline",
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )


def test_batching_job_store_count_scans_underlying_ids_once_for_buffered_jobs() -> None:
    store = _RecordingInMemoryJobStore()
    store.save(_metadata("persisted"))
    batching = BatchingJobStore(store, max_buffer_size=100, flush_interval_seconds=60)

    try:
        batching.save(_metadata("persisted"))
        batching.save(_metadata("buffered-a"))
        batching.save(_metadata("buffered-b"))

        assert batching.count() == 3
    finally:
        batching.close()

    assert store.count_calls == 1
    assert store.list_ids_calls == 1


def test_batching_job_store_count_skips_id_scan_when_buffer_is_empty() -> None:
    store = _RecordingInMemoryJobStore()
    store.save(_metadata("persisted"))
    batching = BatchingJobStore(store, max_buffer_size=100, flush_interval_seconds=60)

    try:
        assert batching.count() == 1
    finally:
        batching.close()

    assert store.count_calls == 1
    assert store.list_ids_calls == 0


def test_batching_job_store_list_ids_preserves_underlying_order_then_buffer_order() -> None:
    store = _RecordingInMemoryJobStore()
    store.save(_metadata("persisted-a"))
    store.save(_metadata("persisted-b"))
    batching = BatchingJobStore(store, max_buffer_size=100, flush_interval_seconds=60)

    try:
        batching.save(_metadata("buffered-a"))
        batching.save(_metadata("persisted-a"))
        batching.save(_metadata("buffered-b"))

        assert batching.list_ids() == [
            "persisted-a",
            "persisted-b",
            "buffered-a",
            "buffered-b",
        ]
    finally:
        batching.close()
