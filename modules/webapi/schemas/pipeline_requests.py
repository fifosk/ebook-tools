"""Schemas for pipeline submission and configuration endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ...services.pipeline_service import PipelineInput, PipelineRequest
from ..jobs import PipelineJobStatus


class PipelineInputPayload(BaseModel):
    """Public schema representing :class:`PipelineInput`."""

    input_file: str
    base_output_file: str
    input_language: str
    target_languages: List[str]
    sentences_per_output_file: int = 10
    start_sentence: int = 1
    end_sentence: Optional[int] = None
    stitch_full: bool = False
    generate_audio: bool = True
    audio_mode: str = "1"
    audio_bitrate_kbps: Optional[int] = None
    written_mode: str = "4"
    selected_voice: str = "gTTS"
    output_html: bool = False
    output_pdf: bool = False
    generate_video: bool = False
    add_images: bool = False
    include_transliteration: bool = True
    translation_provider: str = "llm"
    translation_batch_size: int = 10
    transliteration_mode: str = "default"
    transliteration_model: Optional[str] = None
    enable_lookup_cache: bool = True
    lookup_cache_batch_size: int = 10
    tempo: float = 1.0
    voice_overrides: Dict[str, str] = Field(default_factory=dict)
    book_metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dataclass(self) -> PipelineInput:
        payload = self.model_dump()
        return PipelineInput(**payload)


class PipelineDefaultsResponse(BaseModel):
    """Response payload exposing the resolved baseline configuration."""

    config: Dict[str, Any] = Field(default_factory=dict)


class BookContentIndexResponse(BaseModel):
    """Response payload describing inferred chapter ranges for an EPUB."""

    input_file: str
    content_index: Optional[Dict[str, Any]] = None


class ImageNodeAvailabilityRequest(BaseModel):
    """Request payload for image node availability checks."""

    base_urls: List[str] = Field(default_factory=list)


class ImageNodeAvailabilityEntry(BaseModel):
    """Availability result for a single image node."""

    base_url: str
    available: bool


class ImageNodeAvailabilityResponse(BaseModel):
    """Response payload for image node availability checks."""

    nodes: List[ImageNodeAvailabilityEntry] = Field(default_factory=list)
    available: List[str] = Field(default_factory=list)
    unavailable: List[str] = Field(default_factory=list)


class PipelineFileDeleteRequest(BaseModel):
    """Request payload for deleting a stored pipeline input file."""

    path: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Path cannot be empty")
        return trimmed


class PipelineRequestPayload(BaseModel):
    """Schema mirroring :class:`PipelineRequest` for incoming submissions."""

    config: Dict[str, Any] = Field(default_factory=dict)
    environment_overrides: Dict[str, Any] = Field(default_factory=dict)
    pipeline_overrides: Dict[str, Any] = Field(default_factory=dict)
    inputs: PipelineInputPayload
    correlation_id: Optional[str] = None

    def to_pipeline_request(
        self,
        *,
        context=None,
        resolved_config: Optional[Dict[str, Any]] = None,
    ) -> PipelineRequest:
        return PipelineRequest(
            config=dict(resolved_config) if resolved_config is not None else dict(self.config),
            context=context,
            environment_overrides=dict(self.environment_overrides),
            pipeline_overrides=dict(self.pipeline_overrides),
            inputs=self.inputs.to_dataclass(),
            correlation_id=self.correlation_id,
        )


class PipelineSubmissionResponse(BaseModel):
    """Response payload after submitting a pipeline job."""

    job_id: str
    status: PipelineJobStatus
    created_at: datetime
    job_type: str = "pipeline"
