"""Schemas for source discovery and acquisition endpoints."""

from __future__ import annotations

from typing import Dict, List, Literal

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
