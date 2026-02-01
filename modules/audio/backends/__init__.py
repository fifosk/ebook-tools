"""Registry and helpers for TTS backends."""

from __future__ import annotations

import sys
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Type

from modules import config_manager as cfg

from ..config import get_tts_config
from .base import BaseTTSBackend, SynthesisResult, TTSBackendError
from .gtts import GTTSBackend
from .macos_say import MacOSSayBackend, MacOSTTSBackend
from .piper import PiperTTSBackend


_BACKENDS: MutableMapping[str, Type[BaseTTSBackend]] = {}
_BACKEND_ALIASES: MutableMapping[str, str] = {}
_BACKEND_EXECUTABLE_DEFAULTS: MutableMapping[str, str] = {}
_CONFIG_DEFAULT_BACKEND: Optional[str] = None

_EXECUTABLE_OVERRIDE_KEYS = (
    "tts_executable_path",
    "tts_executable",
    "say_path",
)


def _normalize_backend_key(name: str) -> str:
    return name.strip().lower()


def register_backend(name: str, backend_cls: Type[BaseTTSBackend]) -> None:
    """Register ``backend_cls`` under ``name``."""

    key = _normalize_backend_key(name)
    _BACKENDS[key] = backend_cls
    _BACKEND_ALIASES.setdefault(key, key)


def _register_builtin_backends() -> None:
    register_backend(GTTSBackend.name, GTTSBackend)
    register_backend(MacOSSayBackend.name, MacOSSayBackend)
    register_backend(PiperTTSBackend.name, PiperTTSBackend)


def _iter_aliases(candidate: Any) -> Iterable[str]:
    if isinstance(candidate, str):
        yield candidate
        return
    if isinstance(candidate, Iterable):
        for item in candidate:
            if isinstance(item, str):
                yield item


def _initialize_from_media_config() -> None:
    global _CONFIG_DEFAULT_BACKEND

    config = get_tts_config()
    configured_default = config.get("default_backend")
    if isinstance(configured_default, str) and configured_default.strip():
        _CONFIG_DEFAULT_BACKEND = configured_default.strip()

    backends_section = config.get("backends", {})
    if not isinstance(backends_section, Mapping):
        return

    for name, backend_cfg in backends_section.items():
        if not isinstance(name, str):
            continue
        normalized_name = _normalize_backend_key(name)
        if normalized_name not in _BACKENDS:
            continue
        if isinstance(backend_cfg, Mapping):
            aliases = backend_cfg.get("aliases", [])
            for alias in _iter_aliases(aliases):
                alias_key = alias.strip().lower()
                if alias_key:
                    _BACKEND_ALIASES[alias_key] = normalized_name
            executable = backend_cfg.get("executable")
            if isinstance(executable, str) and executable.strip():
                _BACKEND_EXECUTABLE_DEFAULTS[normalized_name] = executable.strip()


def _bootstrap_registry() -> None:
    _register_builtin_backends()
    _initialize_from_media_config()
    # Preserve historical alias even if the media configuration is absent.
    _BACKEND_ALIASES.setdefault("macos", MacOSSayBackend.name)
    _BACKEND_ALIASES.setdefault("macos_say", MacOSSayBackend.name)
    _BACKEND_ALIASES.setdefault("gtts", GTTSBackend.name)
    _BACKEND_ALIASES.setdefault("piper", PiperTTSBackend.name)


_bootstrap_registry()


def get_default_backend_name() -> str:
    """Return the platform default backend identifier."""

    if isinstance(_CONFIG_DEFAULT_BACKEND, str):
        normalized = _CONFIG_DEFAULT_BACKEND.strip().lower()
        if normalized and normalized != "auto":
            resolved = _BACKEND_ALIASES.get(normalized, normalized)
            if resolved in _BACKENDS:
                return resolved

    return MacOSSayBackend.name if sys.platform == "darwin" else GTTSBackend.name


def create_backend(
    name: str,
    *,
    executable_path: Optional[str] = None,
) -> BaseTTSBackend:
    """Instantiate the backend registered as ``name``."""

    key = _resolve_backend_name(name)
    backend_cls = _BACKENDS.get(key)
    if backend_cls is None:
        raise KeyError(f"Unknown TTS backend: {name}")
    executable_override = executable_path
    if executable_override is None:
        executable_override = _BACKEND_EXECUTABLE_DEFAULTS.get(key)
    return backend_cls(executable_path=executable_override)


def _coerce_backend_name(value: Optional[str]) -> str:
    if value is None:
        return get_default_backend_name()

    normalized = value.strip().lower()
    if not normalized:
        return get_default_backend_name()
    if normalized == "auto":
        return get_default_backend_name()
    return normalized


def _resolve_backend_name(config_backend: str) -> str:
    normalized = config_backend.strip().lower()
    if not normalized or normalized == "auto":
        return get_default_backend_name()
    return _BACKEND_ALIASES.get(normalized, normalized)


def _extract_value(source: Mapping[str, Any], key: str) -> Optional[str]:
    value = source.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_from_object(config: Any, key: str) -> Optional[str]:
    value = getattr(config, key, None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_executable_override(source: Any) -> Optional[str]:
    for key in _EXECUTABLE_OVERRIDE_KEYS:
        if isinstance(source, Mapping):
            value = _extract_value(source, key)
        else:
            value = _extract_from_object(source, key)
        if value:
            return value
    return None


def _get_backend_settings(config: Optional[Any]) -> tuple[str, Optional[str]]:
    backend_name: Optional[str] = None
    executable_override: Optional[str] = None

    if config is not None:
        if isinstance(config, Mapping):
            backend_name = _extract_value(config, "tts_backend")
            executable_override = _extract_executable_override(config)
        else:
            backend_name = _extract_from_object(config, "tts_backend")
            executable_override = _extract_executable_override(config)

    if backend_name is None or backend_name == "auto":
        settings = cfg.get_settings()
        backend_name = _extract_from_object(settings, "tts_backend") or backend_name
        executable_override = _extract_executable_override(settings) or executable_override

    backend_name = _resolve_backend_name(_coerce_backend_name(backend_name))
    return backend_name, executable_override


def get_tts_backend(config: Optional[Any] = None) -> BaseTTSBackend:
    """Return an instantiated backend based on ``config`` and defaults."""

    backend_name, executable_override = _get_backend_settings(config)
    if backend_name not in _BACKENDS:
        raise KeyError(f"Unsupported TTS backend '{backend_name}'")
    return create_backend(backend_name, executable_path=executable_override)


__all__ = [
    "BaseTTSBackend",
    "GTTSBackend",
    "MacOSSayBackend",
    "MacOSTTSBackend",
    "PiperTTSBackend",
    "SynthesisResult",
    "TTSBackendError",
    "create_backend",
    "get_default_backend_name",
    "get_tts_backend",
    "register_backend",
]
