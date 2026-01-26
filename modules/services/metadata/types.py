"""Core type definitions for the unified metadata lookup pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MediaType(str, Enum):
    """Type of media being looked up."""

    BOOK = "book"
    MOVIE = "movie"
    TV_SERIES = "tv_series"
    TV_EPISODE = "tv_episode"
    YOUTUBE_VIDEO = "youtube_video"


class ConfidenceLevel(str, Enum):
    """Confidence level for metadata lookup results."""

    HIGH = "high"  # Exact match from structured API (ISBN, TMDB ID, etc.)
    MEDIUM = "medium"  # Title/author search match from primary source
    LOW = "low"  # Fallback source or partial match


class MetadataSource(str, Enum):
    """Metadata source identifiers."""

    OPENLIBRARY = "openlibrary"
    GOOGLE_BOOKS = "google_books"
    TMDB = "tmdb"
    OMDB = "omdb"
    TVMAZE = "tvmaze"
    WIKIPEDIA = "wikipedia"
    WIKIDATA = "wikidata"
    YTDLP = "yt_dlp"


@dataclass(frozen=True, slots=True)
class SeriesInfo:
    """TV series identification information."""

    series_id: Optional[str] = None
    series_title: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_id: Optional[str] = None
    episode_title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "series_id": self.series_id,
            "series_title": self.series_title,
            "season": self.season,
            "episode": self.episode,
            "episode_id": self.episode_id,
            "episode_title": self.episode_title,
        }


@dataclass(slots=True)
class SourceIds:
    """External identifiers from various metadata sources."""

    isbn: Optional[str] = None
    isbn_13: Optional[str] = None
    openlibrary_work_key: Optional[str] = None
    openlibrary_book_key: Optional[str] = None
    google_books_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    tvmaze_show_id: Optional[int] = None
    tvmaze_episode_id: Optional[int] = None
    wikidata_qid: Optional[str] = None
    youtube_video_id: Optional[str] = None
    youtube_channel_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary, excluding None values."""
        result: Dict[str, Any] = {}
        if self.isbn:
            result["isbn"] = self.isbn
        if self.isbn_13:
            result["isbn_13"] = self.isbn_13
        if self.openlibrary_work_key:
            result["openlibrary"] = self.openlibrary_work_key
        if self.openlibrary_book_key:
            result["openlibrary_book"] = self.openlibrary_book_key
        if self.google_books_id:
            result["google_books"] = self.google_books_id
        if self.tmdb_id is not None:
            result["tmdb"] = self.tmdb_id
        if self.imdb_id:
            result["imdb"] = self.imdb_id
        if self.tvmaze_show_id is not None:
            result["tvmaze_show"] = self.tvmaze_show_id
        if self.tvmaze_episode_id is not None:
            result["tvmaze_episode"] = self.tvmaze_episode_id
        if self.wikidata_qid:
            result["wikidata"] = self.wikidata_qid
        if self.youtube_video_id:
            result["youtube_video"] = self.youtube_video_id
        if self.youtube_channel_id:
            result["youtube_channel"] = self.youtube_channel_id
        return result

    def merge_with(self, other: "SourceIds") -> "SourceIds":
        """Create a new SourceIds merging this with another, preferring self's values."""
        return SourceIds(
            isbn=self.isbn or other.isbn,
            isbn_13=self.isbn_13 or other.isbn_13,
            openlibrary_work_key=self.openlibrary_work_key or other.openlibrary_work_key,
            openlibrary_book_key=self.openlibrary_book_key or other.openlibrary_book_key,
            google_books_id=self.google_books_id or other.google_books_id,
            tmdb_id=self.tmdb_id if self.tmdb_id is not None else other.tmdb_id,
            imdb_id=self.imdb_id or other.imdb_id,
            tvmaze_show_id=self.tvmaze_show_id if self.tvmaze_show_id is not None else other.tvmaze_show_id,
            tvmaze_episode_id=self.tvmaze_episode_id if self.tvmaze_episode_id is not None else other.tvmaze_episode_id,
            wikidata_qid=self.wikidata_qid or other.wikidata_qid,
            youtube_video_id=self.youtube_video_id or other.youtube_video_id,
            youtube_channel_id=self.youtube_channel_id or other.youtube_channel_id,
        )


@dataclass(slots=True)
class UnifiedMetadataResult:
    """Unified output schema for all metadata lookups."""

    # Required fields
    title: str
    type: MediaType

    # Optional core fields
    year: Optional[int] = None
    genres: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    cover_url: Optional[str] = None
    cover_file: Optional[str] = None

    # Series info (for TV)
    series: Optional[SeriesInfo] = None

    # External identifiers
    source_ids: SourceIds = field(default_factory=SourceIds)

    # Provenance
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    primary_source: Optional[MetadataSource] = None
    contributing_sources: List[MetadataSource] = field(default_factory=list)
    queried_at: Optional[datetime] = None

    # Additional metadata
    author: Optional[str] = None  # Book author / TV creator / movie director
    language: Optional[str] = None
    runtime_minutes: Optional[int] = None
    rating: Optional[float] = None  # Rating score (e.g., IMDB rating)
    votes: Optional[int] = None  # Number of votes

    # YouTube-specific
    channel_name: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    upload_date: Optional[str] = None

    # Raw data for debugging (not serialized by default)
    raw_responses: Dict[str, Any] = field(default_factory=dict)

    # Error info
    error: Optional[str] = None

    def to_dict(self, include_raw: bool = False) -> Dict[str, Any]:
        """Serialize to the target JSON schema."""
        result: Dict[str, Any] = {
            "title": self.title,
            "type": self.type.value,
            "year": self.year,
            "genres": self.genres,
            "summary": self.summary,
            "cover": self.cover_url or self.cover_file,
            "confidence": self.confidence.value,
            "source_ids": self.source_ids.to_dict(),
        }

        if self.author:
            result["author"] = self.author

        if self.series:
            result["series"] = self.series.to_dict()

        if self.primary_source:
            result["primary_source"] = self.primary_source.value

        if self.contributing_sources:
            result["contributing_sources"] = [s.value for s in self.contributing_sources]

        if self.queried_at:
            result["queried_at"] = self.queried_at.isoformat()

        if self.language:
            result["language"] = self.language

        if self.runtime_minutes is not None:
            result["runtime_minutes"] = self.runtime_minutes

        if self.rating is not None:
            result["rating"] = self.rating

        if self.votes is not None:
            result["votes"] = self.votes

        if self.cover_url:
            result["cover_url"] = self.cover_url

        if self.cover_file:
            result["cover_file"] = self.cover_file

        # YouTube-specific fields
        if self.channel_name:
            result["channel_name"] = self.channel_name

        if self.view_count is not None:
            result["view_count"] = self.view_count

        if self.like_count is not None:
            result["like_count"] = self.like_count

        if self.upload_date:
            result["upload_date"] = self.upload_date

        if self.error:
            result["error"] = self.error

        if include_raw and self.raw_responses:
            result["raw_responses"] = self.raw_responses

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedMetadataResult":
        """Deserialize from dictionary."""
        source_ids_data = data.get("source_ids", {})
        source_ids = SourceIds(
            isbn=source_ids_data.get("isbn"),
            isbn_13=source_ids_data.get("isbn_13"),
            openlibrary_work_key=source_ids_data.get("openlibrary"),
            openlibrary_book_key=source_ids_data.get("openlibrary_book"),
            google_books_id=source_ids_data.get("google_books"),
            tmdb_id=source_ids_data.get("tmdb"),
            imdb_id=source_ids_data.get("imdb"),
            tvmaze_show_id=source_ids_data.get("tvmaze_show"),
            tvmaze_episode_id=source_ids_data.get("tvmaze_episode"),
            wikidata_qid=source_ids_data.get("wikidata"),
            youtube_video_id=source_ids_data.get("youtube_video"),
            youtube_channel_id=source_ids_data.get("youtube_channel"),
        )

        series_data = data.get("series")
        series = None
        if series_data:
            series = SeriesInfo(
                series_id=series_data.get("series_id"),
                series_title=series_data.get("series_title"),
                season=series_data.get("season"),
                episode=series_data.get("episode"),
                episode_id=series_data.get("episode_id"),
                episode_title=series_data.get("episode_title"),
            )

        primary_source = None
        if data.get("primary_source"):
            try:
                primary_source = MetadataSource(data["primary_source"])
            except ValueError:
                pass

        contributing_sources = []
        for src in data.get("contributing_sources", []):
            try:
                contributing_sources.append(MetadataSource(src))
            except ValueError:
                pass

        queried_at = None
        if data.get("queried_at"):
            try:
                queried_at = datetime.fromisoformat(data["queried_at"])
            except ValueError:
                pass

        return cls(
            title=data.get("title", ""),
            type=MediaType(data.get("type", "book")),
            year=data.get("year"),
            genres=data.get("genres", []),
            summary=data.get("summary"),
            cover_url=data.get("cover_url") or data.get("cover"),
            cover_file=data.get("cover_file"),
            series=series,
            source_ids=source_ids,
            confidence=ConfidenceLevel(data.get("confidence", "low")),
            primary_source=primary_source,
            contributing_sources=contributing_sources,
            queried_at=queried_at,
            author=data.get("author"),
            language=data.get("language"),
            runtime_minutes=data.get("runtime_minutes"),
            rating=data.get("rating"),
            votes=data.get("votes"),
            channel_name=data.get("channel_name"),
            view_count=data.get("view_count"),
            like_count=data.get("like_count"),
            upload_date=data.get("upload_date"),
            raw_responses=data.get("raw_responses", {}),
            error=data.get("error"),
        )

    def has_required_fields(self) -> bool:
        """Check if result has all required fields populated."""
        return all(
            [
                self.title,
                self.year is not None,
                bool(self.genres),
                self.summary,
                self.cover_url or self.cover_file,
            ]
        )


@dataclass(frozen=True, slots=True)
class LookupQuery:
    """Unified query for metadata lookup."""

    media_type: MediaType

    # Book lookup
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None

    # TV/Movie lookup
    series_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    movie_title: Optional[str] = None
    year: Optional[int] = None

    # YouTube lookup
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None

    # Source hints
    source_filename: Optional[str] = None

    # Explicit source IDs for direct lookup
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    openlibrary_key: Optional[str] = None

    def cache_key_parts(self) -> tuple:
        """Return tuple of values for cache key generation."""
        return (
            self.media_type.value,
            self.title or "",
            self.author or "",
            self.isbn or "",
            self.series_name or "",
            str(self.season or ""),
            str(self.episode or ""),
            self.movie_title or "",
            str(self.year or ""),
            self.youtube_video_id or "",
            str(self.tmdb_id or ""),
            self.imdb_id or "",
        )


@dataclass(slots=True)
class LookupOptions:
    """Options controlling lookup behavior."""

    force_refresh: bool = False  # Ignore cache and force new lookup
    skip_cache: bool = False  # Don't use or update cache
    max_sources: int = 3  # Stop after N successful sources
    timeout_seconds: float = 30.0  # Per-source timeout
    include_raw_responses: bool = False  # Include raw API responses
    download_cover: bool = True  # Download cover image to local file


__all__ = [
    "ConfidenceLevel",
    "LookupOptions",
    "LookupQuery",
    "MediaType",
    "MetadataSource",
    "SeriesInfo",
    "SourceIds",
    "UnifiedMetadataResult",
]
