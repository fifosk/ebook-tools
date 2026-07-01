"""Provider-neutral acquisition discovery models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AcquisitionSubtitleHint:
    """Subtitle companion available for a discovered video."""

    path: str
    filename: str
    language: str | None = None
    format: str | None = None


@dataclass(frozen=True)
class AcquisitionCandidate:
    """Provider-neutral candidate returned by discovery endpoints."""

    candidate_id: str
    provider: str
    media_kind: str
    title: str
    rights: str
    capabilities: tuple[str, ...]
    candidate_token: str
    subtitle: str | None = None
    contributors: tuple[str, ...] = ()
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
    subtitles: tuple[AcquisitionSubtitleHint, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    policy_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AcquisitionDiscoveryResult:
    """Result from a discovery query."""

    candidates: tuple[AcquisitionCandidate, ...]
    policy_notes: tuple[str, ...] = ()
    providers_queried: tuple[str, ...] = ()


class AcquisitionProviderDiscoveryError(RuntimeError):
    """Token-safe error raised when a configured discovery provider fails."""

    def __init__(self, *, provider: str, reason: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.reason = reason
        self.public_message = message
