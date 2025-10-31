from __future__ import annotations

from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Callable

import pytest

from modules.services.job_manager import manager as manager_module
from modules.services.job_manager.job import PipelineJobStatus
from modules.services.job_manager.manager import PipelineJobManager
from modules.services.job_manager.stores import InMemoryJobStore
from modules.services.pipeline_service import PipelineInput, PipelineRequest, PipelineService


class _DummyExecutor:
    def __init__(self, *_, **__):
        self.submitted: list[tuple[Callable[..., object], tuple[object, ...], dict[str, object]]] = []

    def submit(self, fn: Callable[..., object], *args: object, **kwargs: object) -> None:
        self.submitted.append((fn, args, kwargs))
        return None

    def shutdown(self, wait: bool = True) -> None:  # noqa: ARG002 - interface compatibility
        self.submitted.clear()


class _DummyWorkerPool:
    def shutdown(self) -> None:  # pragma: no cover - defensive safeguard
        return None


@pytest.fixture(autouse=True)
def _isolate_job_directories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(manager_module, "_JOB_OUTPUT_ROOT", tmp_path / "storage")


@pytest.fixture(autouse=True)
def _patch_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(manager_module, "ThreadPoolExecutor", _DummyExecutor)


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
            generate_video=False,
            include_transliteration=False,
            tempo=1.0,
            book_metadata={},
        ),
    )
    return dataclass_replace(base)


def test_list_jobs_respects_role_visibility(tmp_path: Path) -> None:
    store = InMemoryJobStore()
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: _DummyWorkerPool(),
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


def test_job_actions_require_authorisation(tmp_path: Path) -> None:
    store = InMemoryJobStore()
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: _DummyWorkerPool(),
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

        with pytest.raises(PermissionError):
            service.delete_job(other_job.job_id, user_id="carol", user_role="viewer")

        deleted = service.delete_job(other_job.job_id, user_id="admin", user_role="admin")
        assert deleted.job_id == other_job.job_id
    finally:
        manager._executor.shutdown()
