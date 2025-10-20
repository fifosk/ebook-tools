"""Pydantic models and helper utilities for configuration values."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from modules import logging_manager

from .constants import (
    DEFAULT_BOOKS_RELATIVE,
    DEFAULT_LLM_SOURCE,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_CLOUD_URL,
    DEFAULT_OLLAMA_URL,
    VALID_LLM_SOURCES,
)

logger = logging_manager.get_logger()


class EbookToolsSettings(BaseModel):
    """Typed representation of the application configuration."""

    model_config = ConfigDict(extra="allow")

    input_file: str = ""
    ebooks_dir: str = str(DEFAULT_BOOKS_RELATIVE)
    base_output_file: str = ""
    input_language: str = "English"
    target_languages: list[str] = Field(default_factory=lambda: ["Arabic"])
    ollama_model: str = DEFAULT_MODEL
    generate_audio: bool = True
    generate_video: bool = True
    sentences_per_output_file: int = 10
    start_sentence: int = 1
    end_sentence: Optional[int] = None
    max_words: int = 18
    percentile: int = 96
    split_on_comma_semicolon: bool = False
    audio_mode: str = "1"
    written_mode: str = "4"
    include_transliteration: bool = False
    debug: bool = False
    output_html: bool = True
    output_pdf: bool = False
    stitch_full: bool = False
    selected_voice: str = "gTTS"
    book_title: str = "Unknown Title"
    book_author: str = "Unknown Author"
    book_year: str = "Unknown Year"
    book_summary: str = "No summary provided."
    book_cover_file: Optional[str] = None
    auto_metadata: bool = True
    macos_reading_speed: int = 100
    tempo: float = 1.0
    sync_ratio: float = 0.9
    word_highlighting: bool = True
    highlight_granularity: str = "word"
    forced_alignment_enabled: bool = False
    forced_alignment_smoothing: str = "monotonic_cubic"
    slide_parallelism: str = "off"
    slide_parallel_workers: Optional[int] = None
    prefer_pillow_simd: bool = False
    slide_render_benchmark: bool = False
    working_dir: str = "output"
    output_dir: str = "output/ebook"
    tmp_dir: str = "tmp"
    ollama_url: str = DEFAULT_OLLAMA_URL
    llm_source: str = DEFAULT_LLM_SOURCE
    ollama_local_url: str = DEFAULT_OLLAMA_URL
    ollama_cloud_url: str = DEFAULT_OLLAMA_CLOUD_URL
    ffmpeg_path: Optional[str] = None
    thread_count: int = 5
    queue_size: int = 20
    pipeline_mode: bool = False
    use_ramdisk: bool = True
    ollama_api_key: Optional[SecretStr] = None
    database_url: Optional[SecretStr] = None
    job_store_url: Optional[SecretStr] = None
    job_max_workers: int = 2


class EnvironmentOverrides(BaseSettings):
    """Configuration overrides sourced from environment variables."""

    model_config = SettingsConfigDict(env_prefix="", env_nested_delimiter="__", extra="ignore")

    working_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_WORKING_DIR")
    )
    output_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_OUTPUT_DIR")
    )
    tmp_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_TMP_DIR")
    )
    ebooks_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOKS_DIR", "EBOOK_EBOOKS_DIR")
    )
    ffmpeg_path: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("FFMPEG_PATH", "EBOOK_FFMPEG_PATH")
    )
    ollama_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("OLLAMA_URL", "EBOOK_OLLAMA_URL")
    )
    llm_source: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("LLM_SOURCE", "EBOOK_LLM_SOURCE")
    )
    ollama_local_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OLLAMA_LOCAL_URL", "EBOOK_OLLAMA_LOCAL_URL"),
    )
    ollama_cloud_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OLLAMA_CLOUD_URL", "EBOOK_OLLAMA_CLOUD_URL"),
    )
    ollama_model: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_OLLAMA_MODEL")
    )
    thread_count: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_THREAD_COUNT")
    )
    queue_size: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_QUEUE_SIZE")
    )
    pipeline_mode: Optional[bool] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_PIPELINE_MODE")
    )
    use_ramdisk: Optional[bool] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_USE_RAMDISK")
    )
    ollama_api_key: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("OLLAMA_API_KEY", "EBOOK_OLLAMA_API_KEY")
    )
    database_url: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("DATABASE_URL", "EBOOK_DATABASE_URL")
    )
    job_store_url: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("JOB_STORE_URL", "EBOOK_JOB_STORE_URL")
    )
    job_max_workers: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_JOB_MAX_WORKERS")
    )


def load_environment_overrides() -> Dict[str, Any]:
    """Return configuration overrides sourced from environment variables."""

    try:
        overrides = EnvironmentOverrides()
    except ValidationError as exc:
        logger.warning(
            "Invalid environment configuration detected; using defaults.",
            extra={
                "event": "config.env.validation_error",
                "error": str(exc),
                "console_suppress": True,
            },
        )
        return {}
    return overrides.model_dump(exclude_none=True)


def load_vault_secrets(path: Path) -> Dict[str, SecretStr]:
    """Attempt to read secret values from a vault-style JSON document."""

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        logger.debug(
            "Vault secret file not found at %s; skipping.",
            path,
            extra={"event": "config.vault.missing", "console_suppress": True},
        )
        return {}
    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to parse vault secret file at %s: %s",
            path,
            exc,
            extra={"event": "config.vault.invalid", "console_suppress": True},
        )
        return {}

    secrets: Dict[str, SecretStr] = {}
    for key in ("ollama_api_key", "database_url", "job_store_url"):
        value = payload.get(key)
        if value:
            secrets[key] = SecretStr(str(value))
    return secrets


def apply_settings_updates(
    settings: EbookToolsSettings, updates: Dict[str, Any]
) -> EbookToolsSettings:
    """Return a copy of ``settings`` updated with ``updates`` if any values exist."""

    if not updates:
        return settings
    return settings.model_copy(update=updates)


def normalize_llm_source(candidate: Any, *, default: str = DEFAULT_LLM_SOURCE) -> str:
    """Return a normalised LLM source identifier."""

    if isinstance(candidate, str):
        normalized = candidate.strip().lower()
        if normalized in VALID_LLM_SOURCES:
            return normalized
    if default in VALID_LLM_SOURCES:
        return default
    return "local"


__all__ = [
    "EbookToolsSettings",
    "EnvironmentOverrides",
    "apply_settings_updates",
    "load_environment_overrides",
    "load_vault_secrets",
    "normalize_llm_source",
]
