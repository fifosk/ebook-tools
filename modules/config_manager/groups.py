"""Grouped configuration models for organized settings management.

This module defines Pydantic models that organize the flat configuration
into logical groups for easier management, validation, and UI presentation.
"""
from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .constants import (
    DEFAULT_BOOKS_RELATIVE,
    DEFAULT_FFMPEG_PATH,
    DEFAULT_JOB_MAX_WORKERS,
    DEFAULT_LIBRARY_ROOT,
    DEFAULT_LLM_SOURCE,
    DEFAULT_LMSTUDIO_URL,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_CLOUD_URL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_THREADS,
    DEFAULT_TRANSLATION_FALLBACK_MODEL,
    DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS,
    DEFAULT_TTS_FALLBACK_VOICE,
)


class ConfigGroup(str, Enum):
    """Enumeration of configuration group names."""

    BACKEND = "backend"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGES = "images"
    TRANSLATION = "translation"
    HIGHLIGHTING = "highlighting"
    STORAGE = "storage"
    PROCESSING = "processing"
    API_KEYS = "api_keys"


# Configuration key metadata for UI display and validation
CONFIG_KEY_METADATA: Dict[str, Dict[str, Any]] = {
    # Backend group
    "thread_count": {
        "display_name": "Thread Count",
        "description": "Number of worker threads for parallel processing",
        "group": ConfigGroup.BACKEND,
        "type": "integer",
        "min": 1,
        "max": 64,
        "requires_restart": True,
    },
    "queue_size": {
        "display_name": "Queue Size",
        "description": "Size of the processing queue",
        "group": ConfigGroup.BACKEND,
        "type": "integer",
        "min": 1,
        "max": 256,
        "requires_restart": True,
    },
    "pipeline_mode": {
        "display_name": "Pipeline Mode",
        "description": "Enable pipelined processing for better throughput",
        "group": ConfigGroup.BACKEND,
        "type": "boolean",
        "requires_restart": True,
    },
    "job_max_workers": {
        "display_name": "Max Job Workers",
        "description": "Maximum concurrent job workers",
        "group": ConfigGroup.BACKEND,
        "type": "integer",
        "min": 1,
        "max": 16,
        "requires_restart": True,
    },
    "use_ramdisk": {
        "display_name": "Use RAM Disk",
        "description": "Use RAM-backed temporary storage for faster I/O",
        "group": ConfigGroup.BACKEND,
        "type": "boolean",
        "requires_restart": True,
    },
    "prefer_pillow_simd": {
        "display_name": "Prefer Pillow SIMD",
        "description": "Use SIMD-optimized Pillow if available",
        "group": ConfigGroup.BACKEND,
        "type": "boolean",
        "requires_restart": True,
    },
    # Audio group
    "tts_backend": {
        "display_name": "TTS Backend",
        "description": "Text-to-speech engine (macos_say or gtts)",
        "group": ConfigGroup.AUDIO,
        "type": "string",
        "choices": ["macos_say", "gtts"],
        "requires_restart": True,
    },
    "tts_executable_path": {
        "display_name": "TTS Executable Path",
        "description": "Custom path to TTS executable",
        "group": ConfigGroup.AUDIO,
        "type": "string",
        "requires_restart": True,
    },
    "selected_voice": {
        "display_name": "Selected Voice",
        "description": "Voice identifier for TTS",
        "group": ConfigGroup.AUDIO,
        "type": "string",
        "requires_restart": False,
    },
    "macos_reading_speed": {
        "display_name": "macOS Reading Speed",
        "description": "Words per minute for macOS TTS",
        "group": ConfigGroup.AUDIO,
        "type": "integer",
        "min": 50,
        "max": 400,
        "requires_restart": False,
    },
    "tempo": {
        "display_name": "Tempo",
        "description": "Audio playback tempo multiplier",
        "group": ConfigGroup.AUDIO,
        "type": "number",
        "min": 0.5,
        "max": 2.0,
        "requires_restart": False,
    },
    "tts_fallback_voice": {
        "display_name": "TTS Fallback Voice",
        "description": "Fallback voice when primary is unavailable",
        "group": ConfigGroup.AUDIO,
        "type": "string",
        "requires_restart": False,
    },
    "audio_api_base_url": {
        "display_name": "Audio API Base URL",
        "description": "HTTP endpoint for server-side audio synthesis",
        "group": ConfigGroup.AUDIO,
        "type": "string",
        "requires_restart": True,
    },
    "audio_api_timeout_seconds": {
        "display_name": "Audio API Timeout",
        "description": "Timeout in seconds for audio API requests",
        "group": ConfigGroup.AUDIO,
        "type": "number",
        "min": 5,
        "max": 600,
        "requires_restart": False,
    },
    "audio_api_poll_interval_seconds": {
        "display_name": "Audio API Poll Interval",
        "description": "Polling interval for async audio operations",
        "group": ConfigGroup.AUDIO,
        "type": "number",
        "min": 0.1,
        "max": 30,
        "requires_restart": False,
    },
    # Video group
    "ffmpeg_path": {
        "display_name": "FFmpeg Path",
        "description": "Path to ffmpeg executable",
        "group": ConfigGroup.VIDEO,
        "type": "string",
        "requires_restart": True,
    },
    "sync_ratio": {
        "display_name": "Sync Ratio",
        "description": "Timing ratio for subtitle alignment",
        "group": ConfigGroup.VIDEO,
        "type": "number",
        "min": 0.5,
        "max": 1.5,
        "requires_restart": False,
    },
    # Images group
    "image_api_base_url": {
        "display_name": "Image API Base URL",
        "description": "Stable Diffusion / Draw Things API endpoint",
        "group": ConfigGroup.IMAGES,
        "type": "string",
        "requires_restart": True,
    },
    "image_api_timeout_seconds": {
        "display_name": "Image API Timeout",
        "description": "Timeout in seconds for image generation",
        "group": ConfigGroup.IMAGES,
        "type": "integer",
        "min": 30,
        "max": 1800,
        "requires_restart": False,
    },
    "image_concurrency": {
        "display_name": "Image Concurrency",
        "description": "Number of concurrent image generation requests",
        "group": ConfigGroup.IMAGES,
        "type": "integer",
        "min": 1,
        "max": 16,
        "requires_restart": False,
    },
    # Translation group
    "llm_source": {
        "display_name": "LLM Source",
        "description": "LLM endpoint source (local, cloud, lmstudio)",
        "group": ConfigGroup.TRANSLATION,
        "type": "string",
        "choices": ["local", "cloud", "lmstudio"],
        "requires_restart": True,
    },
    "ollama_url": {
        "display_name": "Ollama URL",
        "description": "Primary Ollama API endpoint",
        "group": ConfigGroup.TRANSLATION,
        "type": "string",
        "requires_restart": True,
    },
    "ollama_local_url": {
        "display_name": "Ollama Local URL",
        "description": "Local Ollama instance URL",
        "group": ConfigGroup.TRANSLATION,
        "type": "string",
        "requires_restart": True,
    },
    "ollama_cloud_url": {
        "display_name": "Ollama Cloud URL",
        "description": "Ollama Cloud endpoint URL",
        "group": ConfigGroup.TRANSLATION,
        "type": "string",
        "requires_restart": True,
    },
    "lmstudio_url": {
        "display_name": "LM Studio URL",
        "description": "LM Studio API endpoint",
        "group": ConfigGroup.TRANSLATION,
        "type": "string",
        "requires_restart": True,
    },
    "ollama_model": {
        "display_name": "Ollama Model",
        "description": "Model identifier for translation",
        "group": ConfigGroup.TRANSLATION,
        "type": "string",
        "requires_restart": False,
        "dynamic_choices_source": "llm_models",
    },
    "translation_fallback_model": {
        "display_name": "Translation Fallback Model",
        "description": "Fallback model when primary is unavailable",
        "group": ConfigGroup.TRANSLATION,
        "type": "string",
        "requires_restart": False,
        "dynamic_choices_source": "llm_models",
    },
    "translation_llm_timeout_seconds": {
        "display_name": "Translation Timeout",
        "description": "Timeout in seconds for translation requests",
        "group": ConfigGroup.TRANSLATION,
        "type": "number",
        "min": 10,
        "max": 600,
        "requires_restart": False,
    },
    # Highlighting group
    "word_highlighting": {
        "display_name": "Word Highlighting",
        "description": "Enable per-word highlighting in videos",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "boolean",
        "requires_restart": False,
    },
    "highlight_granularity": {
        "display_name": "Highlight Granularity",
        "description": "Granularity of highlighting (word only; character mode deprecated)",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "string",
        "choices": ["word"],  # "character" deprecated - video rendering no longer used
        "requires_restart": False,
    },
    "char_weighted_highlighting_default": {
        "display_name": "Character-Weighted Highlighting",
        "description": "Use character-weighted timing by default",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "boolean",
        "requires_restart": False,
    },
    "char_weighted_punctuation_boost": {
        "display_name": "Punctuation Boost",
        "description": "Boost timing for punctuation in highlighting",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "boolean",
        "requires_restart": False,
    },
    "forced_alignment_enabled": {
        "display_name": "Forced Alignment",
        "description": "Enable heuristic forced alignment",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "boolean",
        "requires_restart": False,
    },
    "forced_alignment_smoothing": {
        "display_name": "Alignment Smoothing",
        "description": "Smoothing method (monotonic_cubic, linear)",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "string",
        "choices": ["monotonic_cubic", "linear"],
        "requires_restart": False,
    },
    "alignment_backend": {
        "display_name": "Alignment Backend",
        "description": "Backend for word alignment",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "string",
        "requires_restart": True,
    },
    "alignment_model": {
        "display_name": "Alignment Model",
        "description": "Model for word alignment",
        "group": ConfigGroup.HIGHLIGHTING,
        "type": "string",
        "requires_restart": True,
    },
    # Storage group
    "working_dir": {
        "display_name": "Working Directory",
        "description": "Root directory for runtime artifacts",
        "group": ConfigGroup.STORAGE,
        "type": "string",
        "requires_restart": True,
    },
    "output_dir": {
        "display_name": "Output Directory",
        "description": "Directory for generated ebook assets",
        "group": ConfigGroup.STORAGE,
        "type": "string",
        "requires_restart": True,
    },
    "tmp_dir": {
        "display_name": "Temporary Directory",
        "description": "Directory for temporary files",
        "group": ConfigGroup.STORAGE,
        "type": "string",
        "requires_restart": True,
    },
    "ebooks_dir": {
        "display_name": "Ebooks Directory",
        "description": "Directory for source EPUB files",
        "group": ConfigGroup.STORAGE,
        "type": "string",
        "requires_restart": True,
    },
    "job_storage_dir": {
        "display_name": "Job Storage Directory",
        "description": "Directory for job persistence",
        "group": ConfigGroup.STORAGE,
        "type": "string",
        "requires_restart": True,
    },
    "storage_base_url": {
        "display_name": "Storage Base URL",
        "description": "Base URL for static asset serving",
        "group": ConfigGroup.STORAGE,
        "type": "string",
        "requires_restart": True,
    },
    "library_root": {
        "display_name": "Library Root",
        "description": "Root directory for library database",
        "group": ConfigGroup.STORAGE,
        "type": "string",
        "requires_restart": True,
    },
    # Processing defaults group
    "sentences_per_output_file": {
        "display_name": "Sentences Per File",
        "description": "Number of sentences per output batch",
        "group": ConfigGroup.PROCESSING,
        "type": "integer",
        "min": 1,
        "max": 100,
        "requires_restart": False,
    },
    "max_words": {
        "display_name": "Max Words",
        "description": "Maximum words per sentence chunk",
        "group": ConfigGroup.PROCESSING,
        "type": "integer",
        "min": 5,
        "max": 100,
        "requires_restart": False,
    },
    "percentile": {
        "display_name": "Percentile",
        "description": "Percentile for max_words suggestion",
        "group": ConfigGroup.PROCESSING,
        "type": "integer",
        "min": 50,
        "max": 100,
        "requires_restart": False,
    },
    "split_on_comma_semicolon": {
        "display_name": "Split on Punctuation",
        "description": "Split long sentences on commas/semicolons",
        "group": ConfigGroup.PROCESSING,
        "type": "boolean",
        "requires_restart": False,
    },
    "include_transliteration": {
        "display_name": "Include Transliteration",
        "description": "Include transliteration for non-Latin scripts",
        "group": ConfigGroup.PROCESSING,
        "type": "boolean",
        "requires_restart": False,
    },
    "generate_audio": {
        "display_name": "Generate Audio",
        "description": "Generate MP3 narration by default",
        "group": ConfigGroup.PROCESSING,
        "type": "boolean",
        "requires_restart": False,
    },
    "output_html": {
        "display_name": "Output HTML",
        "description": "Generate HTML output files",
        "group": ConfigGroup.PROCESSING,
        "type": "boolean",
        "requires_restart": False,
    },
    "output_pdf": {
        "display_name": "Output PDF",
        "description": "Generate PDF output files",
        "group": ConfigGroup.PROCESSING,
        "type": "boolean",
        "requires_restart": False,
    },
    "stitch_full": {
        "display_name": "Stitch Full",
        "description": "Combine batch outputs into full deliverables",
        "group": ConfigGroup.PROCESSING,
        "type": "boolean",
        "requires_restart": False,
    },
    # API Keys group
    "ollama_api_key": {
        "display_name": "Ollama API Key",
        "description": "API key for Ollama Cloud",
        "group": ConfigGroup.API_KEYS,
        "type": "secret",
        "sensitive": True,
        "requires_restart": False,
    },
    "tmdb_api_key": {
        "display_name": "TMDB API Key",
        "description": "API key for The Movie Database (movies/TV metadata)",
        "group": ConfigGroup.API_KEYS,
        "type": "secret",
        "sensitive": True,
        "requires_restart": False,
    },
    "omdb_api_key": {
        "display_name": "OMDb API Key",
        "description": "API key for Open Movie Database (movies/TV metadata)",
        "group": ConfigGroup.API_KEYS,
        "type": "secret",
        "sensitive": True,
        "requires_restart": False,
    },
    "google_books_api_key": {
        "display_name": "Google Books API Key",
        "description": "API key for Google Books (book metadata)",
        "group": ConfigGroup.API_KEYS,
        "type": "secret",
        "sensitive": True,
        "requires_restart": False,
    },
    "database_url": {
        "display_name": "Database URL",
        "description": "Database connection URL",
        "group": ConfigGroup.API_KEYS,
        "type": "secret",
        "sensitive": True,
        "requires_restart": True,
    },
    "job_store_url": {
        "display_name": "Job Store URL",
        "description": "Redis URL for job persistence",
        "group": ConfigGroup.API_KEYS,
        "type": "secret",
        "sensitive": True,
        "requires_restart": True,
    },
}


class BackendConfig(BaseModel):
    """Backend and performance configuration settings."""

    model_config = ConfigDict(extra="forbid")

    thread_count: int = Field(default=DEFAULT_THREADS, ge=1, le=64)
    queue_size: int = Field(default=DEFAULT_QUEUE_SIZE, ge=1, le=256)
    pipeline_mode: bool = False
    job_max_workers: int = Field(default=DEFAULT_JOB_MAX_WORKERS, ge=1, le=16)
    use_ramdisk: bool = True
    prefer_pillow_simd: bool = False


class AudioConfig(BaseModel):
    """Audio and TTS configuration settings."""

    model_config = ConfigDict(extra="forbid")

    tts_backend: str = Field(
        default_factory=lambda: "macos_say" if sys.platform == "darwin" else "gtts"
    )
    tts_executable_path: Optional[str] = None
    selected_voice: str = "macOS-auto"
    macos_reading_speed: int = Field(default=100, ge=50, le=400)
    tempo: float = Field(default=1.0, ge=0.5, le=2.0)
    tts_fallback_voice: str = DEFAULT_TTS_FALLBACK_VOICE
    audio_api_base_url: Optional[str] = None
    audio_api_timeout_seconds: float = Field(default=60.0, ge=5, le=600)
    audio_api_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=30)


class VideoConfig(BaseModel):
    """Video rendering configuration settings."""

    model_config = ConfigDict(extra="forbid")

    ffmpeg_path: Optional[str] = Field(default_factory=lambda: DEFAULT_FFMPEG_PATH)
    sync_ratio: float = Field(default=0.9, ge=0.5, le=1.5)


class ImagesConfig(BaseModel):
    """AI image generation configuration settings."""

    model_config = ConfigDict(extra="forbid")

    image_api_base_url: str = "http://192.168.1.9:7860"
    image_api_timeout_seconds: int = Field(default=180, ge=30, le=1800)
    image_concurrency: int = Field(default=2, ge=1, le=16)


class TranslationConfig(BaseModel):
    """Translation and LLM configuration settings."""

    model_config = ConfigDict(extra="forbid")

    llm_source: str = Field(default=DEFAULT_LLM_SOURCE)
    ollama_url: str = Field(default=DEFAULT_OLLAMA_URL)
    ollama_local_url: str = Field(default=DEFAULT_OLLAMA_URL)
    ollama_cloud_url: str = Field(default=DEFAULT_OLLAMA_CLOUD_URL)
    lmstudio_url: str = Field(default=DEFAULT_LMSTUDIO_URL)
    ollama_model: str = Field(default=DEFAULT_MODEL)
    translation_fallback_model: str = DEFAULT_TRANSLATION_FALLBACK_MODEL
    translation_llm_timeout_seconds: float = Field(
        default=DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS, ge=10, le=600
    )


class HighlightingConfig(BaseModel):
    """Word highlighting and alignment configuration settings."""

    model_config = ConfigDict(extra="forbid")

    word_highlighting: bool = True
    highlight_granularity: str = "word"
    char_weighted_highlighting_default: bool = False
    char_weighted_punctuation_boost: bool = False
    forced_alignment_enabled: bool = False
    forced_alignment_smoothing: Union[float, str] = "monotonic_cubic"
    alignment_backend: Optional[str] = None
    alignment_model: Optional[str] = None
    alignment_model_overrides: Optional[Dict[str, str]] = None


class StorageConfig(BaseModel):
    """Storage and path configuration settings."""

    model_config = ConfigDict(extra="forbid")

    working_dir: str = "output"
    output_dir: str = "output/ebook"
    tmp_dir: str = "tmp"
    ebooks_dir: str = str(DEFAULT_BOOKS_RELATIVE)
    job_storage_dir: str = "storage"
    storage_base_url: str = ""
    library_root: str = str(DEFAULT_LIBRARY_ROOT)


class ProcessingConfig(BaseModel):
    """Default processing options for new jobs."""

    model_config = ConfigDict(extra="forbid")

    sentences_per_output_file: int = Field(default=10, ge=1, le=100)
    max_words: int = Field(default=18, ge=5, le=100)
    percentile: int = Field(default=96, ge=50, le=100)
    split_on_comma_semicolon: bool = False
    include_transliteration: bool = True
    generate_audio: bool = True
    output_html: bool = True
    output_pdf: bool = False
    stitch_full: bool = False


class ApiKeysConfig(BaseModel):
    """API keys and secrets configuration."""

    model_config = ConfigDict(extra="forbid")

    ollama_api_key: Optional[SecretStr] = None
    tmdb_api_key: Optional[SecretStr] = None
    omdb_api_key: Optional[SecretStr] = None
    google_books_api_key: Optional[SecretStr] = None
    database_url: Optional[SecretStr] = None
    job_store_url: Optional[SecretStr] = None


class GroupedConfiguration(BaseModel):
    """Complete grouped configuration with all sections."""

    model_config = ConfigDict(extra="allow")

    backend: BackendConfig = Field(default_factory=BackendConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    highlighting: HighlightingConfig = Field(default_factory=HighlightingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    api_keys: ApiKeysConfig = Field(default_factory=ApiKeysConfig)


# Group display metadata for UI
GROUP_METADATA: Dict[str, Dict[str, str]] = {
    ConfigGroup.BACKEND: {
        "display_name": "Backend & Performance",
        "description": "Thread counts, parallelism, and performance tuning settings",
        "icon": "cpu",
    },
    ConfigGroup.AUDIO: {
        "display_name": "Audio & TTS",
        "description": "Text-to-speech engine, voices, and audio generation settings",
        "icon": "volume-2",
    },
    ConfigGroup.VIDEO: {
        "display_name": "Video",
        "description": "Video rendering backend and FFmpeg settings",
        "icon": "film",
    },
    ConfigGroup.IMAGES: {
        "display_name": "Image Generation",
        "description": "Stable Diffusion / Draw Things API settings",
        "icon": "image",
    },
    ConfigGroup.TRANSLATION: {
        "display_name": "Translation & LLM",
        "description": "Language model endpoints, models, and translation settings",
        "icon": "languages",
    },
    ConfigGroup.HIGHLIGHTING: {
        "display_name": "Word Highlighting",
        "description": "Word-level timing and alignment settings",
        "icon": "highlighter",
    },
    ConfigGroup.STORAGE: {
        "display_name": "Storage & Paths",
        "description": "Directory paths and storage location settings",
        "icon": "folder",
    },
    ConfigGroup.PROCESSING: {
        "display_name": "Processing Defaults",
        "description": "Default options for new job processing",
        "icon": "settings",
    },
    ConfigGroup.API_KEYS: {
        "display_name": "API Keys & Secrets",
        "description": "Authentication keys and secret values",
        "icon": "key",
    },
}


def flat_to_grouped(flat_config: Dict[str, Any]) -> GroupedConfiguration:
    """Convert a flat configuration dictionary to grouped structure.

    Args:
        flat_config: Flat dictionary with all config keys at top level

    Returns:
        GroupedConfiguration with values distributed into groups
    """
    grouped_data: Dict[str, Dict[str, Any]] = {
        "backend": {},
        "audio": {},
        "video": {},
        "images": {},
        "translation": {},
        "highlighting": {},
        "storage": {},
        "processing": {},
        "api_keys": {},
    }

    # Map flat keys to groups based on metadata
    for key, value in flat_config.items():
        if key in CONFIG_KEY_METADATA:
            group = CONFIG_KEY_METADATA[key]["group"].value
            grouped_data[group][key] = value
        elif key == "api_keys" and isinstance(value, dict):
            # Handle nested api_keys from config.json format
            for sub_key, sub_value in value.items():
                if sub_key == "ollama":
                    grouped_data["api_keys"]["ollama_api_key"] = sub_value
                elif sub_key == "tmdb":
                    grouped_data["api_keys"]["tmdb_api_key"] = sub_value
                elif sub_key == "omdb":
                    grouped_data["api_keys"]["omdb_api_key"] = sub_value
                elif sub_key == "google_books":
                    grouped_data["api_keys"]["google_books_api_key"] = sub_value

    return GroupedConfiguration(
        backend=BackendConfig(**grouped_data["backend"]) if grouped_data["backend"] else BackendConfig(),
        audio=AudioConfig(**grouped_data["audio"]) if grouped_data["audio"] else AudioConfig(),
        video=VideoConfig(**grouped_data["video"]) if grouped_data["video"] else VideoConfig(),
        images=ImagesConfig(**grouped_data["images"]) if grouped_data["images"] else ImagesConfig(),
        translation=TranslationConfig(**grouped_data["translation"]) if grouped_data["translation"] else TranslationConfig(),
        highlighting=HighlightingConfig(**grouped_data["highlighting"]) if grouped_data["highlighting"] else HighlightingConfig(),
        storage=StorageConfig(**grouped_data["storage"]) if grouped_data["storage"] else StorageConfig(),
        processing=ProcessingConfig(**grouped_data["processing"]) if grouped_data["processing"] else ProcessingConfig(),
        api_keys=ApiKeysConfig(**grouped_data["api_keys"]) if grouped_data["api_keys"] else ApiKeysConfig(),
    )


def grouped_to_flat(grouped: GroupedConfiguration) -> Dict[str, Any]:
    """Convert grouped configuration back to flat dictionary.

    Args:
        grouped: GroupedConfiguration instance

    Returns:
        Flat dictionary compatible with existing config loading
    """
    flat: Dict[str, Any] = {}

    for group_name in ["backend", "audio", "video", "images", "translation", "highlighting", "storage", "processing"]:
        group_config = getattr(grouped, group_name)
        group_dict = group_config.model_dump(exclude_none=True)
        flat.update(group_dict)

    # Handle api_keys specially - convert to both flat and nested format for compatibility
    api_keys_config = grouped.api_keys.model_dump(exclude_none=True)
    flat.update(api_keys_config)

    # Also add nested api_keys for backward compatibility
    api_keys_nested: Dict[str, str] = {}
    if grouped.api_keys.ollama_api_key:
        api_keys_nested["ollama"] = grouped.api_keys.ollama_api_key.get_secret_value()
    if grouped.api_keys.tmdb_api_key:
        api_keys_nested["tmdb"] = grouped.api_keys.tmdb_api_key.get_secret_value()
    if grouped.api_keys.omdb_api_key:
        api_keys_nested["omdb"] = grouped.api_keys.omdb_api_key.get_secret_value()
    if grouped.api_keys.google_books_api_key:
        api_keys_nested["google_books"] = grouped.api_keys.google_books_api_key.get_secret_value()
    if api_keys_nested:
        flat["api_keys"] = api_keys_nested

    return flat


def get_keys_for_group(group: ConfigGroup) -> List[str]:
    """Get list of configuration keys belonging to a group.

    Args:
        group: The configuration group

    Returns:
        List of key names in the group
    """
    return [
        key for key, meta in CONFIG_KEY_METADATA.items()
        if meta.get("group") == group
    ]


def get_hot_reload_keys() -> List[str]:
    """Get list of configuration keys that can be hot-reloaded.

    Returns:
        List of key names that don't require restart
    """
    return [
        key for key, meta in CONFIG_KEY_METADATA.items()
        if not meta.get("requires_restart", True)
    ]


def get_sensitive_keys() -> List[str]:
    """Get list of sensitive configuration keys.

    Returns:
        List of key names that contain sensitive data
    """
    return [
        key for key, meta in CONFIG_KEY_METADATA.items()
        if meta.get("sensitive", False)
    ]


__all__ = [
    "ConfigGroup",
    "CONFIG_KEY_METADATA",
    "GROUP_METADATA",
    "BackendConfig",
    "AudioConfig",
    "VideoConfig",
    "ImagesConfig",
    "TranslationConfig",
    "HighlightingConfig",
    "StorageConfig",
    "ProcessingConfig",
    "ApiKeysConfig",
    "GroupedConfiguration",
    "flat_to_grouped",
    "grouped_to_flat",
    "get_keys_for_group",
    "get_hot_reload_keys",
    "get_sensitive_keys",
]
