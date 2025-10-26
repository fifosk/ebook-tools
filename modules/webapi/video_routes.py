"""HTTP routes for managing standalone video rendering jobs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from modules.video.api import VideoService
from modules.video.jobs import VideoJobManager

from .dependencies import get_video_job_manager, get_video_service
from .schemas import (
    VideoJobStatusResponse,
    VideoJobSubmissionResponse,
    VideoRenderRequestPayload,
)


router = APIRouter(prefix="/api/video", tags=["video"])


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
    job_manager: VideoJobManager = Depends(get_video_job_manager),
    video_service: VideoService = Depends(get_video_service),
) -> VideoJobSubmissionResponse:
    """Queue a video rendering request for asynchronous processing."""

    try:
        task = payload.to_task(job_manager.locator)
    except ValueError as exc:  # pragma: no cover - validated in tests
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    job = job_manager.submit(task, video_service=video_service)
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
    job_manager: VideoJobManager = Depends(get_video_job_manager),
) -> VideoJobStatusResponse:
    """Return the current status for ``job_id``."""

    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return VideoJobStatusResponse.from_job(job)


__all__ = ["router"]
