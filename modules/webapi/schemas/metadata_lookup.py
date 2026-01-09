"""Schemas for media metadata lookup/enrichment endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class YoutubeVideoMetadataParse(BaseModel):
    """Parsed YouTube video identifier inferred from a filename/URL."""

    video_id: str
    pattern: str


class YoutubeVideoMetadataResponse(BaseModel):
    """Response payload describing YouTube metadata enrichment state for a job."""

    job_id: str
    source_name: Optional[str] = None
    parsed: Optional[YoutubeVideoMetadataParse] = None
    youtube_metadata: Optional[Dict[str, Any]] = None


class YoutubeVideoMetadataLookupRequest(BaseModel):
    """Request payload to trigger a YouTube metadata lookup for a job."""

    force: bool = False


class YoutubeVideoMetadataPreviewResponse(BaseModel):
    """Response payload describing YouTube metadata lookup results for a filename/URL."""

    source_name: Optional[str] = None
    parsed: Optional[YoutubeVideoMetadataParse] = None
    youtube_metadata: Optional[Dict[str, Any]] = None


class YoutubeVideoMetadataPreviewLookupRequest(BaseModel):
    """Request payload to trigger a YouTube metadata lookup for a filename/URL."""

    source_name: str
    force: bool = False


class BookOpenLibraryQuery(BaseModel):
    """Parsed Open Library query inferred from a filename/title/ISBN."""

    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None


class BookOpenLibraryMetadataResponse(BaseModel):
    """Response payload describing Open Library enrichment for a book-like job."""

    job_id: str
    source_name: Optional[str] = None
    query: Optional[BookOpenLibraryQuery] = None
    book_metadata_lookup: Optional[Dict[str, Any]] = None


class BookOpenLibraryMetadataLookupRequest(BaseModel):
    """Request payload to trigger an Open Library lookup for a book-like job."""

    force: bool = False


class BookOpenLibraryMetadataPreviewResponse(BaseModel):
    """Response payload describing Open Library lookup results for a filename/title/ISBN."""

    source_name: Optional[str] = None
    query: Optional[BookOpenLibraryQuery] = None
    book_metadata_lookup: Optional[Dict[str, Any]] = None


class BookOpenLibraryMetadataPreviewLookupRequest(BaseModel):
    """Request payload to trigger an Open Library lookup for a filename/title/ISBN."""

    query: str
    force: bool = False
