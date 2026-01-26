"""Configuration loading utilities.

This module implements a layered configuration system with the following priority
(highest to lowest):

1. CLI flags (runtime overrides)
2. Environment variables (EBOOK_*)
3. Hardware tuning defaults
4. Vault secrets ($EBOOK_VAULT_FILE)
5. Active database snapshot (if enabled)
6. Local config file (config/config.local.json)
7. Default config file (conf/config.json)
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError
from pydub import AudioSegment

from modules import logging_manager

from .constants import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_FFMPEG_PATH,
    DEFAULT_LOCAL_CONFIG_PATH,
    DEFAULT_MODEL,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_THREADS,
    DERIVED_CONFIG_KEYS,
    SENSITIVE_CONFIG_KEYS,
    VAULT_FILE_ENV,
    DEFAULT_JOB_MAX_WORKERS,
)
from .settings import (
    EbookToolsSettings,
    apply_settings_updates,
    load_environment_overrides,
    load_vault_secrets,
)
from .runtime import clear_hardware_tuning_cache, get_hardware_tuning_defaults

logger = logging_manager.get_logger()
console_info = logging_manager.console_info
console_warning = logging_manager.console_warning

# Explicitly set ffmpeg converter for pydub using configurable path
AudioSegment.converter = DEFAULT_FFMPEG_PATH


_ACTIVE_SETTINGS: Optional[EbookToolsSettings] = None
_CONFIG_LOADED_AT: Optional[str] = None
_ACTIVE_SNAPSHOT_ID: Optional[str] = None


# Environment variable to enable/disable database-backed configuration
CONFIG_DB_ENABLED_ENV = "EBOOK_CONFIG_DB_ENABLED"


def _read_config_json(path, verbose: bool = False, label: str = "configuration") -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if verbose:
            console_info("Loaded %s from %s", label, path, logger_obj=logger)
        return data
    except FileNotFoundError:
        if verbose:
            console_info("No %s found at %s.", label, path, logger_obj=logger)
        return {}
    except Exception as e:  # pragma: no cover - log and continue
        if verbose:
            console_warning(
                "Error loading %s from %s: %s. Proceeding without it.",
                label,
                path,
                e,
                logger_obj=logger,
            )
        return {}


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_configuration(
    config_file: Optional[str] = None,
    verbose: bool = False,
    default_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Load the layered configuration and return a dictionary view."""

    global _ACTIVE_SETTINGS

    base_payload: Dict[str, Any] = {}
    default_config = _read_config_json(
        DEFAULT_CONFIG_PATH, verbose=verbose, label="default configuration"
    )
    base_payload = _deep_merge_dict(base_payload, default_config)

    override_path = None
    if config_file:
        override_path = Path(config_file).expanduser()
        if not override_path.is_absolute():
            override_path = (Path.cwd() / override_path).resolve()
    else:
        override_path = DEFAULT_LOCAL_CONFIG_PATH

    override_config = (
        _read_config_json(override_path, verbose=verbose, label="local configuration")
        if override_path
        else {}
    )
    base_payload = _deep_merge_dict(base_payload, override_config)

    if verbose and override_path and not override_config:
        if override_path == DEFAULT_LOCAL_CONFIG_PATH:
            console_info(
                "Proceeding with defaults from %s",
                DEFAULT_CONFIG_PATH,
                logger_obj=logger,
            )
        else:
            console_info(
                "Proceeding with defaults because %s could not be loaded",
                override_path,
                logger_obj=logger,
            )

    # Layer 3: Active database snapshot (if enabled)
    db_config = _load_active_db_snapshot(verbose=verbose)
    if db_config:
        base_payload = _deep_merge_dict(base_payload, db_config)

    try:
        settings = EbookToolsSettings.model_validate(base_payload)
    except ValidationError as exc:
        raise RuntimeError("Invalid configuration detected") from exc

    vault_path = os.environ.get(VAULT_FILE_ENV)
    vault_updates: Dict[str, Any] = {}
    if vault_path:
        vault_updates = load_vault_secrets(Path(vault_path).expanduser())
        if vault_updates:
            logger.info(
                "Loaded secret overrides from vault file at %s",
                vault_path,
                extra={"event": "config.vault.loaded", "console_suppress": True},
            )
    env_overrides = load_environment_overrides()

    settings = apply_settings_updates(settings, dict(vault_updates))
    settings = apply_settings_updates(settings, env_overrides)

    tuning_defaults = get_hardware_tuning_defaults()
    tuning_updates: Dict[str, Any] = {}
    if tuning_defaults:
        recommended_threads = tuning_defaults.get("thread_count")
        if (
            isinstance(recommended_threads, int)
            and recommended_threads > 0
            and settings.thread_count == DEFAULT_THREADS
        ):
            tuning_updates["thread_count"] = recommended_threads

        recommended_queue = tuning_defaults.get("queue_size")
        if (
            isinstance(recommended_queue, int)
            and recommended_queue > 0
            and settings.queue_size == DEFAULT_QUEUE_SIZE
        ):
            tuning_updates["queue_size"] = recommended_queue

        recommended_pipeline = tuning_defaults.get("pipeline_mode")
        if (
            isinstance(recommended_pipeline, bool)
            and recommended_pipeline
            and not settings.pipeline_mode
        ):
            tuning_updates["pipeline_mode"] = recommended_pipeline

        recommended_job_workers = tuning_defaults.get("job_max_workers")
        if (
            isinstance(recommended_job_workers, int)
            and recommended_job_workers > 0
            and settings.job_max_workers == DEFAULT_JOB_MAX_WORKERS
        ):
            tuning_updates["job_max_workers"] = recommended_job_workers

        recommended_slide_mode = tuning_defaults.get("slide_parallelism")
        if (
            isinstance(recommended_slide_mode, str)
            and recommended_slide_mode
            and settings.slide_parallelism == "off"
        ):
            tuning_updates["slide_parallelism"] = recommended_slide_mode

        recommended_slide_workers = tuning_defaults.get("slide_parallel_workers")
        if (
            isinstance(recommended_slide_workers, int)
            and recommended_slide_workers > 0
            and settings.slide_parallel_workers in {None, 0}
        ):
            tuning_updates["slide_parallel_workers"] = recommended_slide_workers

    settings = apply_settings_updates(settings, tuning_updates)

    if default_model is None:
        default_model = DEFAULT_MODEL
    if not settings.ollama_model:
        settings = apply_settings_updates(settings, {"ollama_model": default_model})

    _ACTIVE_SETTINGS = settings

    # Track when config was loaded
    global _CONFIG_LOADED_AT
    from datetime import datetime, timezone
    _CONFIG_LOADED_AT = datetime.now(timezone.utc).isoformat()

    exported = settings.model_dump(
        mode="python",
        exclude={
            "ollama_api_key",
            "tmdb_api_key",
            "omdb_api_key",
            "google_books_api_key",
            "database_url",
            "job_store_url",
        },
    )
    return exported


def _load_active_db_snapshot(verbose: bool = False) -> Dict[str, Any]:
    """Load configuration from the active database snapshot if available.

    The database snapshot is always checked for an active configuration.
    This ensures that settings saved via the admin UI are loaded even
    if EBOOK_CONFIG_DB_ENABLED is not explicitly set.

    Returns:
        Configuration dictionary from active snapshot, or empty dict
    """
    global _ACTIVE_SNAPSHOT_ID

    try:
        from .config_repository import ConfigRepository

        repo = ConfigRepository()
        result = repo.get_active_snapshot()

        if result:
            metadata, config = result
            _ACTIVE_SNAPSHOT_ID = metadata.snapshot_id
            if verbose:
                console_info(
                    "Loaded active config snapshot %s (%s)",
                    metadata.snapshot_id,
                    metadata.label or "no label",
                    logger_obj=logger,
                )
            return config

    except Exception as e:
        if verbose:
            console_warning(
                "Failed to load config from database: %s",
                e,
                logger_obj=logger,
            )
        logger.warning(
            "Failed to load config from database",
            extra={
                "event": "config.db.load_failed",
                "error": str(e),
                "console_suppress": True,
            },
        )

    return {}


def reload_configuration(
    verbose: bool = False,
    default_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Hot-reload configuration from all sources.

    This clears cached settings and reloads from all configuration sources.
    Use this for hot-reloading settings that don't require a restart.

    Args:
        verbose: Whether to log detailed loading information
        default_model: Default model to use if not specified

    Returns:
        The reloaded configuration dictionary
    """
    global _ACTIVE_SETTINGS, _ACTIVE_SNAPSHOT_ID

    # Clear cached settings
    _ACTIVE_SETTINGS = None
    _ACTIVE_SNAPSHOT_ID = None

    # Clear hardware tuning cache
    clear_hardware_tuning_cache()

    # Reload and return new configuration
    config = load_configuration(verbose=verbose, default_model=default_model)

    logger.info(
        "Configuration reloaded",
        extra={"event": "config.reloaded", "console_suppress": True},
    )

    return config


def get_config_state() -> Dict[str, Any]:
    """Get information about the current configuration state.

    Returns:
        Dictionary with config state information:
        - loaded_at: When config was last loaded
        - active_snapshot_id: ID of active DB snapshot (if any)
        - db_enabled: Whether DB config is enabled
    """
    return {
        "loaded_at": _CONFIG_LOADED_AT,
        "active_snapshot_id": _ACTIVE_SNAPSHOT_ID,
        "db_enabled": os.environ.get(CONFIG_DB_ENABLED_ENV, "").lower() in ("1", "true", "yes"),
    }


def save_current_config_to_db(
    *,
    label: Optional[str] = None,
    description: Optional[str] = None,
    created_by: Optional[str] = None,
    activate: bool = False,
) -> Optional[str]:
    """Save the current effective configuration to the database.

    Args:
        label: Optional label for the snapshot
        description: Optional description
        created_by: Username creating the snapshot
        activate: Whether to activate this snapshot

    Returns:
        The snapshot_id if successful, None if DB is not available
    """
    try:
        from .config_repository import ConfigRepository

        config = load_configuration()
        repo = ConfigRepository()

        snapshot_id = repo.save_snapshot(
            config,
            label=label,
            description=description,
            created_by=created_by,
            source="current",
            activate=activate,
        )

        return snapshot_id

    except Exception as e:
        logger.warning(
            "Failed to save config to database: %s",
            e,
            extra={"event": "config.db.save_failed", "error": str(e)},
        )
        return None


def strip_derived_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the configuration without derived runtime keys."""

    excluded = DERIVED_CONFIG_KEYS | SENSITIVE_CONFIG_KEYS
    return {k: v for k, v in config.items() if k not in excluded}


def get_settings() -> EbookToolsSettings:
    """Return the currently loaded :class:`EbookToolsSettings` instance.

    If settings haven't been loaded yet, this calls load_configuration()
    which reads from config files, database snapshots, vault, and env vars.
    """
    global _ACTIVE_SETTINGS
    if _ACTIVE_SETTINGS is None:
        # Load full configuration which sets _ACTIVE_SETTINGS
        load_configuration()
    return _ACTIVE_SETTINGS


__all__ = [
    "get_settings",
    "load_configuration",
    "reload_configuration",
    "strip_derived_config",
    "get_config_state",
    "save_current_config_to_db",
    "CONFIG_DB_ENABLED_ENV",
]
