import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from modules.progress_tracker import ProgressTracker
from modules.services.job_manager.job import PipelineJob, PipelineJobStatus
from modules.services.job_manager.request_factory import (
    PipelineRequestFactory,
    _build_pipeline_input,
    _coerce_bool,
    _coerce_float,
    _coerce_int,
    _hydrate_request_from_payload,
)
from modules.services.pipeline_service import PipelineRequest


def test_coerce_helpers_handle_common_inputs():
    assert _coerce_bool("YeS") is True
    assert _coerce_bool("0", default=True) is False
    assert _coerce_bool(None, default=True) is True

    assert _coerce_int("42") == 42
    assert _coerce_int("not a number", default=7) == 7

    assert _coerce_float("3.14") == pytest.approx(3.14)
    assert _coerce_float({}, default=2.5) == pytest.approx(2.5)


def test_build_pipeline_input_normalizes_values():
    payload = {
        "input_file": Path("/tmp/book.epub"),
        "base_output_file": "output",
        "input_language": "en",
        "target_languages": "es",
        "sentences_per_output_file": "5",
        "start_sentence": "2",
        "end_sentence": "invalid",
        "stitch_full": "true",
        "generate_audio": "yes",
        "audio_mode": None,
        "written_mode": "novel",
        "selected_voice": "voice1",
        "output_html": "1",
        "output_pdf": 0,
        "include_transliteration": "no",
        "tempo": "fast",
        "media_metadata": "unexpected",
    }

    pipeline_input = _build_pipeline_input(payload)

    assert pipeline_input.input_file == "/tmp/book.epub"
    assert pipeline_input.target_languages == ["es"]
    assert pipeline_input.sentences_per_output_file == 5
    assert pipeline_input.start_sentence == 2
    assert pipeline_input.end_sentence is None
    assert pipeline_input.stitch_full is True
    assert pipeline_input.generate_audio is True
    assert pipeline_input.audio_mode == ""
    assert pipeline_input.output_html is True
    assert pipeline_input.output_pdf is False
    assert pipeline_input.include_transliteration is False
    assert pipeline_input.tempo == pytest.approx(1.0)
    assert pipeline_input.media_metadata.as_dict() == {}


def test_hydrate_request_creates_tracker_and_observer():
    created_trackers = []
    observed_events = []
    stop_events = []

    def tracker_factory():
        tracker = ProgressTracker()
        created_trackers.append(tracker)
        return tracker

    def stop_event_factory():
        event = threading.Event()
        stop_events.append(event)
        return event

    def observer_factory(job: PipelineJob):
        def _observer(event):
            observed_events.append((job.job_id, event.metadata.get("stage")))

        return _observer

    factory = PipelineRequestFactory(
        tracker_factory=tracker_factory,
        stop_event_factory=stop_event_factory,
        observer_factory=observer_factory,
    )

    job = PipelineJob(
        job_id="job-123",
        status=PipelineJobStatus.PAUSED,
        created_at=datetime.now(timezone.utc),
    )

    payload = {
        "config": {"foo": "bar"},
        "environment_overrides": {"path": "out"},
        "pipeline_overrides": {"mode": "fast"},
        "inputs": {"input_file": "input.txt", "target_languages": ["fr"]},
    }

    request = factory.hydrate_request(job, payload)

    assert created_trackers == [job.tracker]
    assert stop_events == [request.stop_event]
    assert request.inputs.target_languages == ["fr"]

    assert isinstance(request, PipelineRequest)
    assert request.config == {"foo": "bar"}
    assert request.environment_overrides == {"path": "out"}
    assert request.pipeline_overrides == {"mode": "fast"}
    assert request.job_id == "job-123"

    request.progress_tracker.publish_progress({"stage": "resume"})
    assert observed_events == [("job-123", "resume")]


def test_hydrate_request_reuses_existing_tracker_and_stop_event():
    tracker = ProgressTracker()
    stop_event = threading.Event()
    job = PipelineJob(
        job_id="job-456",
        status=PipelineJobStatus.PAUSED,
        created_at=datetime.now(timezone.utc),
        tracker=tracker,
        stop_event=stop_event,
    )

    existing_request = PipelineRequest(
        config={},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=_build_pipeline_input({}),
        progress_tracker=tracker,
        stop_event=stop_event,
        translation_pool=None,
        correlation_id="corr-1",
        job_id="job-456",
    )
    job.request = existing_request

    observer_called = False

    def observer_factory(_job: PipelineJob):
        nonlocal observer_called
        observer_called = True

        def _noop(_event):
            pass

        return _noop

    def _fail_tracker_factory():
        raise AssertionError("tracker factory should not be used")

    def _fail_stop_event_factory():
        raise AssertionError("stop event factory should not be used")

    factory = PipelineRequestFactory(
        tracker_factory=_fail_tracker_factory,
        stop_event_factory=_fail_stop_event_factory,
        observer_factory=observer_factory,
    )

    payload = {
        "config": {"new": "value"},
        "inputs": ["unexpected"],
    }

    request = factory.hydrate_request(job, payload)

    assert request.progress_tracker is tracker
    assert request.stop_event is stop_event
    assert request.correlation_id == "corr-1"
    assert observer_called is False
    assert request.inputs.target_languages == []


def test_hydrate_request_from_payload_function_matches_factory():
    tracker = ProgressTracker()
    job = PipelineJob(
        job_id="job-789",
        status=PipelineJobStatus.PAUSED,
        created_at=datetime.now(timezone.utc),
    )

    payload = {
        "config": {},
        "inputs": {"target_languages": ["de"]},
    }

    request = _hydrate_request_from_payload(
        job,
        payload,
        tracker_factory=lambda: tracker,
        stop_event_factory=threading.Event,
    )

    assert request.progress_tracker is tracker
    assert request.stop_event is not None
    assert job.tracker is tracker
    assert request.inputs.target_languages == ["de"]

