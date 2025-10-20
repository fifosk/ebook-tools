"""Configuration loading utilities."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError
from pydub import AudioSegment

from modules import logging_manager

from .constants import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_FFMPEG_PATH,
    DEFAULT_LOCAL_CONFIG_PATH,
    DEFAULT_MODEL,
    DERIVED_CONFIG_KEYS,
    SENSITIVE_CONFIG_KEYS,
    VAULT_FILE_ENV,
)
from .settings import (
    EbookToolsSettings,
    apply_settings_updates,
    load_environment_overrides,
    load_vault_secrets,
)

logger = logging_manager.get_logger()
console_info = logging_manager.console_info
console_warning = logging_manager.console_warning

# Explicitly set ffmpeg converter for pydub using configurable path
AudioSegment.converter = DEFAULT_FFMPEG_PATH


_ACTIVE_SETTINGS: Optional[EbookToolsSettings] = None


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

    if default_model is None:
        default_model = DEFAULT_MODEL
    if not settings.ollama_model:
        settings = apply_settings_updates(settings, {"ollama_model": default_model})

    _ACTIVE_SETTINGS = settings

    exported = settings.model_dump(
        mode="python",
        exclude={"ollama_api_key", "database_url", "job_store_url"},
    )
    return exported


def strip_derived_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the configuration without derived runtime keys."""

    excluded = DERIVED_CONFIG_KEYS | SENSITIVE_CONFIG_KEYS
    return {k: v for k, v in config.items() if k not in excluded}


def get_settings() -> EbookToolsSettings:
    """Return the currently loaded :class:`EbookToolsSettings` instance."""

    global _ACTIVE_SETTINGS
    if _ACTIVE_SETTINGS is None:
        settings = EbookToolsSettings()
        vault_path = os.environ.get(VAULT_FILE_ENV)
        vault_updates: Dict[str, Any] = {}
        if vault_path:
            vault_updates = load_vault_secrets(Path(vault_path).expanduser())
        env_overrides = load_environment_overrides()
        settings = apply_settings_updates(settings, dict(vault_updates))
        settings = apply_settings_updates(settings, env_overrides)
        _ACTIVE_SETTINGS = settings
    return _ACTIVE_SETTINGS


__all__ = ["get_settings", "load_configuration", "strip_derived_config"]
