"""Routes for playback resume position storage."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules import logging_manager as log_mgr

from ..dependencies import RequestUserContext, get_resume_service, get_request_user
from ..route_telemetry import log_started_route_result
from ..schemas.resume import (
    ResumePositionDeleteResponse,
    ResumePositionEntry,
    ResumePositionListResponse,
    ResumePositionPayload,
    ResumePositionResponse,
)
from ...services.resume_service import ResumeService, normalize_resume_job_ids


router = APIRouter(prefix="/api/resume", tags=["resume"])
logger = log_mgr.get_logger()

RESUME_JOB_NOT_FOUND_MESSAGE = "Job not found"
RESUME_STORAGE_UNAVAILABLE_MESSAGE = "Unable to sync resume position."


def _log_resume_route_result(
    *,
    operation: str,
    result: str,
    started_at: float,
    entry_count: int | None = None,
    deleted: bool | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="RESUME_ROUTE_DURATION",
        message="Resume route",
        operation=operation,
        result=result,
        started_at=started_at,
        entries=entry_count,
        deleted=deleted,
    )


def _require_user(request_user: RequestUserContext) -> str:
    if not request_user.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    return request_user.user_id


def _normalize_route_id(value: str) -> str:
    return value.strip()


def _raise_missing_resume_target(*, operation: str, started_at: float) -> None:
    _log_resume_route_result(
        operation=operation,
        result="not_found",
        started_at=started_at,
    )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RESUME_JOB_NOT_FOUND_MESSAGE)


def _raise_resume_storage_unavailable(*, operation: str, started_at: float) -> None:
    _log_resume_route_result(
        operation=operation,
        result="error",
        started_at=started_at,
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=RESUME_STORAGE_UNAVAILABLE_MESSAGE,
    )


@router.get("", response_model=ResumePositionListResponse)
def list_resume_positions(
    job_id: list[str] | None = Query(default=None),
    request_user: RequestUserContext = Depends(get_request_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumePositionListResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_resume_route_result(
            operation="list",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    filtered_job_ids = None if job_id is None else normalize_resume_job_ids(job_id)
    if job_id is not None and not filtered_job_ids:
        _log_resume_route_result(
            operation="list",
            result="success",
            started_at=started_at,
            entry_count=0,
        )
        return ResumePositionListResponse(entries=[])
    try:
        entries = resume_service.list(user_id, job_ids=filtered_job_ids, limit=200)
    except Exception:
        _raise_resume_storage_unavailable(operation="list", started_at=started_at)
    _log_resume_route_result(
        operation="list",
        result="success",
        started_at=started_at,
        entry_count=len(entries),
    )
    return ResumePositionListResponse(
        entries=[ResumePositionEntry(**entry.__dict__) for entry in entries]
    )


@router.get("/{job_id}", response_model=ResumePositionResponse)
def get_resume_position(
    job_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumePositionResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_resume_route_result(
            operation="get",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    normalized_job_id = _normalize_route_id(job_id)
    if not normalized_job_id:
        _raise_missing_resume_target(operation="get", started_at=started_at)
    try:
        entry = resume_service.get(normalized_job_id, user_id)
    except Exception:
        _raise_resume_storage_unavailable(operation="get", started_at=started_at)
    entry_payload = ResumePositionEntry(**entry.__dict__) if entry else None
    _log_resume_route_result(
        operation="get",
        result="success",
        started_at=started_at,
        entry_count=1 if entry_payload else 0,
    )
    return ResumePositionResponse(job_id=normalized_job_id, entry=entry_payload)


@router.put("/{job_id}", response_model=ResumePositionResponse)
def save_resume_position(
    job_id: str,
    payload: ResumePositionPayload,
    request_user: RequestUserContext = Depends(get_request_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumePositionResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_resume_route_result(
            operation="save",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    normalized_job_id = _normalize_route_id(job_id)
    if not normalized_job_id:
        _raise_missing_resume_target(operation="save", started_at=started_at)
    try:
        entry = resume_service.save(normalized_job_id, user_id, payload.model_dump())
    except Exception:
        _raise_resume_storage_unavailable(operation="save", started_at=started_at)
    _log_resume_route_result(
        operation="save",
        result="success",
        started_at=started_at,
        entry_count=1,
    )
    return ResumePositionResponse(
        job_id=normalized_job_id,
        entry=ResumePositionEntry(**entry.__dict__),
    )


@router.delete("/{job_id}", response_model=ResumePositionDeleteResponse)
def delete_resume_position(
    job_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumePositionDeleteResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_resume_route_result(
            operation="delete",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    normalized_job_id = _normalize_route_id(job_id)
    if not normalized_job_id:
        _raise_missing_resume_target(operation="delete", started_at=started_at)
    try:
        deleted = resume_service.clear(normalized_job_id, user_id)
    except Exception:
        _raise_resume_storage_unavailable(operation="delete", started_at=started_at)
    _log_resume_route_result(
        operation="delete",
        result="success",
        started_at=started_at,
        deleted=deleted,
    )
    return ResumePositionDeleteResponse(deleted=deleted)
