"""High-level configuration management for ebook-tools."""
from __future__ import annotations

from pathlib import Path

from modules import logging_manager

from .constants import (
    CONF_DIR,
    DEFAULT_BOOKS_RELATIVE,
    DEFAULT_CONFIG_PATH,
    DEFAULT_FFMPEG_PATH,
    DEFAULT_LLM_SOURCE,
    DEFAULT_LOCAL_CONFIG_PATH,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_CLOUD_URL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_LMSTUDIO_URL,
    DEFAULT_OUTPUT_RELATIVE,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_JOB_MAX_WORKERS,
    DEFAULT_TRANSLATION_FALLBACK_MODEL,
    DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS,
    DEFAULT_TTS_FALLBACK_VOICE,
    DEFAULT_COVERS_RELATIVE,
    DEFAULT_LIBRARY_ROOT,
    DEFAULT_SMB_BOOKS_PATH,
    DEFAULT_SMB_OUTPUT_PATH,
    DEFAULT_THREADS,
    DEFAULT_TMP_RELATIVE,
    DEFAULT_WORKING_RELATIVE,
    DERIVED_CONFIG_KEYS,
    DERIVED_REFINED_FILENAME_TEMPLATE,
    DERIVED_RUNTIME_DIRNAME,
    MODULE_DIR,
    SCRIPT_DIR,
    SENSITIVE_CONFIG_KEYS,
    VALID_LLM_SOURCES,
    VAULT_FILE_ENV,
)
from .loader import get_settings, load_configuration, strip_derived_config
from .paths import resolve_directory, resolve_file_path
from .runtime import (
    RuntimeContext,
    build_runtime_context,
    cleanup_environment,
    clear_runtime_context,
    get_queue_size,
    get_runtime_context,
    get_hardware_tuning_defaults,
    get_thread_count,
    is_pipeline_mode,
    register_tmp_dir_preservation,
    release_tmp_dir_preservation,
    set_runtime_context,
)
from .settings import EbookToolsSettings, EnvironmentOverrides, normalize_llm_source

logger = logging_manager.get_logger()
console_info = logging_manager.console_info
console_warning = logging_manager.console_warning


def get_llm_source() -> str:
    """Return the active LLM source identifier."""

    context = get_runtime_context(None)
    if context:
        return context.llm_source
    settings = get_settings()
    return normalize_llm_source(
        getattr(settings, "llm_source", DEFAULT_LLM_SOURCE),
        default=DEFAULT_LLM_SOURCE,
    )


def get_local_ollama_url() -> str:
    """Return the configured local Ollama endpoint URL."""

    context = get_runtime_context(None)
    if context:
        return context.local_ollama_url
    settings = get_settings()
    candidate = getattr(settings, "ollama_local_url", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return DEFAULT_OLLAMA_URL


def get_cloud_ollama_url() -> str:
    """Return the configured Ollama Cloud endpoint URL."""

    context = get_runtime_context(None)
    if context:
        return context.cloud_ollama_url
    settings = get_settings()
    candidate = getattr(settings, "ollama_cloud_url", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return DEFAULT_OLLAMA_CLOUD_URL


def get_lmstudio_url() -> str:
    """Return the configured LM Studio endpoint URL."""

    context = get_runtime_context(None)
    if context:
        return context.lmstudio_url
    settings = get_settings()
    candidate = getattr(settings, "lmstudio_url", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return DEFAULT_LMSTUDIO_URL


def get_ollama_url() -> str:
    """Return the Ollama endpoint URL for the active runtime context."""

    context = get_runtime_context(None)
    if context:
        return context.ollama_url

    settings = get_settings()
    candidate = getattr(settings, "ollama_url", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()

    source = get_llm_source()
    if source == "cloud":
        return get_cloud_ollama_url()
    if source == "lmstudio":
        return get_lmstudio_url()
    return get_local_ollama_url()


def get_translation_fallback_model() -> str:
    """Return the configured LLM model for translation fallbacks."""

    settings = get_settings()
    candidate = getattr(settings, "translation_fallback_model", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return DEFAULT_TRANSLATION_FALLBACK_MODEL


def get_translation_llm_timeout_seconds() -> float:
    """Return the per-sentence LLM timeout threshold used to trigger fallbacks."""

    settings = get_settings()
    candidate = getattr(settings, "translation_llm_timeout_seconds", None)
    try:
        value = float(candidate)
    except (TypeError, ValueError):
        value = DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS
    return value


def get_tts_fallback_voice() -> str:
    """Return the configured fallback voice for TTS failures."""

    settings = get_settings()
    candidate = getattr(settings, "tts_fallback_voice", None)
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return DEFAULT_TTS_FALLBACK_VOICE


def get_library_root(*, create: bool = True) -> Path:
    """Return the configured library root directory, creating it when requested."""

    settings = get_settings()
    raw_value = getattr(settings, "library_root", None)
    if isinstance(raw_value, str) and raw_value.strip():
        candidate = Path(raw_value.strip()).expanduser()
    else:
        candidate = DEFAULT_LIBRARY_ROOT

    if not candidate.is_absolute():
        candidate = (MODULE_DIR.parent / candidate).resolve()

    if create:
        candidate.mkdir(parents=True, exist_ok=True)

    return candidate


__all__ = [
    "RuntimeContext",
    "EbookToolsSettings",
    "EnvironmentOverrides",
    "build_runtime_context",
    "cleanup_environment",
    "clear_runtime_context",
    "get_cloud_ollama_url",
    "get_llm_source",
    "get_local_ollama_url",
    "get_lmstudio_url",
    "get_ollama_url",
    "get_translation_fallback_model",
    "get_translation_llm_timeout_seconds",
    "get_tts_fallback_voice",
    "get_library_root",
    "get_queue_size",
    "get_runtime_context",
    "get_hardware_tuning_defaults",
    "get_settings",
    "get_thread_count",
    "is_pipeline_mode",
    "register_tmp_dir_preservation",
    "release_tmp_dir_preservation",
    "load_configuration",
    "resolve_directory",
    "resolve_file_path",
    "set_runtime_context",
    "strip_derived_config",
    "CONF_DIR",
    "DEFAULT_BOOKS_RELATIVE",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_FFMPEG_PATH",
    "DEFAULT_LLM_SOURCE",
    "DEFAULT_LOCAL_CONFIG_PATH",
    "DEFAULT_MODEL",
    "DEFAULT_OLLAMA_CLOUD_URL",
    "DEFAULT_OLLAMA_URL",
    "DEFAULT_OUTPUT_RELATIVE",
    "DEFAULT_QUEUE_SIZE",
    "DEFAULT_JOB_MAX_WORKERS",
    "DEFAULT_TRANSLATION_FALLBACK_MODEL",
    "DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS",
    "DEFAULT_TTS_FALLBACK_VOICE",
    "DEFAULT_COVERS_RELATIVE",
    "DEFAULT_SMB_BOOKS_PATH",
    "DEFAULT_SMB_OUTPUT_PATH",
    "DEFAULT_THREADS",
    "DEFAULT_TMP_RELATIVE",
    "DEFAULT_WORKING_RELATIVE",
    "DERIVED_CONFIG_KEYS",
    "DERIVED_REFINED_FILENAME_TEMPLATE",
    "DERIVED_RUNTIME_DIRNAME",
    "MODULE_DIR",
    "SCRIPT_DIR",
    "SENSITIVE_CONFIG_KEYS",
    "VALID_LLM_SOURCES",
    "VAULT_FILE_ENV",
    "console_info",
    "console_warning",
    "logger",
]
