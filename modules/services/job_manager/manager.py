"""High-level orchestration utilities for pipeline jobs."""

from __future__ import annotations

import asyncio
import copy
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional, Tuple

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ...progress_tracker import ProgressEvent, ProgressTracker
from ...translation_engine import ThreadWorkerPool
from ..file_locator import FileLocator
from ..pipeline_service import PipelineRequest, serialize_pipeline_request
from ...permissions import can_access, default_job_access, is_admin_role, resolve_access_policy
from .dynamic_executor import DynamicThreadPoolExecutor
from .job import PipelineJob, PipelineJobStatus
from .lifecycle import compute_resume_context
from .locking import JobLockManager
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
from .backpressure import (
    BackpressureAction,
    BackpressureController,
    BackpressurePolicy,
    BackpressureState,
    QueueFullError,
)

# Import from new modular components
from .job_logging import (
    _job_correlation_id,
    _log_context,
    log_job_started,
    log_job_finished,
    log_job_error,
    log_job_interrupted,
    log_generic_job_started,
    log_generic_job_finished,
    log_generic_job_submitted,
    log_generic_job_error,
    pipeline_operation_context,
    record_job_metric,
)
from .source_persistence import persist_source_file
from .job_submission import apply_backpressure, create_pipeline_job, create_background_job

logger = log_mgr.logger


class PipelineJobManager:
    """Orchestrate background execution of pipeline jobs with persistence support."""

    def __init__(
        self,
        *,
        max_workers: Optional[int] = None,
        min_workers: Optional[int] = None,
        dynamic_scaling: Optional[bool] = None,
        store: Optional[JobStore] = None,
        worker_pool_factory: Optional[Callable[[PipelineRequest], ThreadWorkerPool]] = None,
        storage_coordinator: Optional[JobStorageCoordinator] = None,
        tuner: Optional[PipelineJobTuner] = None,
        execution_adapter: Optional[PipelineExecutionAdapter] = None,
        file_locator: Optional[FileLocator] = None,
        backpressure_policy: Optional[BackpressurePolicy] = None,
        enable_backpressure: bool = True,
    ) -> None:
        # Fine-grained locking: per-job locks reduce contention
        self._job_locks = JobLockManager()
        # Global lock for registry operations (backwards compatibility)
        self._lock = threading.RLock()
        self._jobs: Dict[str, PipelineJob] = {}
        self._job_handlers: Dict[str, Callable[[str], None]] = {}
        self._custom_workers: Dict[str, Callable[[PipelineJob], None]] = {}
        # Optional notification callback (set via set_notification_callback)
        self._notification_callback: Optional[
            Callable[[str, str, Optional[str], str], Awaitable[None]]
        ] = None
        # Event deduplication: track last stored event signature per job
        self._last_event_sig: Dict[str, tuple] = {}
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

        # Determine if dynamic scaling should be used
        use_dynamic = dynamic_scaling
        if use_dynamic is None:
            use_dynamic = getattr(settings, "job_dynamic_scaling", False)

        if use_dynamic:
            resolved_min = min_workers if min_workers is not None else max(1, resolved_workers // 2)
            self._executor = DynamicThreadPoolExecutor(
                min_workers=resolved_min,
                max_workers=resolved_workers,
                scale_up_threshold=2,
                scale_check_interval=1.0,
            )
        else:
            self._executor = ThreadPoolExecutor(max_workers=resolved_workers)

        # Initialize backpressure controller
        def _get_queue_depth() -> int:
            if hasattr(self._executor, "queue_depth"):
                return self._executor.queue_depth
            # For ThreadPoolExecutor, estimate from pending jobs
            with self._lock:
                return sum(
                    1 for j in self._jobs.values()
                    if j.status == PipelineJobStatus.PENDING
                )

        def _get_active_count() -> int:
            if hasattr(self._executor, "active_count"):
                return self._executor.active_count
            with self._lock:
                return sum(
                    1 for j in self._jobs.values()
                    if j.status == PipelineJobStatus.RUNNING
                )

        if enable_backpressure:
            policy = backpressure_policy or BackpressurePolicy(
                soft_limit=resolved_workers * 2,
                hard_limit=resolved_workers * 10,
            )
            self._backpressure = BackpressureController(
                policy=policy,
                queue_depth_getter=_get_queue_depth,
                active_count_getter=_get_active_count,
            )
        else:
            self._backpressure = None

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
            authorize=lambda job, user_id, user_role: self._assert_job_access(
                job,
                user_id=user_id,
                user_role=user_role,
                permission="edit",
            ),
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

    def submit(
        self,
        request: PipelineRequest,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        bypass_backpressure: bool = False,
    ) -> PipelineJob:
        """Register ``request`` for background execution."""

        apply_backpressure(self._backpressure, bypass=bypass_backpressure)

        job = create_pipeline_job(
            request,
            file_locator=self._file_locator,
            tuner=self._tuner,
            user_id=user_id,
            user_role=user_role,
            event_observer=self._store_event,
        )

        with self._lock:
            self._jobs[job.job_id] = job
            self._register_job_handler(job.job_id, job)
            self._store.save(self._persistence.snapshot(job))

        if job.tuning_summary and job.tracker:
            job.tracker.publish_progress({"stage": "configuration", **job.tuning_summary})

        with log_mgr.log_context(job_id=job.job_id, correlation_id=request.correlation_id):
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

        self._executor.submit(self._dispatch_execution, job.job_id)

        if self._backpressure is not None:
            self._backpressure.record_submission()

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
        bypass_backpressure: bool = False,
    ) -> PipelineJob:
        """Register a non-pipeline job for asynchronous execution."""

        apply_backpressure(self._backpressure, bypass=bypass_backpressure)

        job = create_background_job(
            job_type=job_type,
            file_locator=self._file_locator,
            tracker=tracker,
            stop_event=stop_event,
            request_payload=request_payload,
            user_id=user_id,
            user_role=user_role,
            setup=setup,
            event_observer=self._store_event,
        )

        with self._lock:
            self._jobs[job.job_id] = job
            self._custom_workers[job.job_id] = worker
            self._register_job_handler(job.job_id, job)
            snapshot = self._persistence.snapshot(job)
            self._store.save(snapshot)

        log_generic_job_submitted(job)
        self._executor.submit(self._dispatch_execution, job.job_id)

        if self._backpressure is not None:
            self._backpressure.record_submission()

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
            media_metadata = base_payload.get("media_metadata") or base_payload.get("book_metadata")
            if not isinstance(media_metadata, dict):
                media_metadata = {}
            media_metadata.update(metadata)
            base_payload["media_metadata"] = media_metadata
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
        self._assert_job_access(job, user_id=user_id, user_role=user_role, permission="edit")

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
        stage = metadata.get("stage")
        has_generated = metadata.get("generated_files") is not None
        event_sig = (
            event.event_type,
            event.snapshot.completed,
            event.snapshot.total,
            stage,
            has_generated,
        )

        with self._job_locks.job_lock(job_id):
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return

            last_sig = self._last_event_sig.get(job_id)
            is_terminal = event.event_type in ("complete", "error")
            if last_sig == event_sig and not is_terminal and not has_generated:
                job.last_event = event
                return

            self._last_event_sig[job_id] = event_sig

            if job.status == PipelineJobStatus.RUNNING:
                resume_context = compute_resume_context(job)
                if resume_context is not None:
                    job.resume_context = resume_context
            snapshot = self._persistence.apply_event(job, event)
            self._store.update(snapshot)

        correlation_id = _job_correlation_id(job) if job is not None else None
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
        try:
            handler(job_id)
        finally:
            if self._backpressure is not None:
                self._backpressure.record_completion()

    # Wrapper methods for logging to maintain backward compatibility
    def _log_job_started(self, job: PipelineJob) -> None:
        log_job_started(job)

    def _log_job_finished(self, job: PipelineJob, status: PipelineJobStatus) -> None:
        log_job_finished(job, status)
        # Send push notification for terminal states
        self._dispatch_job_notification(job, status)

    def _log_job_error(self, job: PipelineJob, exc: Exception) -> None:
        log_job_error(job, exc)

    def _log_job_interrupted(self, job: PipelineJob, status: PipelineJobStatus) -> None:
        log_job_interrupted(job, status)

    def _pipeline_operation_context(self, job: PipelineJob):
        return pipeline_operation_context(job)

    def _record_job_metric(self, name: str, value: float, attributes: Mapping[str, str]) -> None:
        record_job_metric(name, value, dict(attributes))

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

        log_generic_job_started(job)

        try:
            worker(job)
        except Exception as exc:
            with self._lock:
                job.status = PipelineJobStatus.FAILED
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                snapshot = self._persistence.snapshot(job)
            self._store.update(snapshot)
            if job.tracker is not None:
                job.tracker.record_error(exc, {"stage": job.job_type})
            log_generic_job_error(job, exc)
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
            log_generic_job_finished(job, job.status)
            # Send push notification for custom job completion
            self._dispatch_job_notification(job, job.status)
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
        log_generic_job_error(job, RuntimeError(message))

    @staticmethod
    def _is_admin(user_role: Optional[str]) -> bool:
        return is_admin_role(user_role)

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
            except Exception:
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
            except Exception:
                logger.debug("Failed to load job metadata from %s", path, exc_info=True)
                continue

        return None

    def _assert_job_access(
        self,
        job: PipelineJob,
        *,
        user_id: Optional[str],
        user_role: Optional[str],
        permission: str = "view",
    ) -> None:
        default_visibility = "private" if job.user_id else "public"
        policy = resolve_access_policy(job.access, default_visibility=default_visibility)
        if can_access(
            policy,
            owner_id=job.user_id,
            user_id=user_id,
            user_role=user_role,
            permission=permission,
        ):
            return
        if permission == "edit":
            raise PermissionError("Not authorized to modify this job")
        raise PermissionError("Not authorized to access this job")

    def get(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        permission: str = "view",
    ) -> PipelineJob:
        """Return the job associated with ``job_id``."""

        job = self._get_unchecked(job_id)
        self._assert_job_access(
            job, user_id=user_id, user_role=user_role, permission=permission
        )
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
            except Exception:
                logger.debug("Unable to clean generated path %s for job %s", path, job_id, exc_info=True)
        for path in (media_root, metadata_root, subtitles_root):
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
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
        self._assert_job_access(job, user_id=user_id, user_role=user_role, permission="edit")

        if job.job_type not in {"pipeline", "book"}:
            raise ValueError(f"Restart is not supported for job type '{job.job_type}'")
        if job.status in (PipelineJobStatus.RUNNING, PipelineJobStatus.PENDING):
            raise ValueError(f"Cannot restart job {job_id} while it is {job.status.value}")

        payload = job.request_payload or job.resume_context
        if payload is None:
            raise ValueError(f"Job {job_id} is missing request payload and cannot be restarted")

        previous_status = job.status

        self._cleanup_generated_outputs(job_id)

        with self._lock:
            job.request = None
            job.tracker = None
            job.stop_event = None
            job.last_event = None
            job.result = None
            job.result_payload = None
            job.error_message = None
            job.generated_files = None
            job.media_completed = False
            job.started_at = None
            job.completed_at = None
            job.status = PipelineJobStatus.PENDING

        stop_event = threading.Event()
        request = self._request_factory.hydrate_request(job, payload, stop_event=stop_event)

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
        self._last_event_sig.pop(job_id, None)
        self._job_locks.remove_job_lock(job_id)
        job_root = self._file_locator.job_root(job.job_id)
        try:
            shutil.rmtree(job_root)
        except FileNotFoundError:
            pass
        except OSError:
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

    def count(
        self,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> int:
        """Return total number of jobs visible to the user."""

        if self._is_admin(user_role):
            return self._store.count()
        return len(self.list(user_id=user_id, user_role=user_role))

    def list(
        self,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, PipelineJob]:
        """Return a snapshot mapping of jobs respecting role-based visibility."""

        if self._is_admin(user_role) and (offset is not None or limit is not None):
            stored = self._store.list(offset=offset, limit=limit)
        else:
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
                self._last_event_sig.pop(job_id, None)
                self._job_locks.remove_job_lock(job_id)
        for job_id, metadata in stored.items():
            active_jobs.setdefault(job_id, self._persistence.build_job(metadata))

        if self._is_admin(user_role):
            return active_jobs

        filtered: Dict[str, PipelineJob] = {}
        for job_id, job in active_jobs.items():
            default_visibility = "private" if job.user_id else "public"
            policy = resolve_access_policy(job.access, default_visibility=default_visibility)
            if can_access(
                policy,
                owner_id=job.user_id,
                user_id=user_id,
                user_role=user_role,
                permission="view",
            ):
                filtered[job_id] = job

        if offset is not None or limit is not None:
            items = list(filtered.items())
            start = offset or 0
            end = start + limit if limit is not None else None
            filtered = dict(items[start:end])

        return filtered

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
        self._assert_job_access(job, user_id=user_id, user_role=user_role, permission="edit")

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

    def enrich_metadata(
        self,
        job_id: str,
        *,
        force: bool = False,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> Tuple[PipelineJob, Dict[str, Any]]:
        """Enrich metadata for ``job_id`` from external sources.

        This method only performs external metadata lookup using the unified
        metadata pipeline. It does not re-extract metadata from the source file.

        Args:
            job_id: The job identifier.
            force: Force refresh even if enrichment data already exists.
            user_id: User requesting the enrichment.
            user_role: Role of the user.

        Returns:
            Tuple of (updated job, enrichment info dict).
        """
        with self._lock:
            job = self._jobs.get(job_id)

        if job is None:
            stored_metadata = self._store.get(job_id)
            job = self._persistence.build_job(stored_metadata)
        self._assert_job_access(job, user_id=user_id, user_role=user_role, permission="edit")

        if job.job_type not in {"pipeline", "book"}:
            raise ValueError(f"Metadata enrichment is not available for job type '{job.job_type}'")

        result = self._metadata_refresher.enrich(job, force=force)

        enrichment_info = {
            "enriched": result.enriched,
            "confidence": result.confidence,
            "source": (
                result.source_result.primary_source.value
                if result.source_result and result.source_result.primary_source
                else None
            ),
            "metadata": result.metadata,
        }

        if result.enriched:
            with log_mgr.log_context(job_id=job_id):
                logger.info(
                    "Pipeline job metadata enriched from %s (confidence: %s)",
                    enrichment_info["source"],
                    enrichment_info["confidence"],
                    extra={
                        "event": "pipeline.job.metadata.enriched",
                        "console_suppress": True,
                    },
                )

            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = job
                self._store.update(self._persistence.snapshot(job))

        return job, enrichment_info

    def shutdown(self, *, wait: bool = True) -> None:
        """Shutdown the manager and release all resources."""

        try:
            self._executor.shutdown(wait=wait)
        except Exception:
            pass

        try:
            self._tuner.shutdown()
        except Exception:
            pass

        if hasattr(self._storage, "shutdown"):
            try:
                self._storage.shutdown()
            except Exception:
                pass

    @property
    def pool_cache_stats(self) -> dict:
        """Return statistics about the worker pool cache."""
        return self._tuner.pool_cache_stats

    @property
    def backpressure_state(self) -> Optional[BackpressureState]:
        """Return current backpressure state, or None if disabled."""
        if self._backpressure is None:
            return None
        return self._backpressure.get_state()

    @property
    def is_accepting_jobs(self) -> bool:
        """Return True if the manager is accepting new job submissions."""
        if self._backpressure is None:
            return True
        return self._backpressure.is_accepting()

    def update_backpressure_policy(self, policy: BackpressurePolicy) -> None:
        """Update the backpressure policy at runtime."""
        if self._backpressure is not None:
            self._backpressure.update_policy(policy)

    def set_notification_callback(
        self,
        callback: Callable[[str, str, Optional[str], str], Awaitable[None]],
    ) -> None:
        """Set the callback for job completion notifications.

        The callback receives: (user_id, job_id, job_label, status).
        """
        self._notification_callback = callback

    def _dispatch_job_notification(
        self,
        job: PipelineJob,
        status: PipelineJobStatus,
    ) -> None:
        """Dispatch a push notification for job completion."""
        if self._notification_callback is None:
            return

        # Only notify for terminal states
        if status not in (
            PipelineJobStatus.COMPLETED,
            PipelineJobStatus.FAILED,
        ):
            return

        # Only notify if the job has an associated user
        if not job.user_id:
            return

        # Extract job label and metadata from result payload if available
        job_label: Optional[str] = None
        subtitle: Optional[str] = None
        cover_url: Optional[str] = None
        input_language: Optional[str] = None
        target_language: Optional[str] = None
        chapter_count: Optional[int] = None
        sentence_count: Optional[int] = None

        if job.result_payload:
            job_label = job.result_payload.get("title")
            media_metadata = job.result_payload.get("media_metadata") or job.result_payload.get("book_metadata")
            if isinstance(media_metadata, dict):
                if not job_label:
                    job_label = media_metadata.get("title")
                # Extract author as subtitle
                subtitle = media_metadata.get("author")
                # Check if job has a cover asset - use the public storage endpoint
                cover_asset = media_metadata.get("job_cover_asset")
                if isinstance(cover_asset, str) and cover_asset:
                    # Extract just the filename if it's a path
                    cover_filename = cover_asset.rsplit("/", 1)[-1]
                    cover_url = f"/api/storage/covers/{cover_filename}"
                # Extract language metadata
                input_language = media_metadata.get("input_language")
                target_language = media_metadata.get("target_language")
                # Extract chapter and sentence counts
                content_index_summary = media_metadata.get("content_index_summary")
                if isinstance(content_index_summary, dict):
                    chapter_count = content_index_summary.get("chapter_count")
                sentence_count = media_metadata.get("book_sentence_count") or media_metadata.get("total_sentences")

        # Schedule the async notification in a background task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._notification_callback(
                        job.user_id,
                        job.job_id,
                        job_label,
                        status.value,
                        subtitle=subtitle,
                        cover_url=cover_url,
                        input_language=input_language,
                        target_language=target_language,
                        chapter_count=chapter_count,
                        sentence_count=sentence_count,
                    )
                )
            else:
                # If no event loop is running, try to get or create one
                loop.run_until_complete(
                    self._notification_callback(
                        job.user_id,
                        job.job_id,
                        job_label,
                        status.value,
                        subtitle=subtitle,
                        cover_url=cover_url,
                        input_language=input_language,
                        target_language=target_language,
                        chapter_count=chapter_count,
                        sentence_count=sentence_count,
                    )
                )
        except RuntimeError:
            # No event loop available (running in sync context)
            try:
                asyncio.run(
                    self._notification_callback(
                        job.user_id,
                        job.job_id,
                        job_label,
                        status.value,
                        subtitle=subtitle,
                        cover_url=cover_url,
                        input_language=input_language,
                        target_language=target_language,
                        chapter_count=chapter_count,
                        sentence_count=sentence_count,
                    )
                )
            except Exception as e:
                logger.debug(
                    "Failed to dispatch job notification: %s",
                    e,
                    exc_info=True,
                )
