"""Schemas for media generation endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MediaGenerationRequestPayload(BaseModel):
    """Request payload describing a media generation request."""

    job_id: str = Field(..., description="Identifier of the pipeline job to enrich with media.")
    media_type: str = Field(
        ..., description="Type of media that should be generated (e.g. 'audio' or 'video')."
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional backend-specific parameters forwarded to the renderer.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional free-form context describing why the media was requested.",
    )


class MediaGenerationResponse(BaseModel):
    """Success payload acknowledging that media generation has been queued."""

    request_id: str = Field(..., description="Server-issued identifier tracking the request.")
    status: str = Field(..., description="Current lifecycle state for the request (e.g. 'accepted').")
    job_id: str = Field(..., description="Identifier of the job targeted by the request.")
    media_type: str = Field(..., description="Type of media that will be generated.")
    requested_by: str = Field(..., description="Username that initiated the request.")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Normalised parameters that will be applied during generation.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional context carried over from the request payload.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional human readable confirmation message returned by the server.",
    )
    artifact_path: Optional[str] = Field(
        default=None,
        description="Relative path to the generated artifact inside the job directory, when available.",
    )
    artifact_url: Optional[str] = Field(
        default=None,
        description="Public URL for downloading the generated artifact, when configured.",
    )


class MediaErrorResponse(BaseModel):
    """Error payload returned when media operations cannot proceed."""

    error: str = Field(..., description="Stable error identifier for programmatic handling.")
    message: str = Field(..., description="Human readable explanation of the failure.")
