"""Schemas for playback resume positions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


ResumeKind = Literal["time", "sentence"]
ResumeMediaType = Literal["text", "audio", "video"]


class ResumePositionPayload(BaseModel):
    kind: ResumeKind = "time"
    position: float | None = None
    sentence: int | None = None
    chunk_id: str | None = None
    media_type: ResumeMediaType | None = None
    base_id: str | None = None


class ResumePositionEntry(BaseModel):
    job_id: str
    kind: ResumeKind
    updated_at: float
    position: float | None = None
    sentence: int | None = None
    chunk_id: str | None = None
    media_type: ResumeMediaType | None = None
    base_id: str | None = None


class ResumePositionResponse(BaseModel):
    job_id: str
    entry: ResumePositionEntry | None = None


class ResumePositionDeleteResponse(BaseModel):
    deleted: bool
