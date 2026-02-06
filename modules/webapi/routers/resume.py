"""Routes for playback resume position storage."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import RequestUserContext, get_resume_service, get_request_user
from ..schemas.resume import (
    ResumePositionDeleteResponse,
    ResumePositionEntry,
    ResumePositionPayload,
    ResumePositionResponse,
)
from ...services.resume_service import ResumeService


router = APIRouter(prefix="/api/resume", tags=["resume"])


def _require_user(request_user: RequestUserContext) -> str:
    if not request_user.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    return request_user.user_id


@router.get("/{job_id}", response_model=ResumePositionResponse)
def get_resume_position(
    job_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumePositionResponse:
    user_id = _require_user(request_user)
    entry = resume_service.get(job_id, user_id)
    entry_payload = ResumePositionEntry(**entry.__dict__) if entry else None
    return ResumePositionResponse(job_id=job_id, entry=entry_payload)


@router.put("/{job_id}", response_model=ResumePositionResponse)
def save_resume_position(
    job_id: str,
    payload: ResumePositionPayload,
    request_user: RequestUserContext = Depends(get_request_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumePositionResponse:
    user_id = _require_user(request_user)
    entry = resume_service.save(job_id, user_id, payload.model_dump())
    return ResumePositionResponse(
        job_id=job_id,
        entry=ResumePositionEntry(**entry.__dict__),
    )


@router.delete("/{job_id}", response_model=ResumePositionDeleteResponse)
def delete_resume_position(
    job_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumePositionDeleteResponse:
    user_id = _require_user(request_user)
    deleted = resume_service.clear(job_id, user_id)
    return ResumePositionDeleteResponse(deleted=deleted)
