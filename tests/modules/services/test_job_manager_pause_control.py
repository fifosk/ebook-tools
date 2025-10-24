from __future__ import annotations

import threading
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
