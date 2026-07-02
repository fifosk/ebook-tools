"""Schemas for playback timing responses."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


TimingTrackName = Literal["mix", "translation", "original"]


class JobTimingTrackPayload(BaseModel):
    """Flattened word timing entries for one playback track."""

    track: TimingTrackName
    segments: List[Dict[str, Any]]
    playback_rate: Optional[float] = None


class JobTimingAudioBinding(BaseModel):
    """Availability summary for a generated audio role."""

    track: TimingTrackName
    available: bool


class JobTimingResponse(BaseModel):
    """Timing payload consumed by Web and Apple playback."""

    job_id: str
    tracks: Dict[str, JobTimingTrackPayload]
    audio: Dict[str, JobTimingAudioBinding]
    highlighting_policy: Optional[str]
    has_estimated_segments: bool = Field(serialization_alias="has_estimated_segments")
