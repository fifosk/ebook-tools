from __future__ import annotations

import threading
import time
from importlib import import_module

import pytest

from tests.helpers.job_manager_stubs import install_job_manager_stubs


install_job_manager_stubs()

job_manager_module = import_module("modules.services.job_manager")
pipeline_service = import_module("modules.services.pipeline_service")


def _build_request() -> pipeline_service.PipelineRequest:
    return pipeline_service.PipelineRequest(
        config={},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=pipeline_service.PipelineInput(),
    )


@pytest.mark.timeout(5)
def test_pause_signals_stop_event_and_preserves_state(monkeypatch):
    PipelineJobManager = job_manager_module.PipelineJobManager
    PipelineJobStatus = job_manager_module.PipelineJobStatus
    InMemoryJobStore = job_manager_module.InMemoryJobStore

    start_event = threading.Event()
    stop_observed = threading.Event()

    def fake_run_pipeline(request: pipeline_service.PipelineRequest) -> pipeline_service.PipelineResponse:
        start_event.set()
        while not request.stop_event.wait(0.01):
            pass
        stop_observed.set()
        return pipeline_service.PipelineResponse(success=True)

    monkeypatch.setattr(job_manager_module, "run_pipeline", fake_run_pipeline)

    manager = PipelineJobManager(max_workers=1, store=InMemoryJobStore())
    try:
        job = manager.submit(_build_request())

        assert start_event.wait(timeout=1.0)

        paused = manager.pause_job(job.job_id)
        assert paused.status == PipelineJobStatus.PAUSED

        assert stop_observed.wait(timeout=1.0)

        state = manager.get(job.job_id)
        assert state.status == PipelineJobStatus.PAUSED
        assert state.completed_at is None
        assert state.stop_event is not None and state.stop_event.is_set()
    finally:
        manager._executor.shutdown(wait=True)


@pytest.mark.timeout(5)
def test_resume_requeues_job_and_completes(monkeypatch):
    PipelineJobManager = job_manager_module.PipelineJobManager
    PipelineJobStatus = job_manager_module.PipelineJobStatus
    InMemoryJobStore = job_manager_module.InMemoryJobStore

    first_run_started = threading.Event()
    first_run_released = threading.Event()
    resumed_run_started = threading.Event()

    run_count = 0

    def fake_run_pipeline(request: pipeline_service.PipelineRequest) -> pipeline_service.PipelineResponse:
        nonlocal run_count
        run_count += 1
        if run_count == 1:
            first_run_started.set()
            while not request.stop_event.wait(0.01):
                pass
            first_run_released.set()
            return pipeline_service.PipelineResponse(success=True)

        resumed_run_started.set()
        return pipeline_service.PipelineResponse(success=True)

    monkeypatch.setattr(job_manager_module, "run_pipeline", fake_run_pipeline)

    manager = PipelineJobManager(max_workers=1, store=InMemoryJobStore())
    try:
        job = manager.submit(_build_request())

        assert first_run_started.wait(timeout=1.0)

        paused = manager.pause_job(job.job_id)
        assert paused.status == PipelineJobStatus.PAUSED

        assert first_run_released.wait(timeout=1.0)

        resumed = manager.resume_job(job.job_id)
        assert resumed.status == PipelineJobStatus.PENDING

        assert resumed_run_started.wait(timeout=1.0)

        deadline = time.time() + 2.0
        while time.time() < deadline:
            state = manager.get(job.job_id)
            if state.status == PipelineJobStatus.COMPLETED:
                break
            time.sleep(0.01)
        else:
            pytest.fail("Resumed job did not complete")

        final_state = manager.get(job.job_id)
        assert final_state.status == PipelineJobStatus.COMPLETED
        assert final_state.stop_event is not None and not final_state.stop_event.is_set()
        assert run_count == 2
    finally:
        manager._executor.shutdown(wait=True)
