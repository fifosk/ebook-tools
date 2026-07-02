from __future__ import annotations

from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from modules.services.job_manager import manager as manager_module
from modules.services.job_manager.execution_adapter import PipelineExecutionAdapter
from modules.services.job_manager.job import PipelineJobStatus
from modules.services.job_manager.manager import PipelineJobManager
from modules.services.job_manager.metadata import PipelineJobMetadata
from modules.services.job_manager.stores import InMemoryJobStore
from modules.services.pipeline_service import (
    PipelineInput,
    PipelineRequest,
    PipelineResponse,
    PipelineService,
)

from .conftest import DummyExecutor, DummyWorkerPool

pytestmark = pytest.mark.services


class _RecordingInMemoryJobStore(InMemoryJobStore):
    def __init__(self) -> None:
        super().__init__()
        self.list_calls: list[dict[str, int | None]] = []

    def list(self, *, offset=None, limit=None):
        self.list_calls.append({"offset": offset, "limit": limit})
        return super().list(offset=offset, limit=limit)


@pytest.fixture(autouse=True)
def _isolate_job_directories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if hasattr(manager_module, "_JOB_OUTPUT_ROOT"):
        monkeypatch.setattr(manager_module, "_JOB_OUTPUT_ROOT", tmp_path / "storage")


@pytest.fixture(autouse=True)
def _patch_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(manager_module, "ThreadPoolExecutor", DummyExecutor)


@pytest.fixture(autouse=True)
def _skip_submission_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(PipelineService, "_prepare_submission_metadata", lambda *_, **__: None)
    monkeypatch.setattr(PipelineService, "_persist_initial_metadata", lambda *_, **__: None)


def _build_request() -> PipelineRequest:
    base = PipelineRequest(
        config={"auto_metadata": False},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=PipelineInput(
            input_file="book.epub",
            base_output_file="output",
            input_language="en",
            target_languages=["en"],
            sentences_per_output_file=10,
            start_sentence=0,
            end_sentence=None,
            stitch_full=False,
            generate_audio=False,
            audio_mode="none",
            written_mode="text",
            selected_voice="",
            output_html=False,
            output_pdf=False,
            add_images=False,
            include_transliteration=False,
            tempo=1.0,
        ),
    )
    return dataclass_replace(base)


def test_list_jobs_respects_role_visibility(tmp_path: Path) -> None:
    store = InMemoryJobStore()
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )
    service = PipelineService(manager)

    admin_job = service.enqueue(_build_request(), user_id="admin", user_role="admin")
    alice_job = service.enqueue(_build_request(), user_id="alice", user_role="editor")
    bob_job = service.enqueue(_build_request(), user_id="bob", user_role="viewer")

    try:
        admin_jobs = service.list_jobs(user_id="admin", user_role="admin")
        assert set(admin_jobs.keys()) == {admin_job.job_id, alice_job.job_id, bob_job.job_id}

        alice_jobs = service.list_jobs(user_id="alice", user_role="editor")
        assert set(alice_jobs.keys()) == {alice_job.job_id}

        stranger_jobs = service.list_jobs(user_id="carol", user_role="viewer")
        assert stranger_jobs == {}

        stored = store.list()
        assert stored[alice_job.job_id].user_id == "alice"
        assert stored[alice_job.job_id].user_role == "editor"
    finally:
        manager._executor.shutdown()


def test_admin_list_jobs_paginates_active_job_snapshot(tmp_path: Path) -> None:
    store = InMemoryJobStore()
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )
    service = PipelineService(manager)

    first_job = service.enqueue(_build_request(), user_id="admin", user_role="admin")
    second_job = service.enqueue(_build_request(), user_id="alice", user_role="editor")
    third_job = service.enqueue(_build_request(), user_id="bob", user_role="viewer")

    try:
        paged_jobs = service.list_jobs(
            user_id="admin",
            user_role="admin",
            offset=1,
            limit=1,
        )

        assert service.count_jobs(user_id="admin", user_role="admin") == 3
        assert list(paged_jobs.keys()) == [second_job.job_id]
        assert first_job.job_id not in paged_jobs
        assert third_job.job_id not in paged_jobs
    finally:
        manager._executor.shutdown()


def test_admin_list_jobs_sorts_visible_metadata_before_pagination(tmp_path: Path) -> None:
    store = _RecordingInMemoryJobStore()
    for index in range(3):
        store.save(
            PipelineJobMetadata(
                job_id=f"stored-{index}",
                job_type="pipeline",
                status=PipelineJobStatus.COMPLETED,
                created_at=datetime(2026, 6, 22, 10, index, tzinfo=timezone.utc),
                user_id=f"user-{index}",
                user_role="editor",
            )
        )
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )
    service = PipelineService(manager)
    store.list_calls.clear()

    try:
        paged_jobs = service.list_jobs(
            user_id="admin",
            user_role="admin",
            offset=1,
            limit=1,
        )

        assert store.list_calls == [{"offset": None, "limit": None}]
        assert list(paged_jobs.keys()) == ["stored-1"]
    finally:
        manager._executor.shutdown()


def test_non_admin_count_jobs_does_not_hydrate_stored_jobs(tmp_path: Path) -> None:
    store = _RecordingInMemoryJobStore()
    for index in range(3):
        store.save(
            PipelineJobMetadata(
                job_id=f"alice-stored-{index}",
                job_type="pipeline",
                status=PipelineJobStatus.COMPLETED,
                created_at=datetime(2026, 6, 22, 10, index, tzinfo=timezone.utc),
                user_id="alice",
                user_role="editor",
            )
        )
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )
    service = PipelineService(manager)
    build_calls: list[PipelineJobMetadata] = []
    original_build_job = manager._persistence.build_job

    def recording_build_job(metadata: PipelineJobMetadata):
        build_calls.append(metadata)
        return original_build_job(metadata)

    manager._persistence.build_job = recording_build_job
    store.list_calls.clear()

    try:
        assert service.count_jobs(user_id="alice", user_role="editor") == 3
    finally:
        manager._executor.shutdown()

    assert store.list_calls == [{"offset": None, "limit": None}]
    assert build_calls == []


def test_non_admin_list_jobs_hydrates_only_requested_visible_page(tmp_path: Path) -> None:
    store = _RecordingInMemoryJobStore()
    for index in range(3):
        store.save(
            PipelineJobMetadata(
                job_id=f"alice-stored-{index}",
                job_type="pipeline",
                status=PipelineJobStatus.COMPLETED,
                created_at=datetime(2026, 6, 22, 10, index, tzinfo=timezone.utc),
                user_id="alice",
                user_role="editor",
            )
        )
    store.save(
        PipelineJobMetadata(
            job_id="bob-hidden",
            job_type="pipeline",
            status=PipelineJobStatus.COMPLETED,
            created_at=datetime(2026, 6, 22, 11, 0, tzinfo=timezone.utc),
            user_id="bob",
            user_role="editor",
        )
    )
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )
    service = PipelineService(manager)
    build_calls: list[PipelineJobMetadata] = []
    original_build_job = manager._persistence.build_job

    def recording_build_job(metadata: PipelineJobMetadata):
        build_calls.append(metadata)
        return original_build_job(metadata)

    manager._persistence.build_job = recording_build_job
    store.list_calls.clear()

    try:
        paged_jobs = service.list_jobs(
            user_id="alice",
            user_role="editor",
            offset=1,
            limit=1,
        )
    finally:
        manager._executor.shutdown()

    assert store.list_calls == [{"offset": None, "limit": None}]
    assert list(paged_jobs.keys()) == ["alice-stored-1"]
    assert [metadata.job_id for metadata in build_calls] == ["alice-stored-1"]


def test_list_metadata_filters_job_type_without_hydrating_stored_jobs(tmp_path: Path) -> None:
    store = _RecordingInMemoryJobStore()
    youtube_metadata = PipelineJobMetadata(
        job_id="youtube-job",
        job_type="youtube_dub",
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
        request_payload={"video_path": "/nas/video-a.mp4"},
        user_id="alice",
        user_role="editor",
    )
    store.save(youtube_metadata)
    store.save(
        PipelineJobMetadata(
            job_id="pipeline-job",
            job_type="pipeline",
            status=PipelineJobStatus.COMPLETED,
            created_at=datetime(2026, 6, 22, 10, 1, tzinfo=timezone.utc),
            request_payload={"input_file": "book.epub"},
            user_id="alice",
            user_role="editor",
        )
    )
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )
    build_calls: list[PipelineJobMetadata] = []
    original_build_job = manager._persistence.build_job

    def recording_build_job(metadata: PipelineJobMetadata):
        build_calls.append(metadata)
        return original_build_job(metadata)

    manager._persistence.build_job = recording_build_job
    store.list_calls.clear()

    try:
        visible = manager.list_metadata(
            user_id="alice",
            user_role="editor",
            job_type="youtube_dub",
        )
    finally:
        manager._executor.shutdown()

    assert store.list_calls == [{"offset": None, "limit": None}]
    assert build_calls == []
    assert list(visible) == ["youtube-job"]
    assert visible["youtube-job"].request_payload == {"video_path": "/nas/video-a.mp4"}


def test_list_metadata_respects_role_visibility(tmp_path: Path) -> None:
    store = InMemoryJobStore()
    for owner in ["alice", "bob"]:
        store.save(
            PipelineJobMetadata(
                job_id=f"{owner}-youtube-job",
                job_type="youtube_dub",
                status=PipelineJobStatus.COMPLETED,
                created_at=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
                request_payload={"video_path": f"/nas/{owner}.mp4"},
                user_id=owner,
                user_role="editor",
            )
        )
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )

    try:
        alice_visible = manager.list_metadata(
            user_id="alice",
            user_role="editor",
            job_type="youtube_dub",
        )
        admin_visible = manager.list_metadata(
            user_id="admin",
            user_role="admin",
            job_type="youtube_dub",
        )
    finally:
        manager._executor.shutdown()

    assert set(alice_visible) == {"alice-youtube-job"}
    assert set(admin_visible) == {"alice-youtube-job", "bob-youtube-job"}


def test_executor_runs_owned_jobs(tmp_path: Path) -> None:
    store = InMemoryJobStore()
    execution_adapter = PipelineExecutionAdapter(lambda _: PipelineResponse(success=True))
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
        execution_adapter=execution_adapter,
    )
    service = PipelineService(manager)

    try:
        job = service.enqueue(_build_request(), user_id="alice", user_role="editor")
        manager._job_executor.execute(job.job_id)
        updated = manager.get(job.job_id, user_id="alice", user_role="editor")
        assert updated.status == PipelineJobStatus.COMPLETED
    finally:
        manager._executor.shutdown()

def test_job_actions_require_authorisation(tmp_path: Path) -> None:
    store = InMemoryJobStore()
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: DummyWorkerPool(),
    )
    service = PipelineService(manager)

    try:
        job = service.enqueue(_build_request(), user_id="alice", user_role="editor")
        job.status = PipelineJobStatus.RUNNING
        manager._jobs[job.job_id] = job

        with pytest.raises(PermissionError):
            service.pause_job(job.job_id, user_id="bob", user_role="viewer")

        paused = service.pause_job(job.job_id, user_id="admin", user_role="admin")
        assert paused.status == PipelineJobStatus.PAUSING

        other_job = service.enqueue(_build_request(), user_id="alice", user_role="editor")
        # Cancel the job first -- only terminal jobs can be deleted.
        service.cancel_job(other_job.job_id, user_id="alice", user_role="editor")

        with pytest.raises(PermissionError):
            service.delete_job(other_job.job_id, user_id="carol", user_role="viewer")

        deleted = service.delete_job(other_job.job_id, user_id="admin", user_role="admin")
        assert deleted.job_id == other_job.job_id
    finally:
        manager._executor.shutdown()
