"""In-memory representations of pipeline jobs."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from ..pipeline_service import PipelineRequest, PipelineResponse
from ...progress_tracker import ProgressEvent, ProgressTracker
from ...translation_engine import ThreadWorkerPool


class PipelineJobStatus(str, Enum):
    """Enumeration of possible job states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineJobTransitionError(ValueError):
    """Raised when an invalid state transition is requested for a job."""

    def __init__(self, job_id: str, job: "PipelineJob", message: str) -> None:
        super().__init__(message)
        self.job_id = job_id
        self.job = job


@dataclass
class PipelineJob:
    """Container describing the state of an in-flight or completed pipeline execution."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime
    request: Optional["PipelineRequest"] = None
    tracker: Optional["ProgressTracker"] = None
    stop_event: Optional[threading.Event] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional["PipelineResponse"] = None
    error_message: Optional[str] = None
    last_event: Optional["ProgressEvent"] = None
    result_payload: Optional[Dict[str, Any]] = None
    owns_translation_pool: bool = False
    request_payload: Optional[Dict[str, Any]] = None
    resume_context: Optional[Dict[str, Any]] = None
    tuning_summary: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    generated_files: Optional[Dict[str, Any]] = None


__all__ = [
    "PipelineJob",
    "PipelineJobStatus",
    "PipelineJobTransitionError",
]
