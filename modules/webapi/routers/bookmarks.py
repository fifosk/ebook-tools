"""Routes for playback bookmark storage."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status

from modules import logging_manager as log_mgr

from ..dependencies import RequestUserContext, get_bookmark_service, get_request_user
from ..route_telemetry import log_started_route_result
from ..schemas.bookmarks import (
    PlaybackBookmarkDeleteResponse,
    PlaybackBookmarkEntry,
    PlaybackBookmarkListResponse,
    PlaybackBookmarkPayload,
)
from ...services.bookmark_service import BookmarkService


router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])
logger = log_mgr.get_logger()

BOOKMARK_JOB_NOT_FOUND_MESSAGE = "Job not found"
BOOKMARK_STORAGE_UNAVAILABLE_MESSAGE = "Unable to sync bookmarks."


def _log_bookmark_route_result(
    *,
    operation: str,
    result: str,
    started_at: float,
    bookmark_count: int | None = None,
    deleted: bool | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="BOOKMARK_ROUTE_DURATION",
        message="Bookmark route",
        operation=operation,
        result=result,
        started_at=started_at,
        bookmarks=bookmark_count,
        deleted=deleted,
    )


def _require_user(request_user: RequestUserContext) -> str:
    if not request_user.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    return request_user.user_id


def _normalize_route_id(value: str) -> str:
    return value.strip()


def _raise_missing_bookmark_target(
    *,
    operation: str,
    started_at: float,
) -> None:
    _log_bookmark_route_result(
        operation=operation,
        result="not_found",
        started_at=started_at,
    )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=BOOKMARK_JOB_NOT_FOUND_MESSAGE)


def _raise_bookmark_storage_unavailable(
    *,
    operation: str,
    started_at: float,
) -> None:
    _log_bookmark_route_result(
        operation=operation,
        result="error",
        started_at=started_at,
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=BOOKMARK_STORAGE_UNAVAILABLE_MESSAGE,
    )


@router.get("/{job_id}", response_model=PlaybackBookmarkListResponse)
def list_bookmarks(
    job_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
) -> PlaybackBookmarkListResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_bookmark_route_result(
            operation="list",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    normalized_job_id = _normalize_route_id(job_id)
    if not normalized_job_id:
        _raise_missing_bookmark_target(operation="list", started_at=started_at)
    try:
        entries = bookmark_service.list_bookmarks(normalized_job_id, user_id)
        payload = [PlaybackBookmarkEntry(**entry.__dict__) for entry in entries]
        response_payload = PlaybackBookmarkListResponse(
            job_id=normalized_job_id,
            bookmarks=payload,
        )
    except Exception:
        _raise_bookmark_storage_unavailable(operation="list", started_at=started_at)
    _log_bookmark_route_result(
        operation="list",
        result="success",
        started_at=started_at,
        bookmark_count=len(payload),
    )
    return response_payload


@router.post("/{job_id}", response_model=PlaybackBookmarkEntry)
def add_bookmark(
    job_id: str,
    payload: PlaybackBookmarkPayload,
    request_user: RequestUserContext = Depends(get_request_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
) -> PlaybackBookmarkEntry:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_bookmark_route_result(
            operation="add",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    normalized_job_id = _normalize_route_id(job_id)
    if not normalized_job_id:
        _raise_missing_bookmark_target(operation="add", started_at=started_at)
    try:
        entry = bookmark_service.add_bookmark(normalized_job_id, user_id, payload.model_dump())
        response_payload = PlaybackBookmarkEntry(**entry.__dict__)
    except Exception:
        _raise_bookmark_storage_unavailable(operation="add", started_at=started_at)
    _log_bookmark_route_result(operation="add", result="success", started_at=started_at)
    return response_payload


@router.delete("/{job_id}/{bookmark_id}", response_model=PlaybackBookmarkDeleteResponse)
def delete_bookmark(
    job_id: str,
    bookmark_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
) -> PlaybackBookmarkDeleteResponse:
    started_at = time.perf_counter()
    try:
        user_id = _require_user(request_user)
    except HTTPException:
        _log_bookmark_route_result(
            operation="delete",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    normalized_job_id = _normalize_route_id(job_id)
    if not normalized_job_id:
        _raise_missing_bookmark_target(operation="delete", started_at=started_at)
    normalized_bookmark_id = _normalize_route_id(bookmark_id)
    if not normalized_bookmark_id:
        _log_bookmark_route_result(
            operation="delete",
            result="success",
            started_at=started_at,
            deleted=False,
        )
        return PlaybackBookmarkDeleteResponse(deleted=False, bookmark_id=normalized_bookmark_id)
    try:
        deleted = bookmark_service.remove_bookmark(
            normalized_job_id,
            user_id,
            normalized_bookmark_id,
        )
        response_payload = PlaybackBookmarkDeleteResponse(
            deleted=deleted,
            bookmark_id=normalized_bookmark_id,
        )
    except Exception:
        _raise_bookmark_storage_unavailable(operation="delete", started_at=started_at)
    _log_bookmark_route_result(
        operation="delete",
        result="success",
        started_at=started_at,
        deleted=deleted,
    )
    return response_payload
