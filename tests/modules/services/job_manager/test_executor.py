from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module
import threading
from typing import Callable, Dict, Mapping, Optional

import pytest

import modules.services.job_manager as job_manager_module
import modules.services.pipeline_service as pipeline_service

PipelineJobExecutor = job_manager_module.PipelineJobExecutor
PipelineJobExecutorHooks = job_manager_module.PipelineJobExecutorHooks
PipelineJob = job_manager_module.PipelineJob
PipelineJobStatus = job_manager_module.PipelineJobStatus
PipelineJobPersistence = job_manager_module.PipelineJobPersistence
InMemoryJobStore = job_manager_module.InMemoryJobStore
FileLocator = job_manager_module.FileLocator
PipelineExecutionAdapter = job_manager_module.PipelineExecutionAdapter


class _TrackerStub:
    def __init__(self) -> None:
        self.finished: list[tuple[str, bool]] = []
        self.errors: list[tuple[BaseException, Mapping[str, object]]] = []
        self.observers: list[Callable[[object], None]] = []

    def register_observer(self, callback: Callable[[object], None]) -> Callable[[], None]:
        self.observers.append(callback)
        return lambda: None

    def record_error(self, exc: BaseException, metadata: Mapping[str, object]) -> None:
        self.errors.append((exc, metadata))

    def mark_finished(self, *, reason: str, forced: bool) -> None:
        self.finished.append((reason, forced))

    def publish_progress(self, metadata: Optional[Mapping[str, object]] = None) -> None:  # noqa: ARG002 - parity with ProgressTracker
        return None

    def get_retry_counts(self) -> Optional[Mapping[str, int]]:
        return None


class _DummyPool:
    def __init__(self) -> None:
        self.shutdown_calls = 0

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class _TunerStub:
    def __init__(self, pool: _DummyPool) -> None:
        self.pool = pool
        self.acquired: list[str] = []

    def acquire_worker_pool(self, job: PipelineJob) -> tuple[Optional[_DummyPool], bool]:
        self.acquired.append(job.job_id)
        if job.request is not None:
            job.request.translation_pool = self.pool
        return self.pool, True

    def release_worker_pool(self, job: PipelineJob) -> None:
        if job.request is not None and job.request.translation_pool is not None:
            job.request.translation_pool.shutdown()
            job.request.translation_pool = None


class _HookRecorder:
    @dataclass
    class _RecordingContext:
        events: list[tuple[str, str]]
        job_id: str

        def __enter__(self) -> None:  # noqa: D401 - context manager protocol
            self.events.append(("enter", self.job_id))

        def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401 - context manager protocol
            self.events.append(("exit", self.job_id))
            return False

    def __init__(self) -> None:
        self.started: list[str] = []
        self.finished: list[tuple[str, PipelineJobStatus]] = []
        self.failures: list[tuple[str, BaseException]] = []
        self.interrupted: list[tuple[str, PipelineJobStatus]] = []
        self.metrics: list[tuple[str, float, Mapping[str, str]]] = []
        self.context_events: list[tuple[str, str]] = []

    def hooks(self) -> PipelineJobExecutorHooks:
        return PipelineJobExecutorHooks(
            on_start=lambda job: self.started.append(job.job_id),
            on_finish=lambda job, status: self.finished.append((job.job_id, status)),
            on_failure=lambda job, exc: self.failures.append((job.job_id, exc)),
            on_interrupted=lambda job, status: self.interrupted.append((job.job_id, status)),
            pipeline_context_factory=lambda job: self._RecordingContext(self.context_events, job.job_id),
            record_metric=self._record_metric,
        )

    def _record_metric(self, name: str, value: float, attributes: Mapping[str, str]) -> None:
        self.metrics.append((name, value, attributes))


def _build_request(tracker: _TrackerStub, stop_event: threading.Event) -> pipeline_service.PipelineRequest:
    request = pipeline_service.PipelineRequest(
        config={},
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
        progress_tracker=tracker,
        stop_event=stop_event,
    )
    request.correlation_id = "corr-id"
    request.job_id = "job-1"
    return request


def _build_job(
    tracker: _TrackerStub,
    request: pipeline_service.PipelineRequest,
) -> PipelineJob:
    job = PipelineJob(
        job_id=request.job_id or "job-1",
        status=PipelineJobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        request=request,
        tracker=tracker,
        stop_event=request.stop_event,
        request_payload=pipeline_service.serialize_pipeline_request(request),
    )
    job.resume_context = dict(job.request_payload)
    job.tuning_summary = {"thread_count": 1}
    return job


@pytest.fixture()
def persistence(tmp_path) -> PipelineJobPersistence:
    locator = FileLocator(storage_dir=tmp_path)
    return PipelineJobPersistence(locator)


def _build_executor(
    job: PipelineJob,
    *,
    persistence: PipelineJobPersistence,
    store: InMemoryJobStore,
    tuner: _TunerStub,
    adapter: PipelineExecutionAdapter,
    hooks: PipelineJobExecutorHooks,
) -> PipelineJobExecutor:
    jobs: Dict[str, PipelineJob] = {job.job_id: job}
    lock = threading.RLock()

    def _get_job(job_id: str) -> PipelineJob:
        try:
            return jobs[job_id]
        except KeyError as exc:
            raise KeyError(job_id) from exc

    return PipelineJobExecutor(
        job_getter=_get_job,
        lock=lock,
        store=store,
        persistence=persistence,
        tuner=tuner,
        execution=adapter,
        hooks=hooks,
    )


def test_executor_handles_success(persistence: PipelineJobPersistence) -> None:
    tracker = _TrackerStub()
    stop_event = threading.Event()
    request = _build_request(tracker, stop_event)
    job = _build_job(tracker, request)
    pool = _DummyPool()
    tuner = _TunerStub(pool)
    store = InMemoryJobStore()
    store.save(persistence.snapshot(job))
    recorder = _HookRecorder()

    class _SuccessAdapter(PipelineExecutionAdapter):
        def __init__(self) -> None:
            super().__init__(runner=lambda req: pipeline_service.PipelineResponse(success=True, generated_files={}))

    executor = _build_executor(
        job,
        persistence=persistence,
        store=store,
        tuner=tuner,
        adapter=_SuccessAdapter(),
        hooks=recorder.hooks(),
    )

    executor.execute(job.job_id)

    assert job.status == PipelineJobStatus.COMPLETED
    assert job.result is not None and job.result.success is True
    assert pool.shutdown_calls == 1
    assert job.request.translation_pool is None
    assert recorder.started == [job.job_id]
    assert recorder.finished == [(job.job_id, PipelineJobStatus.COMPLETED)]
    assert recorder.failures == []
    assert recorder.interrupted == []
    assert recorder.context_events == [("enter", job.job_id), ("exit", job.job_id)]
    assert recorder.metrics
    name, _, attrs = recorder.metrics[-1]
    assert name == "pipeline.job.duration"
    assert attrs["status"] == PipelineJobStatus.COMPLETED.value
    assert attrs["job_id"] == job.job_id
    assert tracker.finished == [("completed", False)]
    assert tuner.acquired == [job.job_id]
    metadata = store.get(job.job_id)
    assert metadata.status == PipelineJobStatus.COMPLETED


def test_executor_handles_adapter_failure(persistence: PipelineJobPersistence) -> None:
    tracker = _TrackerStub()
    stop_event = threading.Event()
    request = _build_request(tracker, stop_event)
    job = _build_job(tracker, request)
    pool = _DummyPool()
    tuner = _TunerStub(pool)
    store = InMemoryJobStore()
    store.save(persistence.snapshot(job))
    recorder = _HookRecorder()

    class _FailingAdapter(PipelineExecutionAdapter):
        def execute(self, request):  # type: ignore[override]
            raise RuntimeError("boom")

    executor = _build_executor(
        job,
        persistence=persistence,
        store=store,
        tuner=tuner,
        adapter=_FailingAdapter(),
        hooks=recorder.hooks(),
    )

    executor.execute(job.job_id)

    assert job.status == PipelineJobStatus.FAILED
    assert job.error_message == "boom"
    assert tracker.errors and tracker.errors[0][0].args == ("boom",)
    assert tracker.errors[0][1] == {"stage": "pipeline"}
    assert tracker.finished == [("failed", True)]
    assert recorder.failures and recorder.failures[0][0] == job.job_id
    assert recorder.interrupted == []
    assert recorder.context_events == [("enter", job.job_id), ("exit", job.job_id)]
    assert pool.shutdown_calls == 1
    assert recorder.metrics
    name, _, attrs = recorder.metrics[-1]
    assert name == "pipeline.job.duration"
    assert attrs["status"] == PipelineJobStatus.FAILED.value
    assert attrs["job_id"] == job.job_id
    assert tuner.acquired == [job.job_id]
    metadata = store.get(job.job_id)
    assert metadata.status == PipelineJobStatus.FAILED


def test_executor_respects_cancellation(persistence: PipelineJobPersistence) -> None:
    tracker = _TrackerStub()
    stop_event = threading.Event()
    request = _build_request(tracker, stop_event)
    job = _build_job(tracker, request)
    pool = _DummyPool()
    tuner = _TunerStub(pool)
    store = InMemoryJobStore()
    store.save(persistence.snapshot(job))
    recorder = _HookRecorder()

    class _CancellingAdapter(PipelineExecutionAdapter):
        def execute(self, request):  # type: ignore[override]
            job.status = PipelineJobStatus.CANCELLED
            if job.stop_event is not None:
                job.stop_event.set()
            return pipeline_service.PipelineResponse(success=True, generated_files={})

    executor = _build_executor(
        job,
        persistence=persistence,
        store=store,
        tuner=tuner,
        adapter=_CancellingAdapter(),
        hooks=recorder.hooks(),
    )

    executor.execute(job.job_id)

    assert job.status == PipelineJobStatus.CANCELLED
    assert job.result is None
    assert job.result_payload is None
    assert tracker.finished == [("cancelled", True)]
    assert recorder.interrupted == []
    assert recorder.finished == [(job.job_id, PipelineJobStatus.CANCELLED)]
    assert recorder.context_events == [("enter", job.job_id), ("exit", job.job_id)]
    assert recorder.metrics
    name, _, attrs = recorder.metrics[-1]
    assert name == "pipeline.job.duration"
    assert attrs["status"] == PipelineJobStatus.CANCELLED.value
    assert attrs["job_id"] == job.job_id
    assert pool.shutdown_calls == 1
    assert tuner.acquired == [job.job_id]
    metadata = store.get(job.job_id)
    assert metadata.status == PipelineJobStatus.CANCELLED
