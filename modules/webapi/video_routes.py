"""HTTP routes for managing standalone video rendering jobs."""

from __future__ import annotations

import time
from typing import Any, Mapping
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from modules import logging_manager as log_mgr
from modules.observability import record_metric
from modules.video.api import VideoService
from modules.video.jobs import VideoJobManager

from .dependencies import get_video_job_manager, get_video_service
from .schemas import (
    VideoJobStatusResponse,
    VideoJobSubmissionResponse,
    VideoRenderRequestPayload,
)


router = APIRouter(prefix="/api/video", tags=["video"])
logger = log_mgr.get_logger().getChild("webapi.video")


def _resolve_renderer_name(video_service: VideoService) -> str:
    try:
        renderer = video_service.renderer
    except Exception:  # pragma: no cover - defensive logging helper
        return getattr(video_service, "_backend_name", "unknown")
    return getattr(renderer, "name", renderer.__class__.__name__)


def _metric_attributes(base: Mapping[str, Any]) -> Mapping[str, Any]:
    return {key: base[key] for key in base if key in {"backend", "slides", "audio_tracks"}}


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=VideoJobSubmissionResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "The provided payload was invalid or incomplete.",
        },
    },
)
def submit_video_job(
    payload: VideoRenderRequestPayload,
    request: Request,
    job_manager: VideoJobManager = Depends(get_video_job_manager),
    video_service: VideoService = Depends(get_video_service),
) -> VideoJobSubmissionResponse:
    """Queue a video rendering request for asynchronous processing."""

    correlation_id = (
        request.headers.get("x-request-id")
        or request.headers.get("x-correlation-id")
        or str(uuid4())
    )
    backend_name = _resolve_renderer_name(video_service)
    request_details = {
        "backend": backend_name,
        "slides": len(payload.slides),
        "audio_tracks": len(payload.audio),
        "path": request.url.path,
    }

    with log_mgr.log_context(
        correlation_id=correlation_id, stage="api.video.submit"
    ):
        logger.info(
            "Video job submission received",
            extra={
                "event": "video.job.submit.request",
                "attributes": request_details,
            },
        )
        record_metric(
            "video.job.submit.requests",
            1.0,
            _metric_attributes(request_details),
        )
        start = time.perf_counter()
    try:
        task = payload.to_task(job_manager.locator)
    except ValueError as exc:  # pragma: no cover - validated in tests
        duration_ms = (time.perf_counter() - start) * 1000.0
        record_metric(
            "video.job.submit.duration_ms",
            duration_ms,
            {**_metric_attributes(request_details), "status": "error"},
        )
        record_metric(
            "video.job.submit.failures",
            1.0,
            _metric_attributes(request_details),
        )
        logger.warning(
            "Video job submission rejected",
            extra={
                "event": "video.job.submit.validation_failed",
                "duration_ms": round(duration_ms, 2),
                "attributes": request_details,
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    job = job_manager.submit(task, video_service=video_service)
    duration_ms = (time.perf_counter() - start) * 1000.0
    record_metric(
        "video.job.submit.duration_ms",
        duration_ms,
        {**_metric_attributes(request_details), "status": "success"},
    )
    record_metric(
        "video.job.submit.success",
        1.0,
        _metric_attributes(request_details),
    )
    logger.info(
        "Video job submission accepted",
        extra={
            "event": "video.job.submit.success",
            "duration_ms": round(duration_ms, 2),
            "attributes": {**request_details, "job_id": job.job_id},
        },
    )
    return VideoJobSubmissionResponse.from_job(job)


@router.get(
    "/{job_id}",
    response_model=VideoJobStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Requested job could not be found."}
    },
)
def get_video_job_status(
    job_id: str,
    request: Request,
    job_manager: VideoJobManager = Depends(get_video_job_manager),
) -> VideoJobStatusResponse:
    """Return the current status for ``job_id``."""

    correlation_id = (
        request.headers.get("x-request-id")
        or request.headers.get("x-correlation-id")
        or str(uuid4())
    )

    with log_mgr.log_context(
        correlation_id=correlation_id, stage="api.video.status"
    ):
        start = time.perf_counter()
        logger.info(
            "Video job status requested",
            extra={
                "event": "video.job.status.request",
                "attributes": {"job_id": job_id, "path": request.url.path},
            },
        )
        job = job_manager.get(job_id)
        duration_ms = (time.perf_counter() - start) * 1000.0
        if job is None:
            record_metric(
                "video.job.status.duration_ms",
                duration_ms,
                {"status": "not_found"},
            )
            record_metric("video.job.status.not_found", 1.0, {})
            logger.warning(
                "Video job not found",
                extra={
                    "event": "video.job.status.not_found",
                    "duration_ms": round(duration_ms, 2),
                    "attributes": {"job_id": job_id, "path": request.url.path},
                },
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
            )

        record_metric(
            "video.job.status.duration_ms",
            duration_ms,
            {"status": job.status.value},
        )
        record_metric(
            "video.job.status.success",
            1.0,
            {"status": job.status.value},
        )
        logger.info(
            "Video job status returned",
            extra={
                "event": "video.job.status.success",
                "duration_ms": round(duration_ms, 2),
                "attributes": {
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "has_result": job.result is not None,
                },
            },
        )
        return VideoJobStatusResponse.from_job(job)


__all__ = ["router"]
