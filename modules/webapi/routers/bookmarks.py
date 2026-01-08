"""Routes for playback bookmark storage."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import RequestUserContext, get_bookmark_service, get_request_user
from ..schemas.bookmarks import (
    PlaybackBookmarkDeleteResponse,
    PlaybackBookmarkEntry,
    PlaybackBookmarkListResponse,
    PlaybackBookmarkPayload,
)
from ...services.bookmark_service import BookmarkService


router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


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
    user_id = _require_user(request_user)
    entries = bookmark_service.list_bookmarks(job_id, user_id)
    payload = [PlaybackBookmarkEntry(**entry.__dict__) for entry in entries]
    return PlaybackBookmarkListResponse(job_id=job_id, bookmarks=payload)


@router.post("/{job_id}", response_model=PlaybackBookmarkEntry)
def add_bookmark(
    job_id: str,
    payload: PlaybackBookmarkPayload,
    request_user: RequestUserContext = Depends(get_request_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
) -> PlaybackBookmarkEntry:
    user_id = _require_user(request_user)
    entry = bookmark_service.add_bookmark(job_id, user_id, payload.model_dump())
    return PlaybackBookmarkEntry(**entry.__dict__)


@router.delete("/{job_id}/{bookmark_id}", response_model=PlaybackBookmarkDeleteResponse)
def delete_bookmark(
    job_id: str,
    bookmark_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    bookmark_service: BookmarkService = Depends(get_bookmark_service),
) -> PlaybackBookmarkDeleteResponse:
    user_id = _require_user(request_user)
    deleted = bookmark_service.remove_bookmark(job_id, user_id, bookmark_id)
    return PlaybackBookmarkDeleteResponse(deleted=deleted, bookmark_id=bookmark_id)
