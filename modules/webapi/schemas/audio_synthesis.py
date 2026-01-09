"""Schemas for audio synthesis endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AudioSynthesisRequest(BaseModel):
    """Payload describing a text-to-speech synthesis request."""

    text: str = Field(..., description="Text content that should be spoken aloud.")
    voice: Optional[str] = Field(
        default=None,
        description="Optional voice identifier understood by the configured backend.",
    )
    speed: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Optional speaking rate hint expressed as words per minute.",
    )
    language: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=16,
        description="Optional language code override for synthesis (e.g. 'en' or 'es').",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Text must not be empty.")
        return value.strip()

    @field_validator("voice")
    @classmethod
    def _validate_voice(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("Voice must not be empty when provided.")
        return value.strip()

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Language must not be empty when provided.")
        return stripped


class AudioSynthesisError(BaseModel):
    """Standard error payload returned by audio synthesis routes."""

    error: str = Field(..., description="Stable error identifier.")
    message: str = Field(..., description="Human readable explanation of the error.")
