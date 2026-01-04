"""High-level orchestration utilities for pipeline jobs."""

from __future__ import annotations

import copy
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
from pathlib import Path
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
        self._job_handlers: Dict[str, Callable[[str], None]] = {}
        self._custom_workers: Dict[str, Callable[[PipelineJob], None]] = {}
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
        self._metadata_refresher = PipelineJobMetadataRefresher(self._file_locator)
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
                    self._register_job_handler(job_id, job)
                    if job.status == PipelineJobStatus.PENDING:
                        pending_jobs.append(job_id)

        self._storage.persist_reconciliation(updates)
        for job_id in pending_jobs:
            self._executor.submit(self._dispatch_execution, job_id)

    def _persist_source_file(self, job_id: str, request: PipelineRequest) -> Optional[str]:
        """Mirror the pipeline input file into the job's dedicated data directory."""

        input_file = getattr(request.inputs, "input_file", "")
        if not input_file:
            return None

        resolved_path: Optional[Path] = None
        candidate = Path(str(input_file)).expanduser()
        try:
            if candidate.is_file():
                resolved_path = candidate
        except OSError:
            resolved_path = None

        if resolved_path is None:
            base_dir = None
            context = request.context
            if context is not None:
                base_dir = getattr(context, "books_dir", None)
            resolved = cfg.resolve_file_path(input_file, base_dir)
            if resolved is not None:
                resolved_path = Path(resolved)

        if resolved_path is None or not resolved_path.exists():
            return None

        data_root = self._file_locator.data_root(job_id)
        data_root.mkdir(parents=True, exist_ok=True)

        destination = data_root / resolved_path.name
        job_root = self._file_locator.job_root(job_id)

        try:
            if destination.exists() and destination.resolve() == resolved_path.resolve():
                return destination.relative_to(job_root).as_posix()
        except OSError:
            pass

        try:
            shutil.copy2(resolved_path, destination)
        except Exception:  # pragma: no cover - defensive logging
            logger.debug(
                "Unable to mirror source file %s for job %s",
                resolved_path,
                job_id,
                exc_info=True,
            )
            return None

        return destination.relative_to(job_root).as_posix()

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

        data_root = self._file_locator.data_root(job_id)
        data_root.mkdir(parents=True, exist_ok=True)

        source_relative = self._persist_source_file(job_id, request)
        if source_relative:
            request.inputs.book_metadata.update(
                {
                    "source_path": source_relative,
                    "source_file": source_relative,
                }
            )

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
            job_type="book",
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
            self._register_job_handler(job_id, job)
            self._store.save(self._persistence.snapshot(job))

        if tuning_summary:
            tracker.publish_progress({"stage": "configuration", **tuning_summary})

        with log_mgr.log_context(job_id=job_id, correlation_id=request.correlation_id):
            logger.info(
                "Pipeline job submitted",
                extra={
                    "event": f"{job.job_type}.job.submitted",
                    "status": PipelineJobStatus.PENDING.value,
                    "attributes": {
                        "input_file": request.inputs.input_file,
                        "target_languages": request.inputs.target_languages,
                    },
                    "console_suppress": True,
                },
            )

        self._executor.submit(self._dispatch_execution, job_id)
        return job

    def submit_background_job(
        self,
        *,
        job_type: str,
        worker: Callable[[PipelineJob], None],
        tracker: Optional[ProgressTracker] = None,
        stop_event: Optional[threading.Event] = None,
        request_payload: Optional[Mapping[str, Any]] = None,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        setup: Optional[Callable[[PipelineJob], None]] = None,
    ) -> PipelineJob:
        """Register a non-pipeline job for asynchronous execution."""

        normalized_type = job_type or "custom"
        job_id = str(uuid4())
        tracker = tracker or ProgressTracker()
        stop_event = stop_event or threading.Event()

        job_root = self._file_locator.resolve_path(job_id)
        job_root.mkdir(parents=True, exist_ok=True)
        self._file_locator.metadata_root(job_id).mkdir(parents=True, exist_ok=True)
        self._file_locator.data_root(job_id).mkdir(parents=True, exist_ok=True)

        job = PipelineJob(
            job_id=job_id,
            job_type=normalized_type,
            status=PipelineJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            request=None,
            tracker=tracker,
            stop_event=stop_event,
            request_payload=dict(request_payload) if request_payload else None,
            resume_context=None,
            user_id=user_id,
            user_role=user_role,
        )

        if setup is not None:
            setup(job)

        tracker.register_observer(lambda event: self._store_event(job_id, event))

        with self._lock:
            self._jobs[job_id] = job
            self._custom_workers[job_id] = worker
            self._register_job_handler(job_id, job)
            snapshot = self._persistence.snapshot(job)
            self._store.save(snapshot)

        self._log_generic_job_submitted(job)
        self._executor.submit(self._dispatch_execution, job_id)
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

    def mutate_job(
        self,
        job_id: str,
        mutator: Callable[[PipelineJob], None],
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Apply ``mutator`` to the persisted job and store the updated snapshot."""

        job = self._get_unchecked(job_id)
        self._assert_job_access(job, user_id=user_id, user_role=user_role)

        with self._lock:
            target = self._jobs.get(job_id) or job
            mutator(target)
            snapshot = self._persistence.snapshot(target)
            if job_id in self._jobs:
                self._jobs[job_id] = target

        self._store.update(snapshot)
        return target

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
        correlation_id = self._job_correlation_id(job) if job is not None else None
        event_name = f"{job.job_type}.job.progress" if job is not None else "pipeline.job.progress"
        with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
            logger.info(
                "Pipeline progress event",
                extra={
                    "event": event_name,
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

    def _register_job_handler(self, job_id: str, job: PipelineJob) -> None:
        worker = self._custom_workers.get(job_id)
        if worker is not None:
            self._job_handlers[job_id] = lambda current_id=job_id, fn=worker: self._execute_custom(current_id, fn)
            return
        if job.job_type in {"pipeline", "book"}:
            self._job_handlers[job_id] = self._execute_pipeline
        else:
            self._job_handlers[job_id] = lambda current_id=job_id: self._execute_orphaned(current_id)

    def _dispatch_execution(self, job_id: str) -> None:
        handler = self._job_handlers.get(job_id)
        if handler is None:
            handler = self._execute_orphaned
        handler(job_id)

    def _job_correlation_id(self, job: PipelineJob) -> Optional[str]:
        request = job.request
        if request is None:
            return None
        return request.correlation_id

    def _execute_pipeline(self, job_id: str) -> None:
        self._job_executor.execute(job_id)

    def _execute_custom(
        self,
        job_id: str,
        worker: Callable[[PipelineJob], None],
    ) -> None:
        try:
            job = self._get_unchecked(job_id)
        except KeyError:
            return

        with self._lock:
            job.status = PipelineJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            snapshot = self._persistence.snapshot(job)
        self._store.update(snapshot)

        self._log_generic_job_started(job)

        try:
            worker(job)
        except Exception as exc:  # pragma: no cover - defensive guard
            with self._lock:
                job.status = PipelineJobStatus.FAILED
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                snapshot = self._persistence.snapshot(job)
            self._store.update(snapshot)
            if job.tracker is not None:
                job.tracker.record_error(exc, {"stage": job.job_type})
            self._log_generic_job_error(job, exc)
        else:
            terminal_states = {
                PipelineJobStatus.COMPLETED,
                PipelineJobStatus.FAILED,
                PipelineJobStatus.CANCELLED,
            }
            with self._lock:
                status = job.status
                if status not in terminal_states:
                    job.status = PipelineJobStatus.COMPLETED
                    status = job.status
                if job.completed_at is None:
                    job.completed_at = datetime.now(timezone.utc)
                snapshot = self._persistence.snapshot(job)
            self._store.update(snapshot)
            self._log_generic_job_finished(job, job.status)
        finally:
            with self._lock:
                self._custom_workers.pop(job_id, None)
                self._job_handlers.pop(job_id, None)
                snapshot = self._persistence.snapshot(job)
            self._store.update(snapshot)

            if job.tracker is not None:
                status = job.status
                if status == PipelineJobStatus.COMPLETED:
                    job.tracker.mark_finished(reason="completed", forced=False)
                elif status == PipelineJobStatus.CANCELLED:
                    job.tracker.mark_finished(reason="cancelled", forced=True)
                else:
                    job.tracker.mark_finished(reason="failed", forced=True)

            if job.started_at and job.completed_at:
                duration_ms = (job.completed_at - job.started_at).total_seconds() * 1000.0
                metric_name = f"{job.job_type}.job.duration"
                self._record_job_metric(
                    metric_name,
                    duration_ms,
                    {"job_id": job.job_id, "status": job.status.value},
                )

    def _execute_orphaned(self, job_id: str) -> None:
        try:
            job = self._get_unchecked(job_id)
        except KeyError:
            return
        message = f"No execution handler registered for job type '{job.job_type}'"
        with self._lock:
            job.status = PipelineJobStatus.FAILED
            job.error_message = message
            job.completed_at = job.completed_at or datetime.now(timezone.utc)
            snapshot = self._persistence.snapshot(job)
        self._store.update(snapshot)
        self._job_handlers.pop(job_id, None)
        if job.tracker is not None:
            job.tracker.mark_finished(reason="failed", forced=True)
        self._log_generic_job_error(job, RuntimeError(message))

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

    def _log_generic_job_started(self, job: PipelineJob) -> None:
        with self._log_context(job):
            logger.info(
                "Background job started",
                extra={
                    "event": f"{job.job_type}.job.started",
                    "status": PipelineJobStatus.RUNNING.value,
                    "console_suppress": True,
                },
            )

    def _log_generic_job_finished(self, job: PipelineJob, status: PipelineJobStatus) -> None:
        with self._log_context(job):
            logger.info(
                "Background job finished",
                extra={
                    "event": f"{job.job_type}.job.finished",
                    "status": status.value,
                    "console_suppress": True,
                },
            )

    def _log_generic_job_submitted(self, job: PipelineJob) -> None:
        with self._log_context(job):
            logger.info(
                "Background job submitted",
                extra={
                    "event": f"{job.job_type}.job.submitted",
                    "status": job.status.value,
                    "console_suppress": True,
                },
            )

    def _log_generic_job_error(self, job: PipelineJob, exc: Exception) -> None:
        with self._log_context(job):
            logger.error(
                "Background job encountered an error",
                extra={
                    "event": f"{job.job_type}.job.error",
                    "status": PipelineJobStatus.FAILED.value,
                    "attributes": {"error": str(exc)},
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
        try:
            metadata = self._store.get(job_id)
        except KeyError:
            metadata = self._load_metadata_from_disk(job_id)
            if metadata is None:
                raise
            try:
                self._store.save(metadata)
            except Exception:  # pragma: no cover - best effort cache
                logger.debug("Failed to cache job metadata for %s", job_id, exc_info=True)
        return self._persistence.build_job(metadata)

    def _load_metadata_from_disk(self, job_id: str) -> Optional[PipelineJobMetadata]:
        """Load job metadata from disk when the store misses the job."""

        candidates: list[Path] = []
        try:
            candidates.append(self._file_locator.resolve_metadata_path(job_id, "job.json"))
        except Exception:
            pass

        try:
            repo_root = cfg.SCRIPT_DIR.parent
            candidates.append(repo_root / "storage" / job_id / "metadata" / "job.json")
        except Exception:
            pass

        for path in candidates:
            try:
                if not path.exists():
                    continue
                payload = path.read_text(encoding="utf-8")
                return PipelineJobMetadata.from_json(payload)
            except Exception:  # pragma: no cover - defensive fallback
                logger.debug("Failed to load job metadata from %s", path, exc_info=True)
                continue

        return None

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
        with self._lock:
            self._jobs[job_id] = job
            self._register_job_handler(job_id, job)
        self._executor.submit(self._dispatch_execution, job_id)
        return job

    def _cleanup_generated_outputs(self, job_id: str) -> None:
        """Remove generated artifacts for ``job_id`` while keeping mirrored inputs."""

        media_root = self._file_locator.media_root(job_id)
        metadata_root = self._file_locator.metadata_root(job_id)
        subtitles_root = self._file_locator.subtitles_root(job_id)
        for path in (media_root, metadata_root, subtitles_root):
            try:
                if path.exists():
                    shutil.rmtree(path)
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Unable to clean generated path %s for job %s", path, job_id, exc_info=True)
        for path in (media_root, metadata_root, subtitles_root):
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Unable to recreate generated path %s for job %s", path, job_id, exc_info=True)

    def restart_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Restart a finished/failed job with the same settings, wiping generated outputs."""

        job = self._get_unchecked(job_id)
        self._assert_job_access(job, user_id=user_id, user_role=user_role)

        if job.job_type not in {"pipeline", "book"}:
            raise ValueError(f"Restart is not supported for job type '{job.job_type}'")
        if job.status in (PipelineJobStatus.RUNNING, PipelineJobStatus.PENDING):
            raise ValueError(f"Cannot restart job {job_id} while it is {job.status.value}")

        payload = job.request_payload or job.resume_context
        if payload is None:
            raise ValueError(f"Job {job_id} is missing request payload and cannot be restarted")

        previous_status = job.status

        # Wipe generated outputs so the rerun can overwrite cleanly.
        self._cleanup_generated_outputs(job_id)

        # Reset state and hydrate a fresh request/tracker.
        with self._lock:
            job.request = None
            job.tracker = None
            job.stop_event = None
            job.last_event = None
            job.result = None
            job.result_payload = None
            job.error_message = None
            job.generated_files = None
            job.chunk_manifest = None
            job.media_completed = False
            job.retry_summary = job.retry_summary  # keep retry history for observability
            job.started_at = None
            job.completed_at = None
            job.status = PipelineJobStatus.PENDING

        stop_event = threading.Event()
        request = self._request_factory.hydrate_request(job, payload, stop_event=stop_event)

        # Ensure output directories are re-established and context reflects current paths.
        media_root = self._file_locator.media_root(job_id)
        request.environment_overrides = dict(request.environment_overrides)
        request.environment_overrides["output_dir"] = str(media_root)
        context = request.context
        if context is not None:
            context = dataclass_replace(context, output_dir=media_root)
        else:
            context = cfg.build_runtime_context(dict(request.config), dict(request.environment_overrides))
            context = dataclass_replace(context, output_dir=media_root)
        request.context = context
        request.progress_tracker = request.progress_tracker or ProgressTracker()
        request.stop_event = stop_event
        request.job_id = job_id
        tracker = request.progress_tracker
        tracker.register_observer(lambda event: self._store_event(job_id, event))

        with self._lock:
            job.request = request
            job.tracker = tracker
            job.stop_event = stop_event
            job.resume_context = copy.deepcopy(payload)
            job.request_payload = copy.deepcopy(payload)
            self._jobs[job_id] = job
            self._register_job_handler(job_id, job)
            snapshot = self._persistence.snapshot(job)

        self._store.update(snapshot)
        tracker.publish_progress({"stage": "restart", "previous_status": previous_status.value})
        self._executor.submit(self._dispatch_execution, job_id)
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

        job = self._transitions.delete_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
        job_root = self._file_locator.job_root(job.job_id)
        try:
            shutil.rmtree(job_root)
        except FileNotFoundError:
            pass
        except OSError:  # pragma: no cover - defensive logging
            logger.debug(
                "Unable to remove job directory %s during delete", job_root,
                exc_info=True,
            )
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

        stored = self._store.list()
        with self._lock:
            active_jobs = dict(self._jobs)
            terminal_states = {
                PipelineJobStatus.COMPLETED,
                PipelineJobStatus.FAILED,
                PipelineJobStatus.CANCELLED,
                PipelineJobStatus.PAUSED,
            }
            stale_job_ids = [
                job_id
                for job_id, job in active_jobs.items()
                if job_id not in stored and job.status in terminal_states
            ]
            for job_id in stale_job_ids:
                self._jobs.pop(job_id, None)
                active_jobs.pop(job_id, None)
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

        if job.job_type not in {"pipeline", "book"}:
            raise ValueError(f"Metadata refresh is not available for job type '{job.job_type}'")

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
