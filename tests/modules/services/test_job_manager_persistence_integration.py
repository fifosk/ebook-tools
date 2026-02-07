from __future__ import annotations

from datetime import datetime, timezone
import shutil
import sys
import time
from importlib import import_module
from pathlib import Path
from typing import Callable

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import modules.jobs.persistence as persistence
import modules.services.job_manager as job_manager_module
import modules.services.pipeline_service as pipeline_service
from modules.services.job_manager import FileJobStore, PipelineJobManager, PipelineJobStatus

job_manager = job_manager_module

from modules.progress_tracker import ProgressEvent, ProgressSnapshot


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
    path = tmp_path / "storage"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(path))
    return path


@pytest.fixture(autouse=True)
def _patch_executor(monkeypatch):
    import modules.services.job_manager.manager as _mgr
    monkeypatch.setattr(_mgr, "ThreadPoolExecutor", _DummyExecutor)


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
            add_images=False,
            include_transliteration=False,
            tempo=1.0,
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
    assert paused.status == PipelineJobStatus.PAUSING
    assert persistence.load_job(job.job_id).status == PipelineJobStatus.PAUSING
    paused.status = PipelineJobStatus.PAUSED
    restarted_manager._jobs[job.job_id] = paused
    restarted_manager._store.update(persistence.snapshot(paused))

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


def test_generated_file_urls_survive_storage_dir_change(tmp_path: Path, monkeypatch):
    original_storage = tmp_path / "storage-original"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(original_storage))
    original_base_url = "https://cdn.example.invalid/original"
    monkeypatch.setenv("EBOOK_STORAGE_BASE_URL", original_base_url)

    store = FileJobStore()
    manager = PipelineJobManager(
        max_workers=1,
        store=store,
        worker_pool_factory=lambda _: _DummyWorkerPool(),
    )

    try:
        request = _build_request()
        job = manager.submit(request, user_id="migrator", user_role="user")
        job.status = PipelineJobStatus.RUNNING

        job_root = manager._file_locator.resolve_path(job.job_id)
        media_path = job_root / "media" / "chunk-001" / "sample.mp3"
        media_path.parent.mkdir(parents=True, exist_ok=True)
        media_path.write_bytes(b"hello world")

        generated_payload = {
            "chunks": [
                {
                    "chunk_id": "chunk-001",
                    "range_fragment": "001-010",
                    "start_sentence": 1,
                    "end_sentence": 10,
                    "files": [
                        {"type": "audio", "path": str(media_path)},
                    ],
                    "sentences": [
                        {
                            "sentence_number": 1,
                            "original": {"text": "Hello", "tokens": ["Hello"]},
                            "timeline": [],
                            "counts": {"original": 1},
                        }
                    ],
                }
            ]
        }

        event = ProgressEvent(
            event_type="file_chunk_generated",
            snapshot=ProgressSnapshot(
                completed=0,
                total=None,
                elapsed=0.0,
                speed=0.0,
                eta=None,
            ),
            timestamp=time.perf_counter(),
            metadata={
                "chunk_id": "chunk-001",
                "range_fragment": "001-010",
                "start_sentence": 1,
                "end_sentence": 10,
                "generated_files": generated_payload,
            },
        )

        manager._store_event(job.job_id, event)

        persisted_before = persistence.load_job(job.job_id)
        assert persisted_before.generated_files is not None
        assert persisted_before.generated_files["files"][0]["url"].startswith(original_base_url)
        chunk_entry = persisted_before.generated_files["chunks"][0]
        assert chunk_entry.get("metadata_path") == "metadata/chunk_0000.json"
    finally:
        manager._executor.shutdown(wait=False)

    migrated_storage = tmp_path / "storage-migrated"
    new_base_url = "https://cdn.example.invalid/new"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(migrated_storage))
    monkeypatch.setenv("EBOOK_STORAGE_BASE_URL", new_base_url)

    shutil.move(str(original_storage), str(migrated_storage))

    restarted_store = FileJobStore()
    restarted_manager = PipelineJobManager(
        max_workers=1,
        store=restarted_store,
        worker_pool_factory=lambda _: _DummyWorkerPool(),
    )

    try:
        restored_job = restarted_manager.get(
            job.job_id,
            user_id="migrator",
            user_role="user",
        )
        assert restored_job.generated_files is not None
        files_index = restored_job.generated_files.get("files", [])
        assert files_index
        entry = files_index[0]
        assert entry["relative_path"] == "chunk-001/sample.mp3"
        assert entry["url"].startswith(new_base_url)
        assert entry["path"].startswith(str(migrated_storage))
    finally:
        restarted_manager._executor.shutdown(wait=False)
