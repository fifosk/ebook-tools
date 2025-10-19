"""In-memory management of pipeline execution jobs."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from uuid import uuid4

from ..progress_tracker import ProgressEvent, ProgressTracker
from ..services.pipeline_service import PipelineRequest, PipelineResponse, run_pipeline


class PipelineJobStatus(str, Enum):
    """Enumeration of possible job states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineJob:
    """Container describing the state of an in-flight pipeline execution."""

    job_id: str
    request: PipelineRequest
    tracker: ProgressTracker
    stop_event: threading.Event
    status: PipelineJobStatus = PipelineJobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[PipelineResponse] = None
    error_message: Optional[str] = None
    last_event: Optional[ProgressEvent] = None


class PipelineJobManager:
    """Orchestrate background execution of pipeline jobs."""

    def __init__(self, max_workers: int = 2) -> None:
        self._jobs: Dict[str, PipelineJob] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, request: PipelineRequest) -> PipelineJob:
        """Register ``request`` for background execution."""

        job_id = str(uuid4())
        tracker = request.progress_tracker or ProgressTracker()
        request.progress_tracker = tracker
        stop_event = request.stop_event or threading.Event()
        request.stop_event = stop_event

        job = PipelineJob(job_id=job_id, request=request, tracker=tracker, stop_event=stop_event)
        tracker.register_observer(lambda event: self._store_event(job_id, event))

        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(self._execute, job_id)
        return job

    def get(self, job_id: str) -> PipelineJob:
        """Return the job associated with ``job_id``."""

        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def _store_event(self, job_id: str, event: ProgressEvent) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.last_event = event

    def _execute(self, job_id: str) -> None:
        try:
            job = self.get(job_id)
        except KeyError:
            return

        with self._lock:
            job.status = PipelineJobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

        try:
            response = run_pipeline(job.request)
            with self._lock:
                job.result = response
                job.status = (
                    PipelineJobStatus.COMPLETED
                    if response.success
                    else PipelineJobStatus.FAILED
                )
                job.error_message = None if response.success else "Pipeline execution reported failure."
        except Exception as exc:  # pragma: no cover - defensive logging
            with self._lock:
                job.result = None
                job.status = PipelineJobStatus.FAILED
                job.error_message = str(exc)
            job.tracker.record_error(exc, {"stage": "pipeline"})
        finally:
            with self._lock:
                job.completed_at = datetime.now(timezone.utc)
            result = job.result
            forced = not (result.success if isinstance(result, PipelineResponse) else False)
            reason = "completed" if not forced else "failed"
            job.tracker.mark_finished(reason=reason, forced=forced)

    def list(self) -> Dict[str, PipelineJob]:
        """Return a snapshot mapping of all jobs."""

        with self._lock:
            return dict(self._jobs)
