"""Schemas supporting the Create Book API."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .pipeline_requests import PipelineRequestPayload


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
    source_book_title: str | None = None
    source_book_author: str | None = None
    source_book_genre: str | None = None
    source_book_summary: str | None = None

    @field_validator("input_language", "output_language", "topic", "book_name", "genre")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Field cannot be empty")
        return result

    @field_validator(
        "voice",
        "author",
        "source_book_title",
        "source_book_author",
        "source_book_genre",
        "source_book_summary",
    )
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


class BookCreationSentenceBounds(BaseModel):
    """Supported sentence-count bounds for generated books."""

    min: int
    max: int
    default: int


class BookCreationDefaults(BaseModel):
    """Default generated-book prompt and narration values."""

    topic: str = ""
    book_name: str = ""
    genre: str = ""
    author: str = "Me"
    input_language: str = "English"
    output_language: str = "Arabic"
    voice: str = "gTTS"


class BookCreationPipelineDefaults(BaseModel):
    """Default pipeline settings used by generated-book creation clients."""

    sentences_per_output_file: int = 10
    stitch_full: bool = False
    audio_mode: str = "4"
    audio_bitrate_kbps: int | None = 96
    written_mode: str = "4"
    selected_voice: str = "gTTS"
    generate_audio: bool = True
    output_html: bool = False
    output_pdf: bool = False
    include_transliteration: bool = True
    translation_provider: str = "llm"
    translation_batch_size: int = 10
    transliteration_mode: str = "default"
    enable_lookup_cache: bool = True
    lookup_cache_batch_size: int = 10
    tempo: float = 1.0


class BookCreationGeneratedSourceDefaults(BaseModel):
    """Generated-source defaults layered on top of the shared pipeline form."""

    add_images: bool = False
    image_prompt_pipeline: str = "prompt_plan"
    image_style_template: str = "wireframe"
    image_prompt_context_sentences: int = 0
    image_width: str = "256"
    image_height: str = "256"


class BookCreationOptionsResponse(BaseModel):
    """Non-secret options contract for generated-book creation clients."""

    sentence_bounds: BookCreationSentenceBounds
    defaults: BookCreationDefaults
    pipeline_defaults: BookCreationPipelineDefaults
    generated_source_defaults: BookCreationGeneratedSourceDefaults
    supported_input_languages: List[str] = Field(default_factory=list)
    supported_output_languages: List[str] = Field(default_factory=list)
    supported_voices: List[str] = Field(default_factory=list)


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
    source_book_title: str | None = None
    source_book_author: str | None = None
    source_book_genre: str | None = None
    source_book_summary: str | None = None

    @field_validator("topic", "book_name", "genre")
    @classmethod
    def _validate_required(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty")
        return trimmed

    @field_validator(
        "author",
        "input_language",
        "output_language",
        "voice",
        "source_book_title",
        "source_book_author",
        "source_book_genre",
        "source_book_summary",
    )
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
