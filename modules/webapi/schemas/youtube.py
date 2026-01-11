"""Schemas for YouTube subtitle/download/dubbing endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..jobs import PipelineJobStatus


class YoutubeSubtitleTrackPayload(BaseModel):
    """Description of an available YouTube subtitle track."""

    language: str
    kind: Literal["auto", "manual"]
    name: Optional[str] = None
    formats: List[str] = Field(default_factory=list)


class YoutubeSubtitleListResponse(BaseModel):
    """Available subtitle tracks for a YouTube video."""

    video_id: str
    title: Optional[str] = None
    tracks: List[YoutubeSubtitleTrackPayload] = Field(default_factory=list)
    video_formats: List["YoutubeVideoFormatPayload"] = Field(default_factory=list)


class YoutubeVideoFormatPayload(BaseModel):
    """Description of an available YouTube mp4 format option."""

    format_id: str
    ext: str
    resolution: Optional[str] = None
    fps: Optional[int] = None
    note: Optional[str] = None
    bitrate_kbps: Optional[float] = None
    filesize: Optional[str] = None


class YoutubeSubtitleDownloadRequest(BaseModel):
    """Request payload to download a YouTube subtitle track."""

    url: str
    language: str
    kind: Literal["auto", "manual"] = "manual"
    video_output_dir: Optional[str] = None
    timestamp: Optional[str] = None


class YoutubeSubtitleDownloadResponse(BaseModel):
    """Response after downloading a YouTube subtitle track."""

    output_path: str
    filename: str


class YoutubeVideoDownloadRequest(BaseModel):
    """Request payload to download a YouTube video."""

    url: str
    output_dir: Optional[str] = None
    format_id: Optional[str] = None
    timestamp: Optional[str] = None


class YoutubeVideoDownloadResponse(BaseModel):
    """Response after downloading a YouTube video."""

    output_path: str
    filename: str
    folder: str


class YoutubeNasSubtitlePayload(BaseModel):
    """Subtitle file stored next to a downloaded YouTube video."""

    path: str
    filename: str
    language: Optional[str] = None
    format: str


class YoutubeNasVideoPayload(BaseModel):
    """Downloaded YouTube video and its discovered subtitle companions."""

    path: str
    filename: str
    folder: str
    size_bytes: int
    modified_at: datetime
    source: Optional[str] = Field(default="youtube")
    linked_job_ids: List[str] = Field(default_factory=list)
    subtitles: List[YoutubeNasSubtitlePayload] = Field(default_factory=list)


class YoutubeNasLibraryResponse(BaseModel):
    """Response describing the NAS directory of downloaded YouTube videos."""

    base_dir: str
    videos: List[YoutubeNasVideoPayload] = Field(default_factory=list)


class YoutubeSubtitleExtractionRequest(BaseModel):
    """Request payload for extracting embedded subtitle tracks from a video."""

    video_path: str
    languages: Optional[List[str]] = None


class YoutubeInlineSubtitleStream(BaseModel):
    """Single subtitle stream embedded in a video file."""

    index: int
    position: int
    language: Optional[str] = None
    codec: Optional[str] = None
    title: Optional[str] = None
    can_extract: bool = True


class YoutubeSubtitleExtractionResponse(BaseModel):
    """Response describing extracted subtitle tracks."""

    video_path: str
    extracted: List[YoutubeNasSubtitlePayload] = Field(default_factory=list)


class YoutubeInlineSubtitleListResponse(BaseModel):
    """Response describing subtitle streams embedded in a video."""

    video_path: str
    streams: List[YoutubeInlineSubtitleStream] = Field(default_factory=list)


class YoutubeSubtitleDeleteRequest(BaseModel):
    """Request payload for deleting a subtitle next to a NAS video."""

    video_path: str
    subtitle_path: str


class YoutubeSubtitleDeleteResponse(BaseModel):
    """Response payload after deleting a NAS subtitle and companions."""

    video_path: str
    subtitle_path: str
    removed: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class YoutubeVideoDeleteRequest(BaseModel):
    """Request payload to delete a downloaded YouTube video."""

    video_path: str


class YoutubeVideoDeleteResponse(BaseModel):
    """Response payload after deleting a YouTube video and companions."""

    video_path: str
    removed: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class YoutubeDubRequest(BaseModel):
    """Request payload for generating a dubbed audio track from an ASS file."""

    video_path: str
    subtitle_path: str
    media_metadata: Optional[Dict[str, Any]] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    voice: Optional[str] = None
    tempo: Optional[float] = None
    macos_reading_speed: Optional[int] = None
    output_dir: Optional[str] = None
    start_time_offset: Optional[str] = None
    end_time_offset: Optional[str] = None
    original_mix_percent: Optional[float] = None
    flush_sentences: Optional[int] = None
    llm_model: Optional[str] = None
    translation_provider: Optional[str] = None
    translation_batch_size: Optional[int] = None
    transliteration_mode: Optional[str] = None
    split_batches: Optional[bool] = None
    stitch_batches: Optional[bool] = True
    include_transliteration: Optional[bool] = None
    target_height: Optional[int] = None
    preserve_aspect_ratio: Optional[bool] = None


class YoutubeDubResponse(BaseModel):
    """Job handle for generating a dubbed YouTube video."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime
    job_type: str = "youtube_dub"
    output_path: Optional[str] = None
