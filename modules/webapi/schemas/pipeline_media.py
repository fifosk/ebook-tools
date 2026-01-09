"""Schemas for pipeline media, chunk metadata, and search responses."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class PipelineMediaFile(BaseModel):
    """Describes generated media metadata for a job."""

    name: str
    url: Optional[str] = None
    size: Optional[int] = None
    updated_at: Optional[datetime] = None
    source: Literal["completed", "live"]
    relative_path: Optional[str] = None
    path: Optional[str] = None
    chunk_id: Optional[str] = None
    range_fragment: Optional[str] = None
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    type: Optional[str] = None

    @field_serializer("updated_at")
    def _serialize_updated_at(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()


class ChunkSentenceTimelineEvent(BaseModel):
    duration: float
    original_index: int
    translation_index: int
    transliteration_index: int


class ChunkSentenceVariant(BaseModel):
    text: str = ""
    tokens: List[str] = Field(default_factory=list)


class ChunkSentenceImagePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    path: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None


class ChunkSentenceMetadata(BaseModel):
    sentence_number: Optional[int] = None
    original: ChunkSentenceVariant
    translation: Optional[ChunkSentenceVariant] = None
    transliteration: Optional[ChunkSentenceVariant] = None
    timeline: List[ChunkSentenceTimelineEvent] = Field(default_factory=list)
    image: Optional[ChunkSentenceImagePayload] = None
    image_path: Optional[str] = None
    imagePath: Optional[str] = None
    total_duration: Optional[float] = None
    highlight_granularity: Optional[str] = None
    counts: Dict[str, int] = Field(default_factory=dict)
    phase_durations: Dict[str, float] = Field(default_factory=dict)


class AudioTrackMetadata(BaseModel):
    """Metadata about an audio artifact referenced by a chunk."""

    path: Optional[str] = None
    url: Optional[str] = None
    duration: Optional[float] = None
    sampleRate: Optional[int] = None


class PipelineMediaChunk(BaseModel):
    """Groups media files produced for a specific chunk."""

    chunk_id: Optional[str] = None
    range_fragment: Optional[str] = None
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    files: List[PipelineMediaFile] = Field(default_factory=list)
    sentences: List[ChunkSentenceMetadata] = Field(default_factory=list)
    metadata_path: Optional[str] = None
    metadata_url: Optional[str] = None
    sentence_count: Optional[int] = None
    audio_tracks: Dict[str, AudioTrackMetadata] = Field(default_factory=dict)


class PipelineMediaResponse(BaseModel):
    """Response payload grouping generated media by type."""

    media: Dict[str, List[PipelineMediaFile]] = Field(default_factory=dict)
    chunks: List[PipelineMediaChunk] = Field(default_factory=list)
    complete: bool = False


class MediaSearchHit(BaseModel):
    """Single search match across generated ebook media."""

    job_id: str
    job_label: Optional[str] = None
    base_id: Optional[str] = None
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_total: Optional[int] = None
    range_fragment: Optional[str] = None
    start_sentence: Optional[int] = None
    end_sentence: Optional[int] = None
    snippet: str
    occurrence_count: int = Field(default=0, ge=0)
    match_start: Optional[int] = None
    match_end: Optional[int] = None
    text_length: Optional[int] = None
    offset_ratio: Optional[float] = None
    approximate_time_seconds: Optional[float] = None
    media: Dict[str, List[PipelineMediaFile]] = Field(default_factory=dict)
    source: Literal["pipeline", "library"] = Field(default="pipeline")
    library_author: Optional[str] = Field(default=None, alias="libraryAuthor")
    library_genre: Optional[str] = Field(default=None, alias="libraryGenre")
    library_language: Optional[str] = Field(default=None, alias="libraryLanguage")
    cover_path: Optional[str] = Field(default=None, alias="coverPath")
    library_path: Optional[str] = Field(default=None, alias="libraryPath")


class MediaSearchResponse(BaseModel):
    """Response payload for media search queries."""

    query: str
    limit: int
    count: int
    results: List[MediaSearchHit] = Field(default_factory=list)
