"""Schemas for playback analytics endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlaybackHeartbeatPayload(BaseModel):
    """Client heartbeat reporting listened seconds."""

    job_id: str
    language: str
    track_kind: str  # "original" | "translation"
    delta_seconds: float = Field(ge=0, le=300)


class PlaybackHeartbeatResponse(BaseModel):
    ok: bool = True
