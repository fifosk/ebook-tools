from __future__ import annotations
import copy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Tuple

import pytest

import modules.services.job_manager.manager as manager_module
import modules.services.job_manager.metadata_refresher as metadata_refresher_module
from modules.services.file_locator import FileLocator
from modules.services.job_manager.job import PipelineJob, PipelineJobStatus
from modules.services.job_manager.manager import PipelineJobManager
from modules.services.job_manager.stores import InMemoryJobStore
from modules.services.pipeline_service import (
    PipelineInput,
    PipelineRequest,
    PipelineResponse,
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from modules.services.pipeline_types import PipelineMetadata


@pytest.fixture
def job_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PipelineJobManager:
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(
        job_max_workers=1,
        job_storage_dir=str(storage_root),
        storage_base_url="https://example.invalid",
    )
    monkeypatch.setattr(manager_module.cfg, "get_settings", lambda: settings)
    monkeypatch.setattr(manager_module.cfg, "get_hardware_tuning_defaults", lambda: {})

    locator = FileLocator(
        storage_dir=storage_root,
        base_url="https://example.invalid",
        settings_provider=lambda: settings,
    )
    manager = PipelineJobManager(
        max_workers=1,
        store=InMemoryJobStore(),
        file_locator=locator,
    )
    try:
        yield manager
    finally:
        manager._executor.shutdown(wait=True)


@pytest.fixture
def runtime_context_spy(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, object]]:
    events: List[Tuple[str, object]] = []

    def fake_build_runtime_context(config: Dict[str, object], overrides: Dict[str, object]) -> Dict[str, object]:
        context = {"config": dict(config), "env": dict(overrides)}
        events.append(("build", context))
        return context

    def fake_set_runtime_context(context: object) -> None:
        events.append(("set", context))

    def fake_cleanup_environment(context: object) -> None:
        events.append(("cleanup", context))

    def fake_clear_runtime_context() -> None:
        events.append(("clear", None))

    monkeypatch.setattr(metadata_refresher_module.cfg, "build_runtime_context", fake_build_runtime_context)
    monkeypatch.setattr(metadata_refresher_module.cfg, "set_runtime_context", fake_set_runtime_context)
    monkeypatch.setattr(metadata_refresher_module.cfg, "cleanup_environment", fake_cleanup_environment)
    monkeypatch.setattr(metadata_refresher_module.cfg, "clear_runtime_context", fake_clear_runtime_context)

    return events


def _build_request(metadata: Dict[str, object], input_file: str = "book.epub") -> PipelineRequest:
    return PipelineRequest(
        config={"auto_metadata": False},
        context=None,
        environment_overrides={"output_dir": "out"},
        pipeline_overrides={},
        inputs=PipelineInput(
            input_file=input_file,
            base_output_file="output",
            input_language="en",
            target_languages=["en"],
            sentences_per_output_file=1,
            start_sentence=0,
            end_sentence=None,
            stitch_full=False,
            generate_audio=False,
            audio_mode="tts",
            written_mode="text",
            selected_voice="voice",
            output_html=False,
            output_pdf=False,
            generate_video=False,
            include_transliteration=False,
            tempo=1.0,
            book_metadata=PipelineMetadata.from_mapping(metadata),
        ),
    )


def test_refresh_metadata_updates_job_payloads(
    job_manager: PipelineJobManager,
    runtime_context_spy: List[Tuple[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: Dict[str, object] = {}

    def fake_infer_metadata(
        input_file: str,
        *,
        existing_metadata: Dict[str, object],
        force_refresh: bool,
    ) -> Dict[str, object]:
        captured.update(
            {
                "input_file": input_file,
                "existing_metadata": dict(existing_metadata),
                "force_refresh": force_refresh,
            }
        )
        return {"title": "Updated", "language": "en"}

    monkeypatch.setattr(
        metadata_refresher_module.metadata_manager,
        "infer_metadata",
        fake_infer_metadata,
    )

    request = _build_request({"title": "Original"})
    result = PipelineResponse(success=True, metadata=PipelineMetadata.from_mapping({"title": "Original"}))
    job_id = "job-refresh"
    request_payload = serialize_pipeline_request(request)

    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        request=request,
        result=result,
        request_payload=request_payload,
        result_payload=serialize_pipeline_response(result),
        resume_context=copy.deepcopy(request_payload),
    )

    with job_manager._lock:
        job_manager._jobs[job_id] = job
        job_manager._store.save(job_manager._persistence.snapshot(job))

    refreshed = job_manager.refresh_metadata(job_id)

    assert refreshed.request is not None
    assert refreshed.request.inputs.book_metadata.as_dict() == {
        "title": "Updated",
        "language": "en",
    }
    assert refreshed.result is not None
    assert refreshed.result.metadata.as_dict() == {
        "title": "Updated",
        "language": "en",
    }
    assert refreshed.result_payload is not None
    assert refreshed.result_payload.get("book_metadata") == {
        "title": "Updated",
        "language": "en",
    }

    stored = job_manager._store.get(job_id)
    assert stored.request_payload is not None
    assert stored.request_payload["inputs"]["book_metadata"] == {
        "title": "Updated",
        "language": "en",
    }

    assert captured == {
        "input_file": "book.epub",
        "existing_metadata": {"title": "Original"},
        "force_refresh": True,
    }
    assert [event[0] for event in runtime_context_spy] == [
        "build",
        "set",
        "cleanup",
        "clear",
    ]


def test_refresh_metadata_handles_persisted_jobs_without_request(
    job_manager: PipelineJobManager,
    runtime_context_spy: List[Tuple[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        metadata_refresher_module.metadata_manager,
        "infer_metadata",
        lambda *_args, **_kwargs: {"title": "Stored", "updated": True},
    )

    job_id = "job-persisted"
    request_payload = {
        "config": {"auto_metadata": False},
        "environment_overrides": {"output_dir": "out"},
        "inputs": {
            "input_file": "book.epub",
            "book_metadata": {"title": "Stored"},
        },
    }

    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        request=None,
        result=None,
        request_payload=copy.deepcopy(request_payload),
        result_payload={"book_metadata": {"title": "Stored"}},
        resume_context=None,
    )

    job_manager._store.save(job_manager._persistence.snapshot(job))

    refreshed = job_manager.refresh_metadata(job_id)

    assert refreshed.request is None
    assert refreshed.request_payload == {
        "config": {"auto_metadata": False},
        "environment_overrides": {"output_dir": "out"},
        "inputs": {
            "input_file": "book.epub",
            "book_metadata": {"title": "Stored", "updated": True},
        },
    }
    assert refreshed.resume_context == refreshed.request_payload
    assert refreshed.result_payload == {
        "book_metadata": {"title": "Stored", "updated": True},
    }

    stored = job_manager._store.get(job_id)
    assert stored.request_payload is not None
    assert stored.request_payload["inputs"]["book_metadata"] == {
        "title": "Stored",
        "updated": True,
    }

    assert [event[0] for event in runtime_context_spy] == [
        "build",
        "set",
        "cleanup",
        "clear",
    ]


def test_refresh_metadata_requires_input_file(
    job_manager: PipelineJobManager,
    runtime_context_spy: List[Tuple[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_infer_metadata(*_args: object, **_kwargs: object) -> Dict[str, object]:
        raise AssertionError("metadata inference should not be called")

    monkeypatch.setattr(
        metadata_refresher_module.metadata_manager,
        "infer_metadata",
        fail_infer_metadata,
    )

    request = _build_request({"title": "Original"}, input_file="   ")
    job_id = "job-invalid"
    request_payload = serialize_pipeline_request(request)

    job = PipelineJob(
        job_id=job_id,
        status=PipelineJobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        request=request,
        result=None,
        request_payload=request_payload,
        result_payload=None,
        resume_context=copy.deepcopy(request_payload),
    )

    with job_manager._lock:
        job_manager._jobs[job_id] = job
        job_manager._store.save(job_manager._persistence.snapshot(job))

    with pytest.raises(ValueError):
        job_manager.refresh_metadata(job_id)

    assert runtime_context_spy == []
