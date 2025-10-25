from __future__ import annotations

from datetime import datetime, timezone
import sys
from importlib import import_module
from pathlib import Path
from typing import Callable

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
STUB_DIR = ROOT_DIR / "tests" / "stubs"

sys.path.insert(0, str(STUB_DIR))
sys.path.insert(0, str(ROOT_DIR))

from tests.helpers.job_manager_stubs import install_job_manager_stubs

install_job_manager_stubs()

persistence = import_module("modules.jobs.persistence")
job_manager_module = import_module("modules.services.job_manager")
pipeline_service = import_module("modules.services.pipeline_service")
FileJobStore = job_manager_module.FileJobStore
PipelineJobManager = job_manager_module.PipelineJobManager
PipelineJobStatus = job_manager_module.PipelineJobStatus
job_manager = job_manager_module


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
        pass


@pytest.fixture
def storage_dir(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "jobs"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(path))
    return path


@pytest.fixture(autouse=True)
def _patch_executor(monkeypatch):
    monkeypatch.setattr(job_manager, "ThreadPoolExecutor", _DummyExecutor)


def _build_request() -> pipeline_service.PipelineRequest:
    return pipeline_service.PipelineRequest(
        config={"auto_metadata": False},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=pipeline_service.PipelineInput(
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


def test_restart_and_control_flow_persists_updates(storage_dir: Path):
    store = FileJobStore()
    manager = PipelineJobManager(max_workers=1, store=store, worker_pool_factory=lambda _: _DummyWorkerPool())

    request = _build_request()
    job = manager.submit(request, user_id="integration", user_role="user")

    persisted = persistence.load_job(job.job_id)
    assert persisted.status == PipelineJobStatus.PENDING
    assert persisted.created_at <= datetime.now(timezone.utc)
    assert persisted.user_id == "integration"
    assert persisted.user_role == "user"

    manager._executor.shutdown()

    # Simulate a process restart by building a new manager reading the same store.
    restarted_store = FileJobStore()
    restarted_manager = PipelineJobManager(
        max_workers=1, store=restarted_store, worker_pool_factory=lambda _: _DummyWorkerPool()
    )

    restored_job = restarted_manager.get(
        job.job_id,
        user_id="integration",
        user_role="user",
    )
    assert restored_job.status == PipelineJobStatus.PENDING

    paused = restarted_manager.pause_job(
        job.job_id,
        user_id="integration",
        user_role="user",
    )
    assert paused.status == PipelineJobStatus.PAUSED
    assert persistence.load_job(job.job_id).status == PipelineJobStatus.PAUSED

    resumed = restarted_manager.resume_job(
        job.job_id,
        user_id="integration",
        user_role="user",
    )
    assert resumed.status == PipelineJobStatus.PENDING
    assert persistence.load_job(job.job_id).status == PipelineJobStatus.PENDING

    cancelled = restarted_manager.cancel_job(
        job.job_id,
        user_id="integration",
        user_role="user",
    )
    assert cancelled.status == PipelineJobStatus.CANCELLED
    final = persistence.load_job(job.job_id)
    assert final.status == PipelineJobStatus.CANCELLED
    assert final.completed_at is not None

    restarted_manager._executor.shutdown()
