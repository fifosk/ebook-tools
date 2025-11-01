"""High-level orchestration utilities for pipeline jobs."""

from __future__ import annotations

import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
from typing import Any, Callable, ContextManager, Dict, Mapping, Optional
from uuid import uuid4

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ... import observability
from ...progress_tracker import ProgressEvent, ProgressTracker
from ...translation_engine import ThreadWorkerPool
from ..file_locator import FileLocator
from ..pipeline_service import (
    PipelineRequest,
    serialize_pipeline_request,
)
from .job import PipelineJob, PipelineJobStatus
from .lifecycle import compute_resume_context
from .metadata import PipelineJobMetadata
from .metadata_refresher import PipelineJobMetadataRefresher
from .persistence import PipelineJobPersistence
from .job_storage import JobStorageCoordinator
from .job_tuner import PipelineJobTuner
from .stores import JobStore
from .execution_adapter import PipelineExecutionAdapter
from .executor import PipelineJobExecutor, PipelineJobExecutorHooks
from .request_factory import PipelineRequestFactory
from .transition_coordinator import PipelineJobTransitionCoordinator

logger = log_mgr.logger

class PipelineJobManager:
    """Orchestrate background execution of pipeline jobs with persistence support."""

    def __init__(
        self,
        *,
        max_workers: Optional[int] = None,
        store: Optional[JobStore] = None,
        worker_pool_factory: Optional[Callable[[PipelineRequest], ThreadWorkerPool]] = None,
        storage_coordinator: Optional[JobStorageCoordinator] = None,
        tuner: Optional[PipelineJobTuner] = None,
        execution_adapter: Optional[PipelineExecutionAdapter] = None,
        file_locator: Optional[FileLocator] = None,
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
        self._storage = storage_coordinator or JobStorageCoordinator(store=store)
        self._store = self._storage.store
        executor_slots_getter = lambda: getattr(self._executor, "_max_workers", None)
        self._tuner = tuner or PipelineJobTuner(
            worker_pool_factory=worker_pool_factory,
            executor_slots_getter=executor_slots_getter,
        )
        self._execution = execution_adapter or PipelineExecutionAdapter()
        self._file_locator = file_locator or FileLocator()
        self._persistence = PipelineJobPersistence(self._file_locator)
        self._metadata_refresher = PipelineJobMetadataRefresher()
        self._request_factory = PipelineRequestFactory(
            tracker_factory=ProgressTracker,
            stop_event_factory=threading.Event,
            observer_factory=lambda job: lambda event: self._store_event(job.job_id, event),
        )
        self._transitions = PipelineJobTransitionCoordinator(
            lock=self._lock,
            jobs=self._jobs,
            store=self._store,
            persistence=self._persistence,
            request_factory=self._request_factory,
            authorize=self._assert_job_access,
        )
        hooks = PipelineJobExecutorHooks(
            on_start=self._log_job_started,
            on_finish=self._log_job_finished,
            on_failure=self._log_job_error,
            on_interrupted=self._log_job_interrupted,
            pipeline_context_factory=self._pipeline_operation_context,
            record_metric=self._record_job_metric,
        )
        self._job_executor = PipelineJobExecutor(
            job_getter=self._get_unchecked,
            lock=self._lock,
            store=self._store,
            persistence=self._persistence,
            tuner=self._tuner,
            execution=self._execution,
            hooks=hooks,
        )
        self._restore_persisted_jobs()

    def _restore_persisted_jobs(self) -> None:
        """Load persisted jobs and reconcile their in-memory representation."""

        stored_jobs = self._storage.load_all()

        updates: list[PipelineJobMetadata] = []
        pending_jobs: list[str] = []
        with self._lock:
            for job_id, metadata in stored_jobs.items():
                job = self._persistence.build_job(metadata)
                if job.status == PipelineJobStatus.RUNNING:
                    job.status = PipelineJobStatus.PAUSED
                    updates.append(self._persistence.snapshot(job))
                elif job.status == PipelineJobStatus.PAUSING:
                    job.status = PipelineJobStatus.PAUSED
                    updates.append(self._persistence.snapshot(job))
                if job.status in (
                    PipelineJobStatus.PENDING,
                    PipelineJobStatus.PAUSING,
                    PipelineJobStatus.PAUSED,
                ):
                    self._jobs[job_id] = job
                    if job.status == PipelineJobStatus.PENDING:
                        pending_jobs.append(job_id)

        self._storage.persist_reconciliation(updates)
        for job_id in pending_jobs:
            self._executor.submit(self._execute, job_id)

    def submit(
        self,
        request: PipelineRequest,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Register ``request`` for background execution."""

        job_id = str(uuid4())
        tracker = request.progress_tracker or ProgressTracker()
        request.progress_tracker = tracker
        stop_event = request.stop_event or threading.Event()
        request.stop_event = stop_event

        request.correlation_id = request.correlation_id or job_id
        request.job_id = job_id

        job_root = self._file_locator.resolve_path(job_id)
        job_root.mkdir(parents=True, exist_ok=True)

        media_root = self._file_locator.media_root(job_id)
        media_root.mkdir(parents=True, exist_ok=True)

        metadata_root = self._file_locator.metadata_root(job_id)
        metadata_root.mkdir(parents=True, exist_ok=True)

        environment_overrides = dict(request.environment_overrides)
        environment_overrides.setdefault("output_dir", str(media_root))
        job_storage_url = self._file_locator.resolve_url(job_id, "media")
        if job_storage_url:
            environment_overrides.setdefault("job_storage_url", job_storage_url)
        request.environment_overrides = environment_overrides

        context = request.context
        if context is not None:
            context = dataclass_replace(context, output_dir=media_root)
        else:
            context = cfg.build_runtime_context(
                dict(request.config),
                dict(environment_overrides),
            )
            context = dataclass_replace(context, output_dir=media_root)
        request.context = context

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
            user_id=user_id,
            user_role=user_role,
        )
        tuning_summary = self._tuner.build_tuning_summary(request)
        job.tuning_summary = tuning_summary if tuning_summary else None

        tracker.register_observer(lambda event: self._store_event(job_id, event))

        with self._lock:
            self._jobs[job_id] = job
            self._store.save(self._persistence.snapshot(job))

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

    @property
    def file_locator(self) -> FileLocator:
        return self._file_locator

    def apply_initial_metadata(
        self,
        job_id: str,
        metadata: Mapping[str, Any],
    ) -> None:
        """Attach pre-computed metadata to ``job_id`` and persist the update."""

        if not metadata:
            return

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return

            base_payload = copy.deepcopy(job.result_payload) if job.result_payload else {}
            book_metadata = base_payload.get("book_metadata")
            if not isinstance(book_metadata, dict):
                book_metadata = {}
            book_metadata.update(metadata)
            base_payload["book_metadata"] = book_metadata
            job.result_payload = base_payload

            snapshot = self._persistence.snapshot(job)

        self._store.update(snapshot)

    def _store_event(self, job_id: str, event: ProgressEvent) -> None:
        metadata = dict(event.metadata)
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.status == PipelineJobStatus.RUNNING:
                resume_context = compute_resume_context(job)
                if resume_context is not None:
                    job.resume_context = resume_context
            snapshot = self._persistence.apply_event(job, event)
            self._store.update(snapshot)
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

    def _execute(self, job_id: str) -> None:
        self._job_executor.execute(job_id)

    def _job_correlation_id(self, job: PipelineJob) -> Optional[str]:
        request = job.request
        if request is None:
            return None
        return request.correlation_id

    @contextmanager
    def _log_context(self, job: PipelineJob):
        with log_mgr.log_context(
            job_id=job.job_id,
            correlation_id=self._job_correlation_id(job),
        ):
            yield

    def _log_job_started(self, job: PipelineJob) -> None:
        with self._log_context(job):
            logger.info(
                "Pipeline job started",
                extra={
                    "event": "pipeline.job.started",
                    "status": PipelineJobStatus.RUNNING.value,
                    "console_suppress": True,
                },
            )

    def _log_job_finished(self, job: PipelineJob, status: PipelineJobStatus) -> None:
        with self._log_context(job):
            if status == PipelineJobStatus.PAUSED:
                logger.info(
                    "Pipeline job paused",
                    extra={
                        "event": "pipeline.job.paused",
                        "status": status.value,
                        "console_suppress": True,
                    },
                )
            else:
                logger.info(
                    "Pipeline job finished",
                    extra={
                        "event": "pipeline.job.finished",
                        "status": status.value,
                        "console_suppress": True,
                    },
                )

    def _log_job_error(self, job: PipelineJob, exc: Exception) -> None:
        with self._log_context(job):
            logger.error(
                "Pipeline job encountered an error",
                extra={
                    "event": "pipeline.job.error",
                    "status": PipelineJobStatus.FAILED.value,
                    "attributes": {"error": str(exc)},
                },
            )

    def _log_job_interrupted(self, job: PipelineJob, status: PipelineJobStatus) -> None:
        with self._log_context(job):
            logger.info(
                "Pipeline job interrupted",
                extra={
                    "event": "pipeline.job.interrupted",
                    "status": status.value,
                    "console_suppress": True,
                },
            )

    def _pipeline_operation_context(
        self, job: PipelineJob
    ) -> ContextManager[object]:
        return observability.pipeline_operation(
            "job",
            attributes={
                "job_id": job.job_id,
                "correlation_id": self._job_correlation_id(job),
            },
        )

    def _record_job_metric(
        self, name: str, value: float, attributes: Mapping[str, str]
    ) -> None:
        observability.record_metric(name, value, attributes)

    @staticmethod
    def _is_admin(user_role: Optional[str]) -> bool:
        return bool(user_role and user_role.lower() == "admin")

    def _get_unchecked(self, job_id: str) -> PipelineJob:
        """Return ``job_id`` without applying authorization checks."""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                return job
        metadata = self._store.get(job_id)
        return self._persistence.build_job(metadata)

    def _assert_job_access(
        self,
        job: PipelineJob,
        *,
        user_id: Optional[str],
        user_role: Optional[str],
    ) -> None:
        if self._is_admin(user_role):
            return
        if job.user_id is None:
            return
        if user_id is None or job.user_id != user_id:
            raise PermissionError("Not authorized to manage this job")

    def get(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Return the job associated with ``job_id``."""

        job = self._get_unchecked(job_id)
        self._assert_job_access(job, user_id=user_id, user_role=user_role)
        return job

    def pause_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Mark ``job_id`` as paused and persist the updated status."""

        return self._transitions.pause_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def resume_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Resume ``job_id`` from a paused state and persist the change."""

        job = self._transitions.resume_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
        self._executor.submit(self._execute, job_id)
        return job

    def cancel_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Cancel ``job_id`` and persist the terminal state."""

        return self._transitions.cancel_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

    def delete_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Remove ``job_id`` from in-memory tracking and persistence."""

        return self._transitions.delete_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )

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

        return self._transitions.finish_job(
            job_id,
            status=status,
            error_message=error_message,
            result_payload=result_payload,
        )

    def list(
        self,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, PipelineJob]:
        """Return a snapshot mapping of jobs respecting role-based visibility."""

        with self._lock:
            active_jobs = dict(self._jobs)
        stored = self._store.list()
        for job_id, metadata in stored.items():
            active_jobs.setdefault(job_id, self._persistence.build_job(metadata))

        if self._is_admin(user_role):
            return active_jobs
        if user_id:
            return {
                job_id: job
                for job_id, job in active_jobs.items()
                if job.user_id == user_id
            }
        return active_jobs

    def refresh_metadata(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Force a metadata refresh for ``job_id`` and persist the updated state."""

        with self._lock:
            job = self._jobs.get(job_id)

        if job is None:
            stored_metadata = self._store.get(job_id)
            job = self._persistence.build_job(stored_metadata)
        self._assert_job_access(job, user_id=user_id, user_role=user_role)

        self._metadata_refresher.refresh(job)

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
            self._store.update(self._persistence.snapshot(job))

        return job
