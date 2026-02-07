from __future__ import annotations

from datetime import datetime, timezone
import shutil
import time
from pathlib import Path

import pytest

import modules.jobs.persistence as persistence
import modules.services.job_manager as job_manager_module
import modules.services.pipeline_service as pipeline_service
from modules.services.job_manager import FileJobStore, PipelineJobManager, PipelineJobStatus
from modules.services.job_manager.job_storage import JobStorageCoordinator
from modules.progress_tracker import ProgressEvent, ProgressSnapshot

from .conftest import DummyExecutor, DummyWorkerPool

job_manager = job_manager_module

pytestmark = pytest.mark.services


def _make_manager(store: FileJobStore, **kwargs) -> PipelineJobManager:
    """Create a manager with batching/caching disabled so disk writes are immediate."""
    coordinator = JobStorageCoordinator(
        store=store,
        enable_batching=False,
        enable_caching=False,
    )
    return PipelineJobManager(
        max_workers=1,
        storage_coordinator=coordinator,
        worker_pool_factory=kwargs.pop("worker_pool_factory", lambda _: DummyWorkerPool()),
        **kwargs,
    )


@pytest.fixture
def storage_dir(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "storage"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(path))

    import modules.config_manager as _cfg_mod

    _original_settings = _cfg_mod.get_settings()
    patched = type("Settings", (), dict(vars(_original_settings)))()
    patched.job_storage_dir = str(path)
    monkeypatch.setattr(_cfg_mod, "get_settings", lambda: patched)

    return path


@pytest.fixture(autouse=True)
def _patch_executor(monkeypatch):
    import modules.services.job_manager.manager as _mgr
    monkeypatch.setattr(_mgr, "ThreadPoolExecutor", DummyExecutor)


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
    manager = _make_manager(store)

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
    restarted_manager = _make_manager(restarted_store)

    restored_job = restarted_manager.get(
        job.job_id,
        user_id="integration",
        user_role="user",
    )
    assert restored_job.status == PipelineJobStatus.PENDING

    # Transition to RUNNING before pausing (pause requires RUNNING state).
    restored_job.status = PipelineJobStatus.RUNNING
    restarted_manager._jobs[job.job_id] = restored_job

    paused = restarted_manager.pause_job(
        job.job_id,
        user_id="integration",
        user_role="user",
    )
    assert paused.status == PipelineJobStatus.PAUSING
    assert persistence.load_job(job.job_id).status == PipelineJobStatus.PAUSING
    paused.status = PipelineJobStatus.PAUSED
    restarted_manager._jobs[job.job_id] = paused
    restarted_manager._store.update(restarted_manager._persistence.snapshot(paused))

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
    import modules.config_manager as _cfg_mod
    original_storage = tmp_path / "storage-original"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(original_storage))
    original_base_url = "https://cdn.example.invalid/original"
    monkeypatch.setenv("EBOOK_STORAGE_BASE_URL", original_base_url)

    _orig = _cfg_mod.get_settings()
    _patched = type("Settings", (), dict(vars(_orig)))()
    _patched.job_storage_dir = str(original_storage)
    _patched.storage_base_url = original_base_url
    monkeypatch.setattr(_cfg_mod, "get_settings", lambda: _patched)

    store = FileJobStore()
    manager = _make_manager(store)

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
    _patched.job_storage_dir = str(migrated_storage)
    _patched.storage_base_url = new_base_url

    shutil.move(str(original_storage), str(migrated_storage))

    restarted_store = FileJobStore()
    restarted_manager = _make_manager(restarted_store)

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
        assert entry["relative_path"] == "media/chunk-001/sample.mp3"
        assert entry["url"].startswith(new_base_url)
        assert entry["path"].startswith(str(migrated_storage))
    finally:
        restarted_manager._executor.shutdown(wait=False)
