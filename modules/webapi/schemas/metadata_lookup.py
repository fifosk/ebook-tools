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


# Unified metadata lookup schemas


class UnifiedMetadataLookupRequest(BaseModel):
    """Request payload for unified metadata lookup."""

    type: str  # "book", "movie", "tv_series", "tv_episode", "youtube_video"

    # Book fields
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None

    # Movie/TV fields
    movie_title: Optional[str] = None
    series_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None

    # YouTube fields
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    source_filename: Optional[str] = None

    # Direct lookup IDs
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None

    # Options
    force: bool = False
    include_raw: bool = False


class SeriesInfoResponse(BaseModel):
    """Series information in metadata response."""

    series_id: Optional[str] = None
    series_title: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_id: Optional[str] = None
    episode_title: Optional[str] = None


class UnifiedMetadataResponse(BaseModel):
    """Response payload for unified metadata lookup."""

    title: str
    type: str
    year: Optional[int] = None
    genres: list[str] = []
    summary: Optional[str] = None
    cover: Optional[str] = None
    cover_url: Optional[str] = None
    cover_file: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    runtime_minutes: Optional[int] = None
    rating: Optional[float] = None
    votes: Optional[int] = None

    # Series info (for TV)
    series: Optional[SeriesInfoResponse] = None

    # Source tracking
    confidence: str = "low"
    primary_source: Optional[str] = None
    contributing_sources: list[str] = []
    source_ids: Dict[str, Any] = {}

    # Metadata
    queried_at: Optional[str] = None
    error: Optional[str] = None

    # Optional raw responses
    raw_responses: Optional[Dict[str, Any]] = None
