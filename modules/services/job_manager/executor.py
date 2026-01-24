"""Execution primitives for pipeline job processing."""

from __future__ import annotations

import copy
import logging
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional

from ..pipeline_service import PipelineResponse, serialize_pipeline_response
from ...translation_engine import ThreadWorkerPool
from .execution_adapter import PipelineExecutionAdapter
from .job import PipelineJob, PipelineJobStatus
from .job_tuner import PipelineJobTuner
from .persistence import PipelineJobPersistence
from .stores import JobStore


@dataclass(frozen=True)
class PipelineJobExecutorHooks:
    """Optional callbacks invoked during job execution lifecycle."""

    on_start: Optional[Callable[[PipelineJob], None]] = None
    on_finish: Optional[Callable[[PipelineJob, PipelineJobStatus], None]] = None
    on_failure: Optional[Callable[[PipelineJob, Exception], None]] = None
    on_interrupted: Optional[
        Callable[[PipelineJob, PipelineJobStatus], None]
    ] = None
    pipeline_context_factory: Optional[
        Callable[[PipelineJob], AbstractContextManager[object]]
    ] = None
    record_metric: Optional[
        Callable[[str, float, Mapping[str, str]], None]
    ] = None


class PipelineJobExecutor:
    """Coordinate execution adapter invocations with persistence updates."""

    def __init__(
        self,
        *,
        job_getter: Callable[[str], PipelineJob],
        lock,
        store: JobStore,
        persistence: PipelineJobPersistence,
        tuner: PipelineJobTuner,
        execution: PipelineExecutionAdapter,
        hooks: Optional[PipelineJobExecutorHooks] = None,
    ) -> None:
        self._job_getter = job_getter
        self._lock = lock
        self._store = store
        self._persistence = persistence
        self._tuner = tuner
        self._execution = execution
        self._hooks = hooks or PipelineJobExecutorHooks()
        self._logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def execute(self, job_id: str) -> None:
        """Execute the pipeline request associated with ``job_id``."""

        try:
            job = self._job_getter(job_id)
        except KeyError:
            return

        with self._lock:
            job.status = PipelineJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            snapshot = self._persistence.snapshot(job)
        self._store.update(snapshot)

        self._dispatch_hook("on_start", job)

        response: Optional[PipelineResponse] = None
        status_after_error: Optional[PipelineJobStatus] = None

        try:
            assert job.request is not None  # noqa: S101 - defensive guard
            with self._pipeline_context(job):
                pool, owns_pool = self._tuner.acquire_worker_pool(job)
                if job.tuning_summary is not None:
                    with self._lock:
                        self._store.update(self._persistence.snapshot(job))
                job.owns_translation_pool = owns_pool
                response = self._execution.execute(job.request)
            with self._lock:
                current_status = job.status
                if current_status == PipelineJobStatus.CANCELLED:
                    job.result = None
                    job.result_payload = None
                    job.error_message = None
                    job.media_completed = False
                elif current_status == PipelineJobStatus.PAUSING:
                    job.generated_files = copy.deepcopy(response.generated_files)
                    job.result = None
                    job.result_payload = None
                    job.error_message = None
                    tracker = job.tracker
                    job.media_completed = bool(tracker.is_complete()) if tracker is not None else False
                    job.status = PipelineJobStatus.PAUSED
                elif current_status == PipelineJobStatus.PAUSED:
                    job.result = None
                    job.result_payload = None
                    job.error_message = None
                    tracker = job.tracker
                    if tracker is not None:
                        job.media_completed = tracker.is_complete()
                else:
                    job.result = response
                    job.result_payload = serialize_pipeline_response(response)
                    job.generated_files = copy.deepcopy(response.generated_files)
                    job.status = (
                        PipelineJobStatus.COMPLETED
                        if response.success
                        else PipelineJobStatus.FAILED
                    )
                    job.error_message = (
                        None
                        if response.success
                        else "Pipeline execution reported failure."
                    )
                    job.media_completed = bool(response.success)
        except Exception as exc:  # pragma: no cover - defensive logging
            with self._lock:
                interruption = job.status in (
                    PipelineJobStatus.PAUSED,
                    PipelineJobStatus.PAUSING,
                    PipelineJobStatus.CANCELLED,
                ) and (job.stop_event is None or job.stop_event.is_set())
                if interruption:
                    job.result = None
                    job.result_payload = None
                    job.error_message = None
                    status_after_error = job.status
                else:
                    job.result = None
                    job.result_payload = None
                    job.status = PipelineJobStatus.FAILED
                    job.error_message = str(exc)
                    status_after_error = job.status
            if status_after_error == PipelineJobStatus.FAILED:
                self._dispatch_hook("on_failure", job, exc)
                if job.tracker is not None:
                    job.tracker.record_error(exc, {"stage": "pipeline"})
            elif status_after_error is not None:
                self._dispatch_hook("on_interrupted", job, status_after_error)
        finally:
            should_release_pool = False
            with self._lock:
                status = job.status
                if job.owns_translation_pool:
                    should_release_pool = True
                job.owns_translation_pool = False
                terminal_states = {
                    PipelineJobStatus.COMPLETED,
                    PipelineJobStatus.FAILED,
                    PipelineJobStatus.CANCELLED,
                }
                if status in terminal_states:
                    job.completed_at = job.completed_at or datetime.now(timezone.utc)
                snapshot = self._persistence.snapshot(job)
            self._store.update(snapshot)
            # Release worker pool back to cache for reuse (or shutdown if no cache)
            if should_release_pool:
                try:
                    self._tuner.release_worker_pool(job)
                except Exception:  # pragma: no cover - defensive logging
                    self._logger.debug(
                        "Translation worker pool release raised an exception",
                        exc_info=True,
                    )
            if job.tracker is not None:
                if status == PipelineJobStatus.COMPLETED:
                    job.tracker.mark_finished(reason="completed", forced=False)
                elif status == PipelineJobStatus.FAILED:
                    job.tracker.mark_finished(reason="failed", forced=True)
                elif status == PipelineJobStatus.CANCELLED:
                    job.tracker.mark_finished(reason="cancelled", forced=True)
            if status in {
                PipelineJobStatus.COMPLETED,
                PipelineJobStatus.FAILED,
                PipelineJobStatus.CANCELLED,
            }:
                duration_ms = 0.0
                if job.started_at and job.completed_at:
                    duration_ms = (
                        job.completed_at - job.started_at
                    ).total_seconds() * 1000.0
                self._record_metric(
                    "pipeline.job.duration",
                    duration_ms,
                    {"job_id": job.job_id, "status": status.value},
                )
            self._dispatch_hook("on_finish", job, status)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _dispatch_hook(self, name: str, *args) -> None:
        hook = getattr(self._hooks, name, None)
        if hook is not None:
            hook(*args)

    def _pipeline_context(self, job: PipelineJob) -> AbstractContextManager[object]:
        factory = self._hooks.pipeline_context_factory
        if factory is None:
            return nullcontext()
        return factory(job)

    def _record_metric(
        self, name: str, value: float, attributes: Mapping[str, str]
    ) -> None:
        recorder = self._hooks.record_metric
        if recorder is None:
            return
        recorder(name, value, attributes)


__all__ = [
    "PipelineJobExecutor",
    "PipelineJobExecutorHooks",
]
