"""Schemas for the video generation API."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class VideoGenerationRequest(BaseModel):
    """Request payload for video generation."""

    job_id: str = Field(..., description="Identifier of the pipeline job owning the video task.")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific parameters required for rendering.",
    )

    model_config = ConfigDict(extra="allow")


class VideoGenerationResponse(BaseModel):
    """Response payload describing a video generation task."""

    request_id: str = Field(..., description="Server-issued identifier for the render request.")
    job_id: str = Field(..., description="Identifier of the pipeline job that owns the task.")
    status: str = Field(..., description="Current lifecycle state for the render request.")
    output_path: str | None = Field(
        default=None,
        description="Relative path to the rendered video artifact when available.",
    )
    logs_url: str | None = Field(
        default=None,
        description="URL pointing to backend logs or troubleshooting output when available.",
    )

    model_config = ConfigDict(extra="allow")


__all__ = ["VideoGenerationRequest", "VideoGenerationResponse"]
