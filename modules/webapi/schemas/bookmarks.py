"""Schemas for playback bookmarks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BookmarkKind = Literal["time", "sentence"]
BookmarkMediaType = Literal["text", "audio", "video"]


class PlaybackBookmarkPayload(BaseModel):
    id: str | None = None
    label: str
    kind: BookmarkKind = "time"
    created_at: float | None = None
    position: float | None = None
    sentence: int | None = None
    media_type: BookmarkMediaType | None = None
    media_id: str | None = None
    base_id: str | None = None
    segment_id: str | None = None
    chunk_id: str | None = None
    item_type: str | None = None


class PlaybackBookmarkEntry(BaseModel):
    id: str
    job_id: str
    item_type: str | None = None
    kind: BookmarkKind
    created_at: float
    label: str
    position: float | None = None
    sentence: int | None = None
    media_type: BookmarkMediaType | None = None
    media_id: str | None = None
    base_id: str | None = None
    segment_id: str | None = None
    chunk_id: str | None = None


class PlaybackBookmarkListResponse(BaseModel):
    job_id: str
    bookmarks: list[PlaybackBookmarkEntry] = Field(default_factory=list)


class PlaybackBookmarkDeleteResponse(BaseModel):
    deleted: bool
    bookmark_id: str
