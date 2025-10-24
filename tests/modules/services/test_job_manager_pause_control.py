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
    progress_recorded = threading.Event()

    run_count = 0
    start_sentences: list[int] = []

    def fake_run_pipeline(request: pipeline_service.PipelineRequest) -> pipeline_service.PipelineResponse:
        nonlocal run_count
        start_sentences.append(request.inputs.start_sentence)
        run_count += 1
        if run_count == 1:
            first_run_started.set()
            if request.progress_tracker is not None:
                request.progress_tracker.set_total(10)
                request.progress_tracker.record_media_completion(0, 4)
            progress_recorded.set()
            while not request.stop_event.wait(0.01):
                pass
            first_run_released.set()
            return pipeline_service.PipelineResponse(success=True)

        resumed_run_started.set()
        return pipeline_service.PipelineResponse(success=True)

    monkeypatch.setattr(job_manager_module, "run_pipeline", fake_run_pipeline)

    manager = PipelineJobManager(max_workers=1, store=InMemoryJobStore())
    try:
        request = _build_request()
        request.inputs.start_sentence = 1
        request.inputs.end_sentence = 8
        job = manager.submit(request)

        assert first_run_started.wait(timeout=1.0)
        assert progress_recorded.wait(timeout=1.0)

        paused = manager.pause_job(job.job_id)
        assert paused.status == PipelineJobStatus.PAUSED

        assert first_run_released.wait(timeout=1.0)

        state = manager.get(job.job_id)
        assert state.resume_context is not None
        resume_inputs = state.resume_context.get("inputs", {})
        assert resume_inputs.get("start_sentence") == 5

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
        assert start_sentences == [1, 5]
    finally:
        manager._executor.shutdown(wait=True)


@pytest.mark.timeout(5)
def test_resume_rolls_back_to_last_completed_batch(monkeypatch):
    PipelineJobManager = job_manager_module.PipelineJobManager
    PipelineJobStatus = job_manager_module.PipelineJobStatus
    InMemoryJobStore = job_manager_module.InMemoryJobStore

    first_run_started = threading.Event()
    progress_recorded = threading.Event()
    first_run_released = threading.Event()
    resumed_run_started = threading.Event()

    start_sentences: list[int] = []

    def fake_run_pipeline(request: pipeline_service.PipelineRequest) -> pipeline_service.PipelineResponse:
        start_sentences.append(request.inputs.start_sentence)
        if len(start_sentences) == 1:
            first_run_started.set()
            tracker = request.progress_tracker
            if tracker is not None:
                tracker.set_total(100)
                base = request.inputs.start_sentence
                for index in range(25):
                    tracker.record_media_completion(index, base + index)
            progress_recorded.set()
            while not request.stop_event.wait(0.01):
                pass
            first_run_released.set()
            return pipeline_service.PipelineResponse(success=True)

        resumed_run_started.set()
        return pipeline_service.PipelineResponse(success=True)

    monkeypatch.setattr(job_manager_module, "run_pipeline", fake_run_pipeline)

    manager = PipelineJobManager(max_workers=1, store=InMemoryJobStore())
    try:
        request = _build_request()
        request.inputs.start_sentence = 1
        request.inputs.sentences_per_output_file = 10
        job = manager.submit(request)

        assert first_run_started.wait(timeout=1.0)
        assert progress_recorded.wait(timeout=1.0)

        paused = manager.pause_job(job.job_id)
        assert paused.status == PipelineJobStatus.PAUSED

        assert first_run_released.wait(timeout=1.0)

        state = manager.get(job.job_id)
        assert state.resume_context is not None
        resume_inputs = state.resume_context.get("inputs", {})
        assert resume_inputs.get("start_sentence") == 21
        assert resume_inputs.get("sentences_per_output_file") == 10

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
        assert start_sentences == [1, 21]
    finally:
        manager._executor.shutdown(wait=True)
