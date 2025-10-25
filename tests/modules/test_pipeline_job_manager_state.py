from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import threading
import time

import pytest

from modules.progress_tracker import ProgressEvent, ProgressSnapshot
from modules.services.job_manager import (
    JobStore,
    PipelineJobManager,
    PipelineJobMetadata,
    PipelineJobStatus,
)
from modules.services.pipeline_service import PipelineInput, PipelineRequest, PipelineResponse
import modules.services.job_manager.manager as manager_module


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


def _build_metadata(
    job_id: str,
    status: PipelineJobStatus,
    *,
    user_id: str = "user",
    user_role: str = "user",
) -> PipelineJobMetadata:
    now = datetime.now(timezone.utc)
    inputs = {
        "input_file": "book.epub",
        "sentences_per_output_file": 10,
        "start_sentence": 1,
    }
    return PipelineJobMetadata(
        job_id=job_id,
        status=status,
        created_at=now,
        started_at=now,
        completed_at=None,
        error_message=None,
        last_event=None,
        result=None,
        request_payload={"config": {}, "inputs": dict(inputs)},
        resume_context={"config": {}, "inputs": dict(inputs)},
        user_id=user_id,
        user_role=user_role,
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

    job = manager.get(metadata.job_id)
    job.status = PipelineJobStatus.RUNNING
    job.last_event = ProgressEvent(
        event_type="progress",
        snapshot=ProgressSnapshot(completed=5, total=20, elapsed=1.0, speed=5.0, eta=None),
        timestamp=1.0,
        metadata={"stage": "media", "sentence_number": 12},
    )
    manager._jobs[metadata.job_id] = job

    paused = manager.pause_job(metadata.job_id)
    assert paused.status == PipelineJobStatus.PAUSED
    assert store.get(metadata.job_id).status == PipelineJobStatus.PAUSED
    paused_inputs = paused.resume_context["inputs"]
    assert paused_inputs["start_sentence"] == 11
    assert paused_inputs["resume_block_start"] == 11
    assert paused_inputs["resume_last_sentence"] == 12

    resumed = manager.resume_job(metadata.job_id)
    assert resumed.status == PipelineJobStatus.PENDING
    assert store.get(metadata.job_id).status == PipelineJobStatus.PENDING
    assert resumed.request_payload["inputs"]["start_sentence"] == 11

    cancelled = manager.cancel_job(metadata.job_id)
    assert cancelled.status == PipelineJobStatus.CANCELLED
    stored = store.get(metadata.job_id)
    assert stored.status == PipelineJobStatus.CANCELLED
    assert stored.completed_at is not None


def test_pause_resume_execution_flow(monkeypatch, job_manager_factory):
    store = _InMemoryJobStore()
    manager = job_manager_factory(store)

    request = PipelineRequest(
        config={},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=PipelineInput(
            input_file="book.epub",
            base_output_file="output",
            input_language="en",
            target_languages=["es"],
            sentences_per_output_file=5,
            start_sentence=1,
            end_sentence=None,
            stitch_full=False,
            generate_audio=False,
            audio_mode="narration",
            written_mode="text",
            selected_voice="",
            output_html=True,
            output_pdf=False,
            generate_video=False,
            include_transliteration=False,
            tempo=1.0,
            book_metadata={},
        ),
    )

    first_run_started = threading.Event()
    first_run_released = threading.Event()
    resume_started = threading.Event()
    start_sentences: list[int] = []

    def _fake_run_pipeline(pipeline_request: PipelineRequest) -> PipelineResponse:
        start_sentences.append(pipeline_request.inputs.start_sentence)
        if not first_run_started.is_set():
            first_run_started.set()
            if pipeline_request.stop_event is not None:
                pipeline_request.stop_event.wait(timeout=2.0)
            first_run_released.set()
            return PipelineResponse(success=False)
        resume_started.set()
        return PipelineResponse(success=True)

    monkeypatch.setattr(manager_module, "run_pipeline", _fake_run_pipeline)

    job = manager.submit(request)
    assert first_run_started.wait(1.0)

    progress_event = ProgressEvent(
        event_type="progress",
        snapshot=ProgressSnapshot(
            completed=7,
            total=20,
            elapsed=1.0,
            speed=7.0,
            eta=None,
        ),
        timestamp=1.0,
        metadata={"stage": "rendering", "sentence_number": 7},
    )
    manager._store_event(job.job_id, progress_event)

    previous_event = job.stop_event
    paused = manager.pause_job(job.job_id)
    assert paused.status == PipelineJobStatus.PAUSED
    assert paused.stop_event is not None and paused.stop_event.is_set()
    assert paused.stop_event is previous_event
    assert store.get(job.job_id).status == PipelineJobStatus.PAUSED

    assert first_run_released.wait(1.0)

    for _ in range(50):
        state = manager.get(job.job_id)
        if state.status == PipelineJobStatus.PAUSED:
            assert state.completed_at is None
            break
        time.sleep(0.02)
    else:  # pragma: no cover - defensive guard
        pytest.fail("Job did not enter paused state")

    paused_metadata = store.get(job.job_id)
    paused_inputs = paused_metadata.resume_context["inputs"]
    assert paused_inputs["start_sentence"] == 6
    assert paused_inputs["resume_block_start"] == 6
    assert paused_inputs["resume_last_sentence"] == 7

    resumed = manager.resume_job(job.job_id)
    assert resumed.status == PipelineJobStatus.PENDING
    assert resumed.stop_event is not None and not resumed.stop_event.is_set()
    assert resumed.stop_event is not previous_event
    assert resumed.request.inputs.start_sentence == 6
    assert resume_started.wait(1.0)

    for _ in range(50):
        state = manager.get(job.job_id)
        if state.status == PipelineJobStatus.COMPLETED:
            assert state.completed_at is not None
            break
        time.sleep(0.02)
    else:  # pragma: no cover - defensive guard
        pytest.fail("Resumed job did not complete")

    stored = store.get(job.job_id)
    assert stored.status == PipelineJobStatus.COMPLETED
    assert start_sentences == [1, 6]


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


def test_submit_records_user_context(tmp_path, job_manager_factory):
    store = _InMemoryJobStore()
    manager = job_manager_factory(store)
    manager._executor.submit = lambda *args, **kwargs: None

    request = PipelineRequest(
        config={},
        context=None,
        environment_overrides={
            "working_dir": str(tmp_path / "working"),
            "tmp_dir": str(tmp_path / "tmp"),
            "ebooks_dir": str(tmp_path / "books"),
        },
        pipeline_overrides={},
        inputs=PipelineInput(
            input_file="book.epub",
            base_output_file="output",
            input_language="en",
            target_languages=["es"],
            sentences_per_output_file=5,
            start_sentence=1,
            end_sentence=None,
            stitch_full=False,
            generate_audio=False,
            audio_mode="narration",
            written_mode="text",
            selected_voice="",
            output_html=True,
            output_pdf=False,
            generate_video=False,
            include_transliteration=False,
            tempo=1.0,
            book_metadata={},
        ),
    )

    job = manager.submit(request, user_id="alice", user_role="user")
    expected_dir = Path.cwd() / "data" / "jobs" / "alice" / job.job_id

    assert job.user_id == "alice"
    assert job.user_role == "user"
    assert job.request.context is not None
    assert job.request.context.output_dir == expected_dir
    assert job.request.environment_overrides["output_dir"] == str(expected_dir)
    assert expected_dir.exists()
    assert store.saved and store.saved[0].user_id == "alice"
    assert store.saved[0].user_role == "user"


def test_list_jobs_filters_by_role(job_manager_factory):
    records = {
        "job-admin": _build_metadata(
            "job-admin",
            PipelineJobStatus.PENDING,
            user_id="carol",
            user_role="admin",
        ),
        "job-user": _build_metadata(
            "job-user",
            PipelineJobStatus.PENDING,
            user_id="dave",
            user_role="user",
        ),
    }
    store = _InMemoryJobStore(records)
    manager = job_manager_factory(store)

    admin_visible = manager.list(user_id="carol", user_role="admin")
    assert set(admin_visible) == {"job-admin", "job-user"}

    user_visible = manager.list(user_id="dave", user_role="user")
    assert set(user_visible) == {"job-user"}

    default_visible = manager.list()
    assert set(default_visible) == {"job-admin", "job-user"}
