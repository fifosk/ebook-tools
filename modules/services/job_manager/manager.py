"""High-level orchestration utilities for pipeline jobs."""

from __future__ import annotations

import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional
from uuid import uuid4

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ... import metadata_manager
from ... import observability
from ...progress_tracker import ProgressEvent, ProgressTracker
from ...translation_engine import ThreadWorkerPool
from ..file_locator import FileLocator
from ..pipeline_service import (
    PipelineInput,
    PipelineRequest,
    serialize_pipeline_request,
    serialize_pipeline_response,
)
from ..pipeline_types import PipelineMetadata
from .job import PipelineJob, PipelineJobStatus, PipelineJobTransitionError
from .lifecycle import (
    apply_pause_transition,
    apply_resume_transition,
    compute_resume_context,
)
from .metadata import PipelineJobMetadata
from .progress import deserialize_progress_event, serialize_progress_event
from .job_storage import JobStorageCoordinator
from .job_tuner import PipelineJobTuner
from .stores import JobStore
from .execution_adapter import PipelineExecutionAdapter

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
        self._restore_persisted_jobs()

    def _restore_persisted_jobs(self) -> None:
        """Load persisted jobs and reconcile their in-memory representation."""

        stored_jobs = self._storage.load_all()

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

        self._storage.persist_reconciliation(updates)

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "on"}:
                return True
            if normalized in {"false", "0", "no", "n", "off"}:
                return False
        return bool(value)

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _build_pipeline_input(self, payload: Mapping[str, Any]) -> PipelineInput:
        data = dict(payload or {})
        raw_targets = data.get("target_languages") or []
        if isinstance(raw_targets, list):
            target_languages = [str(item) for item in raw_targets]
        elif isinstance(raw_targets, (tuple, set)):
            target_languages = [str(item) for item in raw_targets]
        elif raw_targets is None:
            target_languages = []
        else:
            target_languages = [str(raw_targets)]

        end_sentence_value = data.get("end_sentence")
        end_sentence = None
        if end_sentence_value is not None:
            try:
                end_sentence = int(end_sentence_value)
            except (TypeError, ValueError):
                end_sentence = None

        book_metadata = data.get("book_metadata")
        if not isinstance(book_metadata, Mapping):
            book_metadata = {}

        return PipelineInput(
            input_file=str(data.get("input_file") or ""),
            base_output_file=str(data.get("base_output_file") or ""),
            input_language=str(data.get("input_language") or ""),
            target_languages=target_languages,
            sentences_per_output_file=self._coerce_int(data.get("sentences_per_output_file"), 1),
            start_sentence=self._coerce_int(data.get("start_sentence"), 1),
            end_sentence=end_sentence,
            stitch_full=self._coerce_bool(data.get("stitch_full")),
            generate_audio=self._coerce_bool(data.get("generate_audio")),
            audio_mode=str(data.get("audio_mode") or ""),
            written_mode=str(data.get("written_mode") or ""),
            selected_voice=str(data.get("selected_voice") or ""),
            output_html=self._coerce_bool(data.get("output_html")),
            output_pdf=self._coerce_bool(data.get("output_pdf")),
            generate_video=self._coerce_bool(data.get("generate_video")),
            include_transliteration=self._coerce_bool(data.get("include_transliteration")),
            tempo=self._coerce_float(data.get("tempo"), 1.0),
            book_metadata=PipelineMetadata.from_mapping(book_metadata),
        )

    def _hydrate_request_from_payload(
        self,
        job: PipelineJob,
        payload: Mapping[str, Any],
        stop_event: threading.Event,
    ) -> PipelineRequest:
        config = dict(payload.get("config") or {})
        environment_overrides = dict(payload.get("environment_overrides") or {})
        pipeline_overrides = dict(payload.get("pipeline_overrides") or {})
        inputs_payload = payload.get("inputs")
        if not isinstance(inputs_payload, Mapping):
            inputs_payload = {}

        tracker = job.tracker or ProgressTracker()
        if job.tracker is None:
            tracker.register_observer(lambda event: self._store_event(job.job_id, event))
            job.tracker = tracker

        correlation_id = payload.get("correlation_id")
        if correlation_id is None and job.request is not None:
            correlation_id = job.request.correlation_id

        request = PipelineRequest(
            config=config,
            context=job.request.context if job.request is not None else None,
            environment_overrides=environment_overrides,
            pipeline_overrides=pipeline_overrides,
            inputs=self._build_pipeline_input(inputs_payload),
            progress_tracker=tracker,
            stop_event=stop_event,
            translation_pool=None,
            correlation_id=correlation_id,
            job_id=job.job_id,
        )

        return request

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
            user_id=job.user_id,
            user_role=job.user_role,
        )

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

        job_output_dir = self._file_locator.resolve_path(job_id)
        job_output_dir.mkdir(parents=True, exist_ok=True)

        environment_overrides = dict(request.environment_overrides)
        environment_overrides.setdefault("output_dir", str(job_output_dir))
        job_storage_url = self._file_locator.resolve_url(job_id)
        if job_storage_url:
            environment_overrides.setdefault("job_storage_url", job_storage_url)
        request.environment_overrides = environment_overrides

        context = request.context
        if context is not None:
            context = dataclass_replace(context, output_dir=job_output_dir)
        else:
            context = cfg.build_runtime_context(
                dict(request.config),
                dict(environment_overrides),
            )
            context = dataclass_replace(context, output_dir=job_output_dir)
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

    def _execute(self, job_id: str) -> None:
        try:
            job = self.get(job_id)
        except KeyError:
            return

        with self._lock:
            job.status = PipelineJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            self._store.update(self._snapshot(job))

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
                pool, owns_pool = self._tuner.acquire_worker_pool(job)
                if job.tuning_summary is not None:
                    with self._lock:
                        self._store.update(self._snapshot(job))
                job.owns_translation_pool = owns_pool
                response = self._execution.execute(job.request)
            with self._lock:
                current_status = job.status
                if current_status == PipelineJobStatus.PAUSED:
                    job.result = None
                    job.result_payload = None
                    job.error_message = None
                elif current_status == PipelineJobStatus.CANCELLED:
                    job.result = None
                    job.result_payload = None
                    job.error_message = None
                else:
                    job.result = response
                    job.result_payload = serialize_pipeline_response(response)
                    job.status = (
                        PipelineJobStatus.COMPLETED
                        if response.success
                        else PipelineJobStatus.FAILED
                    )
                    job.error_message = (
                        None if response.success else "Pipeline execution reported failure."
                    )
        except Exception as exc:  # pragma: no cover - defensive logging
            with self._lock:
                interruption = job.status in (
                    PipelineJobStatus.PAUSED,
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
                with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
                    logger.error(
                        "Pipeline job encountered an error",
                        extra={
                            "event": "pipeline.job.error",
                            "status": PipelineJobStatus.FAILED.value,
                            "attributes": {"error": str(exc)},
                        },
                    )
                if job.tracker is not None:
                    job.tracker.record_error(exc, {"stage": "pipeline"})
            else:
                with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
                    logger.info(
                        "Pipeline job interrupted",
                        extra={
                            "event": "pipeline.job.interrupted",
                            "status": status_after_error.value,
                            "console_suppress": True,
                        },
                    )
        finally:
            pool_to_shutdown: Optional[ThreadWorkerPool] = None
            with self._lock:
                status = job.status
                if job.owns_translation_pool and job.request is not None:
                    pool_to_shutdown = job.request.translation_pool
                    job.request.translation_pool = None
                job.owns_translation_pool = False
                terminal_states = {
                    PipelineJobStatus.COMPLETED,
                    PipelineJobStatus.FAILED,
                    PipelineJobStatus.CANCELLED,
                }
                if status in terminal_states:
                    job.completed_at = job.completed_at or datetime.now(timezone.utc)
                snapshot = self._snapshot(job)
            self._store.update(snapshot)
            if pool_to_shutdown is not None:
                try:
                    pool_to_shutdown.shutdown()
                except Exception:  # pragma: no cover - defensive logging
                    logger.debug(
                        "Translation worker pool shutdown raised an exception",
                        exc_info=True,
                    )
            if job.tracker is not None:
                if status == PipelineJobStatus.COMPLETED:
                    job.tracker.mark_finished(reason="completed", forced=False)
                elif status == PipelineJobStatus.FAILED:
                    job.tracker.mark_finished(reason="failed", forced=True)
                elif status == PipelineJobStatus.CANCELLED:
                    job.tracker.mark_finished(reason="cancelled", forced=True)
            with log_mgr.log_context(job_id=job_id, correlation_id=correlation_id):
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
                    if status in terminal_states:
                        duration_ms = 0.0
                        if job.started_at and job.completed_at:
                            duration_ms = (
                                job.completed_at - job.started_at
                            ).total_seconds() * 1000.0
                        observability.record_metric(
                            "pipeline.job.duration",
                            duration_ms,
                            {"job_id": job_id, "status": status.value},
                        )

    @staticmethod
    def _is_admin(user_role: Optional[str]) -> bool:
        return bool(user_role and user_role.lower() == "admin")

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

        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                self._assert_job_access(job, user_id=user_id, user_role=user_role)
                return job
        metadata = self._store.get(job_id)
        job = self._build_job_from_metadata(metadata)
        self._assert_job_access(job, user_id=user_id, user_role=user_role)
        return job

    def _mutate_job(
        self,
        job_id: str,
        mutator: Callable[[PipelineJob], None],
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Apply ``mutator`` to ``job_id`` and persist the resulting state."""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                metadata = self._store.get(job_id)
                job = self._build_job_from_metadata(metadata)
            self._assert_job_access(job, user_id=user_id, user_role=user_role)
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

    def pause_job(
        self,
        job_id: str,
        *,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> PipelineJob:
        """Mark ``job_id`` as paused and persist the updated status."""

        def _pause(job: PipelineJob) -> None:
            apply_pause_transition(job)
            event = job.stop_event
            if event is None and job.request is not None:
                event = job.request.stop_event
            if event is None:
                event = threading.Event()
            event.set()
            job.stop_event = event
            if job.request is not None:
                job.request.stop_event = event

        return self._mutate_job(
            job_id,
            _pause,
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

        def _resume(job: PipelineJob) -> None:
            apply_resume_transition(job)
            payload = job.resume_context or job.request_payload
            if payload is None:
                raise ValueError(
                    f"Job {job.job_id} is missing resume context and cannot be resumed"
                )
            stop_event = threading.Event()
            request = self._hydrate_request_from_payload(job, payload, stop_event)
            job.request = request
            job.stop_event = stop_event
            job.request.stop_event = stop_event
            job.result = None
            job.result_payload = None
            job.error_message = None
            job.started_at = None
            job.completed_at = None
            job.owns_translation_pool = False
            if job.request is not None:
                job.request.translation_pool = None

        job = self._mutate_job(
            job_id,
            _resume,
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

        def _cancel(job: PipelineJob) -> None:
            if job.status in (
                PipelineJobStatus.COMPLETED,
                PipelineJobStatus.FAILED,
                PipelineJobStatus.CANCELLED,
            ):
                raise ValueError(
                    f"Cannot cancel job {job.job_id} in terminal state {job.status.value}"
                )
            event = job.stop_event
            if event is None and job.request is not None:
                event = job.request.stop_event
            if event is None:
                event = threading.Event()
            event.set()
            job.stop_event = event
            if job.request is not None:
                job.request.stop_event = event
            job.status = PipelineJobStatus.CANCELLED
            job.completed_at = job.completed_at or datetime.now(timezone.utc)

        return self._mutate_job(
            job_id,
            _cancel,
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

        self._assert_job_access(job, user_id=user_id, user_role=user_role)
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
            user_id=metadata.user_id,
            user_role=metadata.user_role,
        )
        if metadata.last_event is not None:
            job.last_event = deserialize_progress_event(metadata.last_event)
        return job

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
            active_jobs.setdefault(job_id, self._build_job_from_metadata(metadata))

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
            metadata = self._store.get(job_id)
            job = self._build_job_from_metadata(metadata)
        self._assert_job_access(job, user_id=user_id, user_role=user_role)

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
            job.request.inputs.book_metadata = PipelineMetadata.from_mapping(metadata)
        job.request_payload = request_payload
        job.resume_context = copy.deepcopy(request_payload)

        if job.result is not None:
            job.result.metadata = PipelineMetadata.from_mapping(metadata)
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
