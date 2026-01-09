"""Schemas for video job submissions and status payloads."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel

from ...video.jobs import VideoJob, VideoJobResult, VideoJobStatus
from .progress import ProgressEventPayload, ProgressSnapshotPayload


class VideoJobResultPayload(BaseModel):
    """Serializable representation of :class:`VideoJobResult`."""

    path: str
    relative_path: str
    url: str | None = None

    @classmethod
    def from_result(cls, result: VideoJobResult) -> "VideoJobResultPayload":
        return cls(
            path=str(result.path),
            relative_path=result.relative_path,
            url=result.url,
        )


class VideoJobSubmissionResponse(BaseModel):
    """Response payload returned after submitting a video job."""

    job_id: str
    status: VideoJobStatus
    created_at: datetime

    @classmethod
    def from_job(cls, job: VideoJob) -> "VideoJobSubmissionResponse":
        return cls(job_id=job.job_id, status=job.status, created_at=job.created_at)


class VideoJobStatusResponse(BaseModel):
    """Detailed status payload describing an individual video job."""

    job_id: str
    status: VideoJobStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    progress: ProgressSnapshotPayload
    latest_event: ProgressEventPayload | None
    result: VideoJobResultPayload | None = None
    generated_files: Dict[str, Any] | None = None

    @classmethod
    def from_job(cls, job: VideoJob) -> "VideoJobStatusResponse":
        result_payload = None
        if job.result is not None:
            result_payload = VideoJobResultPayload.from_result(job.result)

        latest_event = (
            ProgressEventPayload.from_event(job.last_event)
            if job.last_event is not None
            else None
        )

        generated_files = copy.deepcopy(job.generated_files) if job.generated_files else None

        return cls(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error,
            progress=ProgressSnapshotPayload.from_snapshot(job.tracker.snapshot()),
            latest_event=latest_event,
            result=result_payload,
            generated_files=generated_files,
        )
