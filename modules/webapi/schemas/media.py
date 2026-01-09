"""Schemas for media generation endpoints."""

from __future__ import annotations

from typing import Dict, Optional

from typing_extensions import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...services.video_payloads import VideoRenderRequestPayload
from .audio_synthesis import AudioSynthesisRequest


class MediaAPISettings(BaseModel):
    """Optional override values used when dispatching to external media APIs."""

    base_url: Optional[str] = Field(
        default=None,
        description="Explicit API base URL that should override the configured endpoint.",
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional HTTP headers forwarded to the downstream API.",
    )

    model_config = ConfigDict(extra="forbid")


class AudioGenerationParameters(BaseModel):
    """Audio-specific options supplied when requesting media generation."""

    request: "AudioSynthesisRequest" = Field(
        ..., description="Normalised synthesis request for the audio backend."
    )
    output_filename: Optional[str] = Field(
        default=None,
        description="Desired filename for the generated audio artifact.",
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Optional correlation identifier propagated to downstream services.",
    )

    model_config = ConfigDict(extra="forbid")


class VideoGenerationParameters(BaseModel):
    """Video-specific options supplied when requesting media generation."""

    request: "VideoRenderRequestPayload" = Field(
        ..., description="Rendering request passed through to the video job manager."
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Optional correlation identifier propagated to downstream services.",
    )

    model_config = ConfigDict(extra="forbid")


class MediaGenerationRequestPayload(BaseModel):
    """Request payload describing a media generation request."""

    job_id: str = Field(..., description="Identifier of the pipeline job to enrich with media.")
    media_type: Literal["audio", "video"] = Field(
        ..., description="Type of media that should be generated (either 'audio' or 'video')."
    )
    audio: Optional[AudioGenerationParameters] = Field(
        default=None,
        description="Audio-specific request settings when ``media_type`` is 'audio'.",
    )
    video: Optional[VideoGenerationParameters] = Field(
        default=None,
        description="Video-specific request settings when ``media_type`` is 'video'.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional free-form context describing why the media was requested.",
    )
    api: Optional[MediaAPISettings] = Field(
        default=None,
        description="Optional overrides applied when calling remote media APIs.",
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_parameters(self) -> "MediaGenerationRequestPayload":
        if self.media_type == "audio" and self.audio is None:
            raise ValueError("Audio parameters must be supplied when media_type is 'audio'.")
        if self.media_type == "video" and self.video is None:
            raise ValueError("Video parameters must be supplied when media_type is 'video'.")
        return self


class MediaGenerationResponse(BaseModel):
    """Success payload acknowledging that media generation has been queued."""

    request_id: str = Field(..., description="Server-issued identifier tracking the request.")
    status: str = Field(..., description="Current lifecycle state for the request (e.g. 'accepted').")
    job_id: str = Field(..., description="Identifier of the job targeted by the request.")
    media_type: str = Field(..., description="Type of media that will be generated.")
    requested_by: str = Field(..., description="Username that initiated the request.")
    parameters: Dict[str, object] = Field(
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
    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation identifier propagated to downstream media services, when used.",
    )


class MediaErrorResponse(BaseModel):
    """Error payload returned when media operations cannot proceed."""

    error: str = Field(..., description="Stable error identifier for programmatic handling.")
    message: str = Field(..., description="Human readable explanation of the failure.")


# Resolve forward references now that dependent models are defined.
AudioGenerationParameters.model_rebuild()
VideoGenerationParameters.model_rebuild()
MediaGenerationRequestPayload.model_rebuild()
