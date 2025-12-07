"""Schemas supporting the Create Book API."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import PipelineRequestPayload


class BookCreationRequest(BaseModel):
    """Incoming payload for synthesising a new book pipeline job."""

    model_config = ConfigDict(extra="forbid")

    input_language: str
    output_language: str
    voice: str | None = None
    num_sentences: int = Field(default=10, ge=1, le=500)
    topic: str
    book_name: str
    genre: str
    author: str = "Me"

    @field_validator("input_language", "output_language", "topic", "book_name", "genre")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Field cannot be empty")
        return result

    @field_validator("voice", "author")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class BookCreationResponse(BaseModel):
    """Response payload detailing the prepared synthetic book artefacts."""

    job_id: str | None = None
    status: str
    metadata: Dict[str, Any]
    messages: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    epub_path: str | None = None
    input_file: str | None = None
    sentences_preview: List[str] = Field(default_factory=list)


class BookGenerationJobRequest(BaseModel):
    """Payload for submitting a managed book-generation pipeline job."""

    model_config = ConfigDict(extra="forbid")

    topic: str
    book_name: str
    genre: str
    author: str = "Me"
    num_sentences: int = Field(default=10, ge=1, le=500)
    input_language: str | None = None
    output_language: str | None = None
    voice: str | None = None

    @field_validator("topic", "book_name", "genre")
    @classmethod
    def _validate_required(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty")
        return trimmed

    @field_validator("author", "input_language", "output_language", "voice")
    @classmethod
    def _validate_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class BookGenerationJobSubmission(BaseModel):
    """Full submission payload for the managed book-generation pipeline job."""

    model_config = ConfigDict(extra="forbid")

    generator: BookGenerationJobRequest
    pipeline: PipelineRequestPayload
