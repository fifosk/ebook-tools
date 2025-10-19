"""Job orchestration utilities for ebook-tools pipeline executions."""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Mapping, Optional, Protocol
from uuid import uuid4

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover - defensive import guard
    redis = None

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import metadata_manager
from .. import observability
from ..progress_tracker import ProgressEvent, ProgressSnapshot, ProgressTracker
from ..translation_engine import TranslationWorkerPool
from .pipeline_service import (
    PipelineRequest,
    PipelineResponse,
    run_pipeline,
    serialize_pipeline_request,
    serialize_pipeline_response,
)

logger = log_mgr.logger


class PipelineJobStatus(str, Enum):
    """Enumeration of possible job states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineJobMetadata:
    """Serializable metadata describing a pipeline job."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    last_event: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    request_payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        def _dt(value: Optional[datetime]) -> Optional[str]:
            return value.isoformat() if value is not None else None

        payload: Dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": _dt(self.created_at),
            "started_at": _dt(self.started_at),
            "completed_at": _dt(self.completed_at),
            "error_message": self.error_message,
            "last_event": self.last_event,
            "result": self.result,
        }
        if self.request_payload is not None:
            payload["request"] = self.request_payload
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PipelineJobMetadata":
        return cls(
            job_id=str(data["job_id"]),
            status=PipelineJobStatus(str(data["status"])),
            created_at=cls._parse_datetime(data.get("created_at")) or datetime.now(timezone.utc),
            started_at=cls._parse_datetime(data.get("started_at")),
            completed_at=cls._parse_datetime(data.get("completed_at")),
            error_message=data.get("error_message"),
            last_event=data.get("last_event"),
            result=data.get("result"),
            request_payload=data.get("request"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "PipelineJobMetadata":
        return cls.from_dict(json.loads(payload))


class JobStore(Protocol):
    """Persistence backend for job metadata."""

    def save(self, metadata: PipelineJobMetadata) -> None:
        ...

    def update(self, metadata: PipelineJobMetadata) -> None:
        ...

    def get(self, job_id: str) -> PipelineJobMetadata:
        ...

    def list(self) -> Dict[str, PipelineJobMetadata]:
        ...


class InMemoryJobStore(JobStore):
    """Simple process-local store used as a default fallback."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: Dict[str, PipelineJobMetadata] = {}

    def save(self, metadata: PipelineJobMetadata) -> None:
        with self._lock:
            self._records[metadata.job_id] = metadata

    def update(self, metadata: PipelineJobMetadata) -> None:
        with self._lock:
            self._records[metadata.job_id] = metadata

    def get(self, job_id: str) -> PipelineJobMetadata:
        with self._lock:
            try:
                return self._records[job_id]
            except KeyError as exc:
                raise KeyError(job_id) from exc

    def list(self) -> Dict[str, PipelineJobMetadata]:
        with self._lock:
            return dict(self._records)


class RedisJobStore(JobStore):
    """Redis-backed implementation of :class:`JobStore`."""

    def __init__(self, url: str, *, namespace: str = "ebook-tools:jobs") -> None:
        if redis is None:  # pragma: no cover - optional dependency
            raise RuntimeError("redis-py is not available; cannot use RedisJobStore")
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._namespace = namespace

    def _key(self, job_id: str) -> str:
        return f"{self._namespace}:{job_id}"

    def save(self, metadata: PipelineJobMetadata) -> None:
        self._client.set(self._key(metadata.job_id), metadata.to_json())

    def update(self, metadata: PipelineJobMetadata) -> None:
        self.save(metadata)

    def get(self, job_id: str) -> PipelineJobMetadata:
        payload = self._client.get(self._key(job_id))
        if payload is None:
            raise KeyError(job_id)
        return PipelineJobMetadata.from_json(payload)

    def list(self) -> Dict[str, PipelineJobMetadata]:
        records: Dict[str, PipelineJobMetadata] = {}
        cursor = 0
        pattern = f"{self._namespace}:*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern)
            for key in keys:
                payload = self._client.get(key)
                if payload is None:
                    continue
                job_id = key.split(":", 1)[-1]
                records[job_id] = PipelineJobMetadata.from_json(payload)
            if cursor == 0:
                break
        return records


@dataclass
class PipelineJob:
    """Container describing the state of an in-flight or completed pipeline execution."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime
    request: Optional[PipelineRequest] = None
    tracker: Optional[ProgressTracker] = None
    stop_event: Optional[threading.Event] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[PipelineResponse] = None
    error_message: Optional[str] = None
    last_event: Optional[ProgressEvent] = None
    result_payload: Optional[Dict[str, Any]] = None
    owns_translation_pool: bool = False
    request_payload: Optional[Dict[str, Any]] = None


def _serialize_progress_event(event: ProgressEvent) -> Dict[str, Any]:
    snapshot = event.snapshot
    return {
        "event_type": event.event_type,
        "timestamp": event.timestamp,
        "metadata": dict(event.metadata),
        "error": str(event.error) if event.error else None,
        "snapshot": {
            "completed": snapshot.completed,
            "total": snapshot.total,
            "elapsed": snapshot.elapsed,
            "speed": snapshot.speed,
            "eta": snapshot.eta,
        },
    }


def _deserialize_progress_event(payload: Mapping[str, Any]) -> ProgressEvent:
    snapshot_data = payload.get("snapshot", {})
    snapshot = ProgressSnapshot(
        completed=int(snapshot_data.get("completed", 0)),
        total=snapshot_data.get("total"),
        elapsed=float(snapshot_data.get("elapsed", 0.0)),
        speed=float(snapshot_data.get("speed", 0.0)),
        eta=snapshot_data.get("eta"),
    )
    error_message = payload.get("error")
    error: Optional[BaseException] = None
    if error_message:
        error = RuntimeError(str(error_message))
    metadata = dict(payload.get("metadata", {}))
    return ProgressEvent(
        event_type=str(payload.get("event_type", "progress")),
        snapshot=snapshot,
        timestamp=float(payload.get("timestamp", 0.0)),
        metadata=metadata,
        error=error,
    )


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
        resolved_workers = max(1, int(configured_workers))
        self._executor = ThreadPoolExecutor(max_workers=resolved_workers)
        self._store = store or self._default_store()
        self._worker_pool_factory = worker_pool_factory or (lambda request: TranslationWorkerPool())

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
        return InMemoryJobStore()

    def _snapshot(self, job: PipelineJob) -> PipelineJobMetadata:
        last_event = _serialize_progress_event(job.last_event) if job.last_event else None
        result_payload = job.result_payload
        if result_payload is None and job.result is not None:
            result_payload = serialize_pipeline_response(job.result)
        if job.request is not None:
            request_payload = serialize_pipeline_request(job.request)
        else:
            request_payload = dict(job.request_payload) if job.request_payload else None
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

        job = PipelineJob(
            job_id=job_id,
            status=PipelineJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            request=request,
            tracker=tracker,
            stop_event=stop_event,
            request_payload=serialize_pipeline_request(request),
        )

        tracker.register_observer(lambda event: self._store_event(job_id, event))

        with self._lock:
            self._jobs[job_id] = job
            self._store.save(self._snapshot(job))

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

    def _acquire_worker_pool(self, request: PipelineRequest) -> tuple[Optional[TranslationWorkerPool], bool]:
        if request.translation_pool is not None:
            return request.translation_pool, False
        pool = self._worker_pool_factory(request)
        request.translation_pool = pool
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
                pool, owns_pool = self._acquire_worker_pool(job.request)
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

    def _build_job_from_metadata(self, metadata: PipelineJobMetadata) -> PipelineJob:
        job = PipelineJob(
            job_id=metadata.job_id,
            status=metadata.status,
            created_at=metadata.created_at,
            started_at=metadata.started_at,
            completed_at=metadata.completed_at,
            error_message=metadata.error_message,
            result_payload=metadata.result,
            request_payload=metadata.request_payload,
        )
        if metadata.last_event is not None:
            job.last_event = _deserialize_progress_event(metadata.last_event)
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
