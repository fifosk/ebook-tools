"""Schemas for source discovery and acquisition endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


AcquisitionCapability = Literal[
    "search",
    "metadata",
    "acquire",
    "poll",
    "extract_subtitles",
    "import_local",
]
AcquisitionMediaKind = Literal["book", "video"]
AcquisitionProviderStatus = Literal["available", "not_configured", "planned"]
AcquisitionRights = Literal[
    "public_domain",
    "open_license",
    "user_provided",
    "unknown",
    "restricted",
]


class AcquisitionProviderPayload(BaseModel):
    """A provider clients can show in a discovery/acquisition picker."""

    id: str
    label: str
    media_kinds: List[AcquisitionMediaKind] = Field(default_factory=list)
    capabilities: List[AcquisitionCapability] = Field(default_factory=list)
    status: AcquisitionProviderStatus
    configured: bool = False
    available: bool = False
    rights: List[AcquisitionRights] = Field(default_factory=list)
    source_path: str | None = None
    policy_notes: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)


class AcquisitionProviderListResponse(BaseModel):
    """Response listing configured and planned acquisition providers."""

    providers: List[AcquisitionProviderPayload] = Field(default_factory=list)
    policy_notes: List[str] = Field(default_factory=list)
    paths: Dict[str, str] = Field(default_factory=dict)


class AcquisitionSubtitleHintPayload(BaseModel):
    """Subtitle companion advertised for a discovered video candidate."""

    path: str
    filename: str
    language: str | None = None
    format: str | None = None


class AcquisitionCandidatePayload(BaseModel):
    """Provider-neutral source candidate returned by discovery."""

    candidate_id: str
    provider: str
    media_kind: AcquisitionMediaKind
    title: str
    rights: AcquisitionRights
    capabilities: List[AcquisitionCapability] = Field(default_factory=list)
    candidate_token: str
    subtitle: str | None = None
    contributors: List[str] = Field(default_factory=list)
    language: str | None = None
    year: int | None = None
    published_at: str | None = None
    source_url: str | None = None
    thumbnail_url: str | None = None
    cover_url: str | None = None
    local_path: str | None = None
    size_bytes: int | None = None
    modified_at: datetime | None = None
    duration_seconds: int | None = None
    subtitles: List[AcquisitionSubtitleHintPayload] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    policy_notes: List[str] = Field(default_factory=list)


class AcquisitionDiscoveryResponse(BaseModel):
    """Response for normalized discovery candidates."""

    candidates: List[AcquisitionCandidatePayload] = Field(default_factory=list)
    policy_notes: List[str] = Field(default_factory=list)
    providers_queried: List[str] = Field(default_factory=list)


class AcquisitionAcquireRequest(BaseModel):
    """Reviewed acquisition request for a discovery candidate."""

    candidate_token: str
    confirmed: bool = False
    filename: str | None = None


class AcquisitionJobCreateRequest(BaseModel):
    """Reviewed async downloader handoff request."""

    provider: str = "download_station"
    source_uri: str
    confirmed: bool = False
    destination: str | None = None


class AcquisitionArtifactResponse(BaseModel):
    """Completed acquisition artifact ready for existing Create flows."""

    provider: str
    media_kind: AcquisitionMediaKind
    status: str
    artifact_id: str = ""
    artifact_path: str
    local_path: str
    filename: str
    size_bytes: int
    modified_at: datetime
    next_actions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AcquisitionPreparedArtifactResponse(BaseModel):
    """Prepared source fields that existing Create flows can submit directly."""

    provider: str
    media_kind: AcquisitionMediaKind
    source_kind: str
    local_path: str
    input_file: str | None = None
    video_path: str | None = None
    subtitle_path: str | None = None
    subtitles: List[AcquisitionSubtitleHintPayload] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AcquisitionJobStatusResponse(BaseModel):
    """Token-safe downloader job status for Web and Apple Create."""

    provider: str
    task_id: str
    status: str
    progress: float | None = None
    message: str | None = None
    external_task_id: str | None = None
    raw_status: str | None = None
    started_at: datetime | None = None
    updated_at: datetime
    completed_files: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
