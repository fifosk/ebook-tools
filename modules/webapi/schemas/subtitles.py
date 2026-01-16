"""Schemas for subtitle pipeline endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SubtitleSourceEntry(BaseModel):
    """Metadata describing a discoverable subtitle file."""

    name: str
    path: str
    format: str
    language: Optional[str] = None
    modified_at: Optional[datetime] = None


class SubtitleDeleteRequest(BaseModel):
    """Request payload used to delete a subtitle source file."""

    subtitle_path: str
    base_dir: Optional[str] = None


class SubtitleDeleteResponse(BaseModel):
    """Outcome of deleting a subtitle source file."""

    subtitle_path: str
    base_dir: Optional[str] = None
    removed: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class SubtitleSubmissionPayload(BaseModel):
    """Payload used when submitting a subtitle job via JSON."""

    input_language: str
    target_language: str
    enable_transliteration: bool = False
    highlight: bool = True
    batch_size: Optional[int] = None
    translation_batch_size: Optional[int] = None
    source_path: Optional[str] = None
    cleanup_source: bool = False
    mirror_batches_to_source_dir: bool = True
    llm_model: Optional[str] = None
    translation_provider: Optional[str] = None
    transliteration_mode: Optional[str] = None
    transliteration_model: Optional[str] = None


class SubtitleSourceListResponse(BaseModel):
    """Collection of available subtitle sources."""

    sources: List[SubtitleSourceEntry] = Field(default_factory=list)


class SubtitleTvMetadataParse(BaseModel):
    """Parsed TV episode identifier inferred from a subtitle filename."""

    series: str
    season: int
    episode: int
    pattern: str


class SubtitleTvMetadataResponse(BaseModel):
    """Response payload describing subtitle TV metadata enrichment state."""

    job_id: str
    source_name: Optional[str] = None
    parsed: Optional[SubtitleTvMetadataParse] = None
    media_metadata: Optional[Dict[str, Any]] = None


class SubtitleTvMetadataLookupRequest(BaseModel):
    """Request payload to trigger a TV metadata lookup for a subtitle job."""

    force: bool = False


class SubtitleTvMetadataPreviewResponse(BaseModel):
    """Response payload describing TV metadata lookup results for a filename."""

    source_name: Optional[str] = None
    parsed: Optional[SubtitleTvMetadataParse] = None
    media_metadata: Optional[Dict[str, Any]] = None


class SubtitleTvMetadataPreviewLookupRequest(BaseModel):
    """Request payload to trigger a TV metadata lookup for a subtitle filename."""

    source_name: str
    force: bool = False
