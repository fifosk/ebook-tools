"""Typed Pydantic models for structured media metadata (v2).

Replaces the flat Dict[str, Any] ``media_metadata`` with semantic sections
that are polymorphic by media type.  All keys use camelCase to match the
v3 chunk convention established in the refactoring plan.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Nested sub-schemas
# ---------------------------------------------------------------------------


class SourceIdsSchema(BaseModel):
    """External identifiers from metadata lookup services."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    isbn: Optional[str] = None
    isbn_13: Optional[str] = Field(default=None, alias="isbn13")
    openlibrary: Optional[str] = None
    openlibrary_book: Optional[str] = Field(default=None, alias="openlibraryBook")
    google_books: Optional[str] = Field(default=None, alias="googleBooks")
    tmdb: Optional[int] = None
    imdb: Optional[str] = None
    tvmaze_show: Optional[int] = Field(default=None, alias="tvmazeShow")
    tvmaze_episode: Optional[int] = Field(default=None, alias="tvmazeEpisode")
    wikidata: Optional[str] = None
    youtube_video: Optional[str] = Field(default=None, alias="youtubeVideo")
    youtube_channel: Optional[str] = Field(default=None, alias="youtubeChannel")


class SeriesInfoSchema(BaseModel):
    """TV series identification (season/episode)."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    series_title: Optional[str] = Field(default=None, alias="seriesTitle")
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = Field(default=None, alias="episodeTitle")
    series_id: Optional[str] = Field(default=None, alias="seriesId")
    episode_id: Optional[str] = Field(default=None, alias="episodeId")


class YouTubeInfoSchema(BaseModel):
    """YouTube-specific metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    video_id: Optional[str] = Field(default=None, alias="videoId")
    channel_id: Optional[str] = Field(default=None, alias="channelId")
    channel_name: Optional[str] = Field(default=None, alias="channelName")
    upload_date: Optional[str] = Field(default=None, alias="uploadDate")


# ---------------------------------------------------------------------------
# Main sections
# ---------------------------------------------------------------------------


class SourceMetadata(BaseModel):
    """Identity information about the media source.

    Common fields apply to all media types.  Type-conditional fields
    (``isbn``, ``series``, ``youtube``) are present depending on ``mediaType``
    at the top level of :class:`StructuredMediaMetadata`.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Common fields
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    summary: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    language: Optional[str] = None

    # Book-specific
    isbn: Optional[str] = None
    isbn_13: Optional[str] = Field(default=None, alias="isbn13")

    # TV-specific
    series: Optional[SeriesInfoSchema] = None

    # YouTube-specific
    youtube: Optional[YouTubeInfoSchema] = None

    # Movie/TV extras
    runtime_minutes: Optional[int] = Field(default=None, alias="runtimeMinutes")
    rating: Optional[float] = None
    votes: Optional[int] = None


class LanguageConfig(BaseModel):
    """Translation and transliteration configuration."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    input_language: Optional[str] = Field(default=None, alias="inputLanguage")
    original_language: Optional[str] = Field(default=None, alias="originalLanguage")
    target_language: Optional[str] = Field(default=None, alias="targetLanguage")
    target_languages: List[str] = Field(default_factory=list, alias="targetLanguages")
    translation_provider: Optional[str] = Field(default=None, alias="translationProvider")
    translation_model: Optional[str] = Field(default=None, alias="translationModel")
    translation_model_requested: Optional[str] = Field(
        default=None, alias="translationModelRequested"
    )
    transliteration_mode: Optional[str] = Field(default=None, alias="transliterationMode")
    transliteration_model: Optional[str] = Field(default=None, alias="transliterationModel")
    transliteration_module: Optional[str] = Field(default=None, alias="transliterationModule")


class ContentStructure(BaseModel):
    """Content structure — sentence counts and chapter index references."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    total_sentences: Optional[int] = Field(default=None, alias="totalSentences")
    content_index_path: Optional[str] = Field(default=None, alias="contentIndexPath")
    content_index_url: Optional[str] = Field(default=None, alias="contentIndexUrl")
    content_index_summary: Optional[Dict[str, Any]] = Field(
        default=None, alias="contentIndexSummary"
    )


class CoverAssets(BaseModel):
    """Cover image paths and URLs."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    cover_file: Optional[str] = Field(default=None, alias="coverFile")
    cover_url: Optional[str] = Field(default=None, alias="coverUrl")
    book_cover_url: Optional[str] = Field(default=None, alias="bookCoverUrl")
    job_cover_asset: Optional[str] = Field(default=None, alias="jobCoverAsset")
    job_cover_asset_url: Optional[str] = Field(default=None, alias="jobCoverAssetUrl")


class EnrichmentProvenance(BaseModel):
    """Tracks where metadata was enriched from and lookup snapshots."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    source: Optional[str] = None
    confidence: Optional[str] = None
    queried_at: Optional[str] = Field(default=None, alias="queriedAt")
    source_ids: Optional[SourceIdsSchema] = Field(default=None, alias="sourceIds")
    lookup_result: Optional[Dict[str, Any]] = Field(default=None, alias="lookupResult")


# ---------------------------------------------------------------------------
# Top-level container
# ---------------------------------------------------------------------------


class StructuredMediaMetadata(BaseModel):
    """Top-level structured metadata container (v2).

    This replaces the flat ``media_metadata`` / ``book_metadata`` dict with
    semantic sections that are polymorphic by ``media_type``.
    """

    model_config = ConfigDict(populate_by_name=True)

    metadata_version: int = Field(default=2, alias="metadataVersion")
    media_type: str = Field(default="book", alias="mediaType")
    source: SourceMetadata = Field(default_factory=SourceMetadata)
    language_config: LanguageConfig = Field(default_factory=LanguageConfig, alias="languageConfig")
    content_structure: ContentStructure = Field(
        default_factory=ContentStructure, alias="contentStructure"
    )
    cover_assets: CoverAssets = Field(default_factory=CoverAssets, alias="coverAssets")
    enrichment: EnrichmentProvenance = Field(
        default_factory=EnrichmentProvenance, alias="enrichment"
    )
    job_label: Optional[str] = Field(default=None, alias="jobLabel")
    extras: Dict[str, Any] = Field(default_factory=dict)

    def to_camel_dict(self) -> Dict[str, Any]:
        """Serialize to a dict using camelCase keys (for JSON storage)."""
        return self.model_dump(by_alias=True, exclude_none=True)


__all__ = [
    "ContentStructure",
    "CoverAssets",
    "EnrichmentProvenance",
    "LanguageConfig",
    "SeriesInfoSchema",
    "SourceIdsSchema",
    "SourceMetadata",
    "StructuredMediaMetadata",
    "YouTubeInfoSchema",
]
