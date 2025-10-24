"""High-level orchestration utilities for pipeline jobs."""

from __future__ import annotations

import copy
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional
from uuid import uuid4

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ... import metadata_manager
from ... import observability
from ...progress_tracker import ProgressEvent, ProgressTracker
from ...translation_engine import TranslationWorkerPool
from ..pipeline_service import (
    PipelineRequest,
    PipelineResponse,
    run_pipeline,
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from .job import PipelineJob, PipelineJobStatus, PipelineJobTransitionError
from .lifecycle import (
    apply_pause_transition,
    apply_resume_transition,
    compute_resume_context,
)
from .metadata import PipelineJobMetadata
from .progress import deserialize_progress_event, serialize_progress_event
from .stores import FileJobStore, InMemoryJobStore, JobStore, RedisJobStore

logger = log_mgr.logger

class PipelineJobManager:
    """Orchestrate background execution of pipeline jobs with persistence support."""

    def __init__(
        self,
        *,
        max_workers: Optional[int] = None,
        store: Optional[JobStore] = None,
        worker_pool_factory: Optional[Callable[[PipelineRequest], TranslationWorkerPool]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._jobs: Dict[str, PipelineJob] = {}
        settings = cfg.get_settings()
        configured_workers = max_workers if max_workers is not None else settings.job_max_workers
        if max_workers is None:
            hardware_defaults = cfg.get_hardware_tuning_defaults()
            recommended_workers = hardware_defaults.get("job_max_workers")
            if (
                isinstance(recommended_workers, int)
                and recommended_workers > 0
                and (
                    settings.job_max_workers <= 0
                    or settings.job_max_workers == cfg.DEFAULT_JOB_MAX_WORKERS
                )
            ):
                configured_workers = recommended_workers
        resolved_workers = max(1, int(configured_workers))
        self._executor = ThreadPoolExecutor(max_workers=resolved_workers)
        self._store = store or self._default_store()
        self._worker_pool_factory = (
            worker_pool_factory or self._default_worker_pool_factory
        )
        self._restore_persisted_jobs()

    @staticmethod
    def _coerce_non_negative_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None

    def _resolve_thread_count(self, request: PipelineRequest) -> Optional[int]:
        candidate = request.pipeline_overrides.get("thread_count")
        if candidate is None and request.context is not None:
            candidate = request.context.thread_count
        if candidate is None:
            candidate = request.config.get("thread_count")
        value = self._coerce_non_negative_int(candidate)
        if value is None:
            return None
        return max(1, value)

    def _resolve_queue_size(self, request: PipelineRequest) -> Optional[int]:
        candidate = request.pipeline_overrides.get("queue_size")
        if candidate is None and request.context is not None:
            candidate = request.context.queue_size
        if candidate is None:
            candidate = request.config.get("queue_size")
        return self._coerce_non_negative_int(candidate)

    def _resolve_job_max_workers(self, request: PipelineRequest) -> Optional[int]:
        candidate = request.pipeline_overrides.get("job_max_workers")
        if candidate is None:
            candidate = request.config.get("job_max_workers")
        if candidate is None:
            candidate = getattr(cfg.get_settings(), "job_max_workers", None)
        value = self._coerce_non_negative_int(candidate)
        if value is None or value <= 0:
            defaults = cfg.get_hardware_tuning_defaults()
            recommended = defaults.get("job_max_workers")
            if isinstance(recommended, int) and recommended > 0:
                return recommended
            return None
        return value

    def _build_tuning_summary(self, request: PipelineRequest) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        thread_count = self._resolve_thread_count(request)
        if thread_count is not None:
            summary["thread_count"] = thread_count
        queue_size = self._resolve_queue_size(request)
        if queue_size is not None:
            summary["queue_size"] = queue_size
        job_max_workers = self._resolve_job_max_workers(request)
        if job_max_workers is not None:
            summary["job_max_workers"] = job_max_workers
        slide_workers = request.pipeline_overrides.get("slide_parallel_workers")
        if slide_workers is None:
            slide_workers = request.config.get("slide_parallel_workers")
        slide_workers_value = self._coerce_non_negative_int(slide_workers)
        if slide_workers_value is not None:
            summary["slide_parallel_workers"] = slide_workers_value
        slide_mode = request.pipeline_overrides.get("slide_parallelism") or request.config.get(
            "slide_parallelism"
        )
        if slide_mode:
            summary["slide_parallelism"] = slide_mode
        executor_slots = getattr(self._executor, "_max_workers", None)
        if isinstance(executor_slots, int) and executor_slots > 0:
            summary["job_worker_slots"] = executor_slots
        pipeline_mode_override = request.pipeline_overrides.get("pipeline_mode")
        pipeline_mode = pipeline_mode_override
        if pipeline_mode is None and request.context is not None:
            pipeline_mode = request.context.pipeline_enabled
        if pipeline_mode is None:
            pipeline_mode = request.config.get("pipeline_mode")
        if pipeline_mode is not None:
            summary["pipeline_mode"] = bool(pipeline_mode)
        hardware_defaults = cfg.get_hardware_tuning_defaults()
        hardware_profile = hardware_defaults.get("profile")
        if isinstance(hardware_profile, str) and hardware_profile:
            summary.setdefault("hardware_profile", hardware_profile)
        detected_cpu = hardware_defaults.get("detected_cpu_count")
        if isinstance(detected_cpu, int) and detected_cpu > 0:
            summary.setdefault("detected_cpu_cores", detected_cpu)
        detected_memory = hardware_defaults.get("detected_memory_gib")
        if isinstance(detected_memory, (int, float)) and detected_memory > 0:
            summary.setdefault("detected_memory_gib", detected_memory)
        return summary

    def _default_worker_pool_factory(self, request: PipelineRequest) -> TranslationWorkerPool:
        max_workers = self._resolve_thread_count(request)
        return TranslationWorkerPool(max_workers=max_workers)

    @staticmethod
    def _maybe_update_translation_pool_summary(
        job: PipelineJob, pool: Optional[TranslationWorkerPool]
    ) -> None:
        if job.tuning_summary is None or pool is None:
            return
        worker_count = getattr(pool, "max_workers", None)
        if worker_count is not None:
            job.tuning_summary["translation_pool_workers"] = int(worker_count)
        pool_mode = getattr(pool, "mode", None)
        if pool_mode:
            job.tuning_summary["translation_pool_mode"] = pool_mode

    def _restore_persisted_jobs(self) -> None:
        """Load persisted jobs and reconcile their in-memory representation."""

        try:
            stored_jobs = self._store.list()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to load persisted pipeline jobs",  # pragma: no cover - log only
                exc_info=exc,
                extra={"event": "pipeline.job.restore.failed", "console_suppress": True},
            )
            return

        updates: list[PipelineJobMetadata] = []
        with self._lock:
            for job_id, metadata in stored_jobs.items():
                job = self._build_job_from_metadata(metadata)
                if job.status == PipelineJobStatus.RUNNING:
                    job.status = PipelineJobStatus.PAUSED
                    updates.append(self._snapshot(job))
                if job.status in (
                    PipelineJobStatus.PENDING,
                    PipelineJobStatus.PAUSED,
                ):
                    self._jobs[job_id] = job

        for payload in updates:
            try:
                self._store.update(payload)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Failed to persist reconciled job state",  # pragma: no cover - log only
                    exc_info=exc,
                    extra={
                        "event": "pipeline.job.restore.persist_failed",
                        "job_id": payload.job_id,
                        "console_suppress": True,
                    },
                )

    def _default_store(self) -> JobStore:
        settings = cfg.get_settings()
        secret = settings.job_store_url
        url = secret.get_secret_value() if secret is not None else None
        if not url:
            url = os.environ.get("JOB_STORE_URL")
        if url:
            try:
                logger.debug("Using RedisJobStore for pipeline job metadata at %s", url)
                return RedisJobStore(url)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to initialize RedisJobStore: %s", exc)
        try:
            return FileJobStore()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to initialize FileJobStore: %s", exc)
        return InMemoryJobStore()

    def _snapshot(self, job: PipelineJob) -> PipelineJobMetadata:
        last_event = serialize_progress_event(job.last_event) if job.last_event else None
        result_payload = (
            copy.deepcopy(job.result_payload) if job.result_payload is not None else None
        )
        if result_payload is None and job.result is not None:
            result_payload = serialize_pipeline_response(job.result)
        if job.request is not None:
            request_payload = serialize_pipeline_request(job.request)
        else:
            request_payload = (
                copy.deepcopy(job.request_payload) if job.request_payload else None
            )
        resume_context = (
            copy.deepcopy(job.resume_context) if job.resume_context is not None else None
        )
        if resume_context is None and request_payload is not None:
            resume_context = copy.deepcopy(request_payload)
        return PipelineJobMetadata(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            last_event=last_event,
            result=result_payload,
            request_payload=request_payload,
            resume_context=resume_context,
            tuning_summary=copy.deepcopy(job.tuning_summary)
            if job.tuning_summary is not None
            else None,
        )

    def submit(self, request: PipelineRequest) -> PipelineJob:
        """Register ``request`` for background execution."""

        job_id = str(uuid4())
        tracker = request.progress_tracker or ProgressTracker()
        request.progress_tracker = tracker
        stop_event = request.stop_event or threading.Event()
        request.stop_event = stop_event

        request.correlation_id = request.correlation_id or job_id
        request.job_id = job_id

        request_payload = serialize_pipeline_request(request)
        job = PipelineJob(
            job_id=job_id,
            status=PipelineJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            request=request,
            tracker=tracker,
            stop_event=stop_event,
            request_payload=request_payload,
            resume_context=copy.deepcopy(request_payload),
        )
        tuning_summary = self._build_tuning_summary(request)
        job.tuning_summary = tuning_summary if tuning_summary else None

        tracker.register_observer(lambda event: self._store_event(job_id, event))

        with self._lock:
            self._jobs[job_id] = job
            self._store.save(self._snapshot(job))

        if tuning_summary:
            tracker.publish_progress({"stage": "configuration", **tuning_summary})

        with log_mgr.log_context(job_id=job_id, correlation_id=request.correlation_id):
            logger.info(
                "Pipeline job submitted",
                extra={
                    "event": "pipeline.job.submitted",
                    "status": PipelineJobStatus.PENDING.value,
                    "attributes": {
                        "input_file": request.inputs.input_file,
                        "target_languages": request.inputs.target_languages,
                    },
                    "console_suppress": True,
                },
            )

        self._executor.submit(self._execute, job_id)
        return job

    def _store_event(self, job_id: str, event: ProgressEvent) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.last_event = event
            if job.status == PipelineJobStatus.RUNNING:
                resume_context = compute_resume_context(job)
                if resume_context is not None:
                    job.resume_context = resume_context
            self._store.update(self._snapshot(job))
        metadata = dict(event.metadata)
        stage = metadata.get("stage")
        correlation_id = None
        if job and job.request is not None:
            correlation_id = job.request.correlation_id
        with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
            logger.info(
                "Pipeline progress event",
                extra={
                    "event": "pipeline.job.progress",
                    "stage": stage,
                    "attributes": {
                        "event_type": event.event_type,
                        "completed": event.snapshot.completed,
                        "total": event.snapshot.total,
                        "metadata": metadata,
                    },
                    "console_suppress": True,
                },
            )

    def _acquire_worker_pool(
        self, job: PipelineJob
    ) -> tuple[Optional[TranslationWorkerPool], bool]:
        request = job.request
        if request is None:
            return None, False
        if request.translation_pool is not None:
            pool = request.translation_pool
            self._maybe_update_translation_pool_summary(job, pool)
            return pool, False
        pool = self._worker_pool_factory(request)
        request.translation_pool = pool
        self._maybe_update_translation_pool_summary(job, pool)
        return pool, True

    def _execute(self, job_id: str) -> None:
        try:
            job = self.get(job_id)
        except KeyError:
            return

        with self._lock:
            job.status = PipelineJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            self._store.update(self._snapshot(job))

        pool: Optional[TranslationWorkerPool]
        owns_pool: bool
        correlation_id = job.request.correlation_id if job.request else None
        try:
            assert job.request is not None  # noqa: S101
            with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
                logger.info(
                    "Pipeline job started",
                    extra={
                        "event": "pipeline.job.started",
                        "status": PipelineJobStatus.RUNNING.value,
                        "console_suppress": True,
                    },
                )
            with observability.pipeline_operation(
                "job",
                attributes={"job_id": job_id, "correlation_id": correlation_id},
            ):
                pool, owns_pool = self._acquire_worker_pool(job)
                if job.tuning_summary is not None:
                    with self._lock:
                        self._store.update(self._snapshot(job))
                job.owns_translation_pool = owns_pool
                response = run_pipeline(job.request)
            with self._lock:
                job.result = response
                job.result_payload = serialize_pipeline_response(response)
                job.status = (
                    PipelineJobStatus.COMPLETED if response.success else PipelineJobStatus.FAILED
                )
                job.error_message = None if response.success else "Pipeline execution reported failure."
                self._store.update(self._snapshot(job))
        except Exception as exc:  # pragma: no cover - defensive logging
            with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
                logger.error(
                    "Pipeline job encountered an error",
                    extra={
                        "event": "pipeline.job.error",
                        "status": PipelineJobStatus.FAILED.value,
                        "attributes": {"error": str(exc)},
                    },
                )
            with self._lock:
                job.result = None
                job.result_payload = None
                job.status = PipelineJobStatus.FAILED
                job.error_message = str(exc)
                self._store.update(self._snapshot(job))
            if job.tracker is not None:
                job.tracker.record_error(exc, {"stage": "pipeline"})
        finally:
            with self._lock:
                job.completed_at = datetime.now(timezone.utc)
                self._store.update(self._snapshot(job))
            if job.tracker is not None:
                result = job.result
                forced = not (result.success if isinstance(result, PipelineResponse) else False)
                reason = "completed" if not forced else "failed"
                job.tracker.mark_finished(reason=reason, forced=forced)
            if job.request is not None and job.owns_translation_pool:
                pool = job.request.translation_pool
                if pool is not None:
                    pool.shutdown()
            with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
                logger.info(
                    "Pipeline job finished",
                    extra={
                        "event": "pipeline.job.finished",
                        "status": job.status.value,
                        "console_suppress": True,
                    },
                )
                duration_ms = 0.0
                if job.started_at and job.completed_at:
                    duration_ms = (
                        job.completed_at - job.started_at
                    ).total_seconds() * 1000.0
                observability.record_metric(
                    "pipeline.job.duration",
                    duration_ms,
                    {"job_id": job_id, "status": job.status.value},
                )

    def get(self, job_id: str) -> PipelineJob:
        """Return the job associated with ``job_id``."""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                return job
        metadata = self._store.get(job_id)
        return self._build_job_from_metadata(metadata)

    def _mutate_job(self, job_id: str, mutator: Callable[[PipelineJob], None]) -> PipelineJob:
        """Apply ``mutator`` to ``job_id`` and persist the resulting state."""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                metadata = self._store.get(job_id)
                job = self._build_job_from_metadata(metadata)
            try:
                mutator(job)
            except ValueError as exc:
                raise PipelineJobTransitionError(job_id, job, str(exc)) from exc
            if job.status in (
                PipelineJobStatus.PENDING,
                PipelineJobStatus.RUNNING,
                PipelineJobStatus.PAUSED,
            ):
                self._jobs[job_id] = job
            else:
                self._jobs.pop(job_id, None)
            snapshot = self._snapshot(job)

        self._store.update(snapshot)
        return job

    def pause_job(self, job_id: str) -> PipelineJob:
        """Mark ``job_id`` as paused and persist the updated status."""

        def _pause(job: PipelineJob) -> None:
            apply_pause_transition(job)

        return self._mutate_job(job_id, _pause)

    def resume_job(self, job_id: str) -> PipelineJob:
        """Resume ``job_id`` from a paused state and persist the change."""

        def _resume(job: PipelineJob) -> None:
            apply_resume_transition(job)

        return self._mutate_job(job_id, _resume)

    def cancel_job(self, job_id: str) -> PipelineJob:
        """Cancel ``job_id`` and persist the terminal state."""

        def _cancel(job: PipelineJob) -> None:
            if job.status in (
                PipelineJobStatus.COMPLETED,
                PipelineJobStatus.FAILED,
                PipelineJobStatus.CANCELLED,
            ):
                raise ValueError(
                    f"Cannot cancel job {job.job_id} in terminal state {job.status.value}"
                )
            if job.stop_event is not None:
                job.stop_event.set()
            job.status = PipelineJobStatus.CANCELLED
            job.completed_at = job.completed_at or datetime.now(timezone.utc)

        return self._mutate_job(job_id, _cancel)

    def delete_job(self, job_id: str) -> PipelineJob:
        """Remove ``job_id`` from in-memory tracking and persistence."""

        with self._lock:
            job = self._jobs.pop(job_id, None)

        if job is None:
            metadata = self._store.get(job_id)
            job = self._build_job_from_metadata(metadata)
        else:
            # ensure persistence has the latest snapshot before deletion
            snapshot = self._snapshot(job)
            try:
                self._store.update(snapshot)
            except Exception:
                # if persistence update fails, continue with delete attempt
                pass

        self._store.delete(job_id)
        return job

    def finish_job(
        self,
        job_id: str,
        *,
        status: PipelineJobStatus = PipelineJobStatus.COMPLETED,
        error_message: Optional[str] = None,
        result_payload: Optional[Mapping[str, Any]] = None,
    ) -> PipelineJob:
        """Persist a terminal state for ``job_id`` and return the updated job."""

        if status not in (
            PipelineJobStatus.COMPLETED,
            PipelineJobStatus.FAILED,
            PipelineJobStatus.CANCELLED,
        ):
            raise ValueError(f"Unsupported terminal status: {status}")

        def _finish(job: PipelineJob) -> None:
            job.status = status
            job.error_message = error_message
            if result_payload is not None:
                job.result_payload = copy.deepcopy(dict(result_payload))
            job.completed_at = job.completed_at or datetime.now(timezone.utc)

        return self._mutate_job(job_id, _finish)

    def _build_job_from_metadata(self, metadata: PipelineJobMetadata) -> PipelineJob:
        request_payload = (
            copy.deepcopy(metadata.request_payload)
            if metadata.request_payload is not None
            else None
        )
        resume_context = (
            copy.deepcopy(metadata.resume_context)
            if metadata.resume_context is not None
            else (copy.deepcopy(request_payload) if request_payload is not None else None)
        )
        result_payload = (
            copy.deepcopy(metadata.result) if metadata.result is not None else None
        )
        job = PipelineJob(
            job_id=metadata.job_id,
            status=metadata.status,
            created_at=metadata.created_at,
            started_at=metadata.started_at,
            completed_at=metadata.completed_at,
            error_message=metadata.error_message,
            result_payload=result_payload,
            request_payload=request_payload,
            resume_context=resume_context,
            tuning_summary=copy.deepcopy(metadata.tuning_summary)
            if metadata.tuning_summary is not None
            else None,
        )
        if metadata.last_event is not None:
            job.last_event = deserialize_progress_event(metadata.last_event)
        return job

    def list(self) -> Dict[str, PipelineJob]:
        """Return a snapshot mapping of all jobs."""

        with self._lock:
            active_jobs = dict(self._jobs)
        stored = self._store.list()
        for job_id, metadata in stored.items():
            active_jobs.setdefault(job_id, self._build_job_from_metadata(metadata))
        return active_jobs

    def refresh_metadata(self, job_id: str) -> PipelineJob:
        """Force a metadata refresh for ``job_id`` and persist the updated state."""

        with self._lock:
            job = self._jobs.get(job_id)

        if job is None:
            metadata = self._store.get(job_id)
            job = self._build_job_from_metadata(metadata)

        if job.request is not None:
            request_payload = serialize_pipeline_request(job.request)
        elif job.request_payload is not None:
            request_payload = dict(job.request_payload)
        else:
            raise KeyError(job_id)

        inputs_payload = dict(request_payload.get("inputs", {}))
        input_file = str(inputs_payload.get("input_file") or "").strip()
        if not input_file:
            raise ValueError(f"Job {job_id} does not include an input file for metadata refresh")

        existing_metadata = inputs_payload.get("book_metadata")
        if not isinstance(existing_metadata, dict):
            existing_metadata = {}

        config_payload = request_payload.get("config")
        if not isinstance(config_payload, dict):
            config_payload = {}
        environment_overrides = request_payload.get("environment_overrides")
        if not isinstance(environment_overrides, dict):
            environment_overrides = {}

        context = cfg.build_runtime_context(dict(config_payload), dict(environment_overrides))
        cfg.set_runtime_context(context)
        try:
            metadata = metadata_manager.infer_metadata(
                input_file,
                existing_metadata=dict(existing_metadata),
                force_refresh=True,
            )
        finally:
            try:
                cfg.cleanup_environment(context)
            finally:
                cfg.clear_runtime_context()

        inputs_payload["book_metadata"] = dict(metadata)
        request_payload["inputs"] = inputs_payload

        if job.request is not None:
            job.request.inputs.book_metadata = dict(metadata)
        job.request_payload = request_payload
        job.resume_context = copy.deepcopy(request_payload)

        if job.result is not None:
            job.result.book_metadata = dict(metadata)
            job.result_payload = serialize_pipeline_response(job.result)
        else:
            result_payload = dict(job.result_payload or {})
            result_payload["book_metadata"] = dict(metadata)
            job.result_payload = result_payload

        with log_mgr.log_context(job_id=job_id):
            logger.info(
                "Pipeline job metadata refreshed",
                extra={
                    "event": "pipeline.job.metadata.refreshed",
                    "console_suppress": True,
                },
            )

        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id] = job
            self._store.update(self._snapshot(job))

        return job
