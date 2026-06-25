"""Routes for playback bookmark storage."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status

from modules import logging_manager as log_mgr

from ..dependencies import RequestUserContext, get_bookmark_service, get_request_user
from ..route_telemetry import record_started_route_duration
from ..schemas.bookmarks import (
    PlaybackBookmarkDeleteResponse,
    PlaybackBookmarkEntry,
    PlaybackBookmarkListResponse,
    PlaybackBookmarkPayload,
)
from ...services.bookmark_service import BookmarkService


router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])
logger = log_mgr.get_logger()


def _record_bookmark_route_duration(operation: str, result: str, started_at: float) -> None:
    """Record token-safe playback bookmark route timing if metrics are available."""

    record_started_route_duration("BOOKMARK_ROUTE_DURATION", operation, result, started_at)


def _log_bookmark_route_result(
    *,
    operation: str,
    result: str,
    started_at: float,
    bookmark_count: int | None = None,
    deleted: bool | None = None,
) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1000
    details = (
        f"Bookmark route operation={operation} "
        f"result={result} duration_ms={duration_ms:.1f}"
    )
    if bookmark_count is not None:
        details += f" bookmarks={bookmark_count}"
    if deleted is not None:
        details += f" deleted={str(deleted).lower()}"
    log_method = logger.info if result != "success" or duration_ms >= 250 else logger.debug
    log_method(details)


def _require_user(request_user: RequestUserContext) -> str:
    if not request_user.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    return request_user.user_id


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
        _record_bookmark_route_duration("list", "unauthorized", started_at)
        _log_bookmark_route_result(
            operation="list",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    try:
        entries = bookmark_service.list_bookmarks(job_id, user_id)
    except Exception:
        _record_bookmark_route_duration("list", "error", started_at)
        _log_bookmark_route_result(operation="list", result="error", started_at=started_at)
        raise
    payload = [PlaybackBookmarkEntry(**entry.__dict__) for entry in entries]
    _record_bookmark_route_duration("list", "success", started_at)
    _log_bookmark_route_result(
        operation="list",
        result="success",
        started_at=started_at,
        bookmark_count=len(payload),
    )
    return PlaybackBookmarkListResponse(job_id=job_id, bookmarks=payload)


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
        _record_bookmark_route_duration("add", "unauthorized", started_at)
        _log_bookmark_route_result(
            operation="add",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    try:
        entry = bookmark_service.add_bookmark(job_id, user_id, payload.model_dump())
    except Exception:
        _record_bookmark_route_duration("add", "error", started_at)
        _log_bookmark_route_result(operation="add", result="error", started_at=started_at)
        raise
    _record_bookmark_route_duration("add", "success", started_at)
    _log_bookmark_route_result(operation="add", result="success", started_at=started_at)
    return PlaybackBookmarkEntry(**entry.__dict__)


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
        _record_bookmark_route_duration("delete", "unauthorized", started_at)
        _log_bookmark_route_result(
            operation="delete",
            result="unauthorized",
            started_at=started_at,
        )
        raise
    try:
        deleted = bookmark_service.remove_bookmark(job_id, user_id, bookmark_id)
    except Exception:
        _record_bookmark_route_duration("delete", "error", started_at)
        _log_bookmark_route_result(operation="delete", result="error", started_at=started_at)
        raise
    _record_bookmark_route_duration("delete", "success", started_at)
    _log_bookmark_route_result(
        operation="delete",
        result="success",
        started_at=started_at,
        deleted=deleted,
    )
    return PlaybackBookmarkDeleteResponse(deleted=deleted, bookmark_id=bookmark_id)
