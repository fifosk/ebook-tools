"""Schemas for the library API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class LibraryItemPayload(BaseModel):
    """Serializable representation of a library entry."""

    job_id: str = Field(alias="jobId")
    author: str
    book_title: str = Field(alias="bookTitle")
    genre: Optional[str] = None
    language: str
    status: Literal["finished", "paused"]
    media_completed: bool = Field(alias="mediaCompleted", default=False)
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    library_path: str = Field(alias="libraryPath")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class LibraryMoveRequest(BaseModel):
    """Payload for moving a job into the library."""

    status_override: Optional[Literal["paused", "finished"]] = Field(
        default=None, alias="statusOverride"
    )

    class Config:
        populate_by_name = True


class LibraryMoveResponse(BaseModel):
    """Response returned when a job is moved into the library."""

    item: LibraryItemPayload


class LibrarySearchResponse(BaseModel):
    """Response envelope for library search requests."""

    total: int
    page: int
    limit: int
    view: Literal["flat", "by_author", "by_genre", "by_language"]
    items: List[LibraryItemPayload] = Field(default_factory=list)
    groups: Optional[List[Dict[str, Any]]] = None


class LibraryMediaRemovalResponse(BaseModel):
    """Response payload after removing generated media."""

    job_id: str = Field(alias="jobId")
    location: Literal["library", "queue"]
    removed: int
    item: Optional[LibraryItemPayload] = None

    class Config:
        populate_by_name = True


class LibraryReindexResponse(BaseModel):
    """Response payload for reindex operations."""

    indexed: int
