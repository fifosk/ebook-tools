from __future__ import annotations

from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Callable

import pytest

import modules.services.job_manager.manager as manager_module
from modules.services.job_manager.job import PipelineJobStatus, PipelineJobTransitionError
from modules.services.job_manager.manager import PipelineJobManager
from modules.services.job_manager.stores import InMemoryJobStore
from modules.services.pipeline_service import PipelineInput, PipelineRequest


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
def _patch_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(manager_module, "ThreadPoolExecutor", _DummyExecutor)


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


@pytest.fixture
def manager(tmp_path: Path) -> PipelineJobManager:
    store = InMemoryJobStore()
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: _DummyWorkerPool(),
    )
    yield manager
    manager._executor.shutdown()


def test_pause_job_requires_authorized_running_state(manager: PipelineJobManager) -> None:
    job = manager.submit(_build_request(), user_id="alice", user_role="editor")
    job.status = PipelineJobStatus.RUNNING
    manager._jobs[job.job_id] = job

    with pytest.raises(PermissionError):
        manager.pause_job(job.job_id, user_id="bob", user_role="viewer")

    paused = manager.pause_job(job.job_id, user_id="alice", user_role="editor")
    assert paused.status == PipelineJobStatus.PAUSING

    pending = manager.submit(_build_request(), user_id="alice", user_role="editor")
    with pytest.raises(PipelineJobTransitionError):
        manager.pause_job(pending.job_id, user_id="alice", user_role="editor")


def test_resume_job_requires_authorized_paused_state(manager: PipelineJobManager) -> None:
    job = manager.submit(_build_request(), user_id="alice", user_role="editor")
    job.status = PipelineJobStatus.RUNNING
    manager._jobs[job.job_id] = job
    paused = manager.pause_job(job.job_id, user_id="alice", user_role="editor")
    paused.status = PipelineJobStatus.PAUSED

    with pytest.raises(PermissionError):
        manager.resume_job(job.job_id, user_id="bob", user_role="viewer")

    resumed = manager.resume_job(job.job_id, user_id="alice", user_role="editor")
    assert resumed.status == PipelineJobStatus.PENDING

    other = manager.submit(_build_request(), user_id="alice", user_role="editor")
    with pytest.raises(PipelineJobTransitionError):
        manager.resume_job(other.job_id, user_id="alice", user_role="editor")


def test_cancel_job_requires_authorized_non_terminal_state(manager: PipelineJobManager) -> None:
    job = manager.submit(_build_request(), user_id="alice", user_role="editor")
    job.status = PipelineJobStatus.RUNNING
    manager._jobs[job.job_id] = job

    with pytest.raises(PermissionError):
        manager.cancel_job(job.job_id, user_id="bob", user_role="viewer")

    cancelled = manager.cancel_job(job.job_id, user_id="alice", user_role="editor")
    assert cancelled.status == PipelineJobStatus.CANCELLED

    terminal = manager.submit(_build_request(), user_id="alice", user_role="editor")
    terminal.status = PipelineJobStatus.COMPLETED
    manager._jobs[terminal.job_id] = terminal

    with pytest.raises(PipelineJobTransitionError):
        manager.cancel_job(terminal.job_id, user_id="alice", user_role="editor")


def test_cancel_job_preserves_generated_files(manager: PipelineJobManager) -> None:
    job = manager.submit(_build_request(), user_id="alice", user_role="editor")
    job.status = PipelineJobStatus.RUNNING
    manager._jobs[job.job_id] = job

    generated_payload = {
        "chunks": [
            {
                "chunk_id": "chunk-1",
                "files": [
                    {
                        "type": "audio",
                        "path": "audio/chunk-1.mp3",
                    }
                ],
            }
        ],
        "files": [
            {
                "chunk_id": "chunk-1",
                "type": "audio",
                "path": "audio/chunk-1.mp3",
            }
        ],
    }

    assert job.tracker is not None
    job.tracker.get_generated_files = lambda: generated_payload  # type: ignore[assignment]

    manager.cancel_job(job.job_id, user_id="alice", user_role="editor")

    restored = manager.get(job.job_id, user_id="alice", user_role="editor")
    assert restored.generated_files is not None
    assert restored.generated_files.get("chunks")
    assert restored.generated_files.get("files")
    assert restored.generated_files["chunks"][0]["chunk_id"] == "chunk-1"


def test_delete_job_requires_authorized_terminal_state(manager: PipelineJobManager) -> None:
    job = manager.submit(_build_request(), user_id="alice", user_role="editor")
    job.status = PipelineJobStatus.RUNNING
    manager._jobs[job.job_id] = job

    with pytest.raises(ValueError):
        manager.delete_job(job.job_id, user_id="alice", user_role="editor")

    manager.cancel_job(job.job_id, user_id="alice", user_role="editor")

    with pytest.raises(PermissionError):
        manager.delete_job(job.job_id, user_id="bob", user_role="viewer")

    deleted = manager.delete_job(job.job_id, user_id="alice", user_role="editor")
    assert deleted.status == PipelineJobStatus.CANCELLED


def test_delete_paused_job(manager: PipelineJobManager) -> None:
    job = manager.submit(_build_request(), user_id="alice", user_role="editor")
    job.status = PipelineJobStatus.PAUSED
    manager._jobs[job.job_id] = job

    deleted = manager.delete_job(job.job_id, user_id="alice", user_role="editor")
    assert deleted.status == PipelineJobStatus.PAUSED


def test_finish_job_requires_supported_terminal_status(manager: PipelineJobManager) -> None:
    job = manager.submit(_build_request(), user_id="alice", user_role="editor")

    with pytest.raises(ValueError):
        manager.finish_job(job.job_id, status=PipelineJobStatus.RUNNING)

    finished = manager.finish_job(job.job_id, status=PipelineJobStatus.COMPLETED)
    assert finished.status == PipelineJobStatus.COMPLETED
    assert finished.completed_at is not None
