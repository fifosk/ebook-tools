"""Schemas for image inspection/regeneration endpoints."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SentenceImageRegenerateRequest(BaseModel):
    """Request payload for manually regenerating a sentence image."""

    use_llm_prompt: Optional[bool] = Field(
        default=None,
        description="When true, regenerate the prompt via the configured LLM instead of using the supplied/stored prompt.",
    )
    context_sentences: Optional[int] = Field(
        default=None,
        ge=0,
        le=50,
        description="How many nearby sentences (before and after) to include as context when generating an LLM prompt.",
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Prompt supplied to the diffusion backend. When omitted, the server reuses the stored prompt.",
    )
    negative_prompt: Optional[str] = Field(
        default=None,
        description="Negative prompt supplied to the diffusion backend.",
    )
    width: Optional[int] = Field(default=None, ge=64, description="Output image width in pixels.")
    height: Optional[int] = Field(default=None, ge=64, description="Output image height in pixels.")
    steps: Optional[int] = Field(default=None, ge=1, description="Diffusion sampling steps.")
    cfg_scale: Optional[float] = Field(default=None, ge=0.0, description="Classifier-free guidance scale.")
    sampler_name: Optional[str] = Field(default=None, description="Sampler identifier accepted by the backend.")
    seed: Optional[int] = Field(default=None, description="Optional deterministic seed.")

    model_config = ConfigDict(extra="forbid")


class SentenceImageInfoResponse(BaseModel):
    """Metadata returned for a sentence image stored in job metadata."""

    job_id: str
    sentence_number: int
    range_fragment: Optional[str] = None
    relative_path: Optional[str] = None
    sentence: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class SentenceImageInfoBatchResponse(BaseModel):
    """Batch metadata returned for multiple sentence images."""

    job_id: str
    items: List[SentenceImageInfoResponse] = Field(default_factory=list)
    missing: List[int] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class SentenceImageRegenerateResponse(BaseModel):
    """Response returned after regenerating a sentence image."""

    job_id: str
    sentence_number: int
    range_fragment: Optional[str] = None
    relative_path: str
    prompt: str
    negative_prompt: str = ""
    width: int
    height: int
    steps: int
    cfg_scale: float
    sampler_name: Optional[str] = None
    seed: Optional[int] = None

    model_config = ConfigDict(extra="forbid")
