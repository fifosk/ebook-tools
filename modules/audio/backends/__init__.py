"""Registry and helpers for TTS backends."""

from __future__ import annotations

import sys
from typing import Any, Mapping, MutableMapping, Optional, Type

from modules import config_manager as cfg

from .base import BaseTTSBackend, TTSBackendError
from .gtts import GTTSBackend
from .macos import MacOSTTSBackend


_BACKENDS: MutableMapping[str, Type[BaseTTSBackend]] = {
    GTTSBackend.name: GTTSBackend,
    MacOSTTSBackend.name: MacOSTTSBackend,
}

_BACKEND_ALIASES = {
    "macos": MacOSTTSBackend.name,
    "macos_say": MacOSTTSBackend.name,
    "gtts": GTTSBackend.name,
}


def get_default_backend_name() -> str:
    """Return the platform default backend identifier."""

    return MacOSTTSBackend.name if sys.platform == "darwin" else GTTSBackend.name


def register_backend(name: str, backend_cls: Type[BaseTTSBackend]) -> None:
    """Register ``backend_cls`` under ``name``."""

    key = name.lower()
    _BACKENDS[key] = backend_cls


def create_backend(
    name: str,
    *,
    executable_path: Optional[str] = None,
) -> BaseTTSBackend:
    """Instantiate the backend registered as ``name``."""

    key = name.lower()
    backend_cls = _BACKENDS.get(key)
    if backend_cls is None:
        raise KeyError(f"Unknown TTS backend: {name}")
    return backend_cls(executable_path=executable_path)


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
    if not normalized:
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


def _get_backend_settings(config: Optional[Any]) -> tuple[str, Optional[str]]:
    backend_name: Optional[str] = None
    executable_override: Optional[str] = None

    if config is not None:
        if isinstance(config, Mapping):
            backend_name = _extract_value(config, "tts_backend")
            executable_override = _extract_value(config, "tts_executable_path")
        else:
            backend_name = _extract_from_object(config, "tts_backend")
            executable_override = _extract_from_object(config, "tts_executable_path")

    if backend_name is None or backend_name == "auto":
        settings = cfg.get_settings()
        backend_name = _extract_from_object(settings, "tts_backend") or backend_name
        executable_override = (
            _extract_from_object(settings, "tts_executable_path") or executable_override
        )

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
    "MacOSTTSBackend",
    "TTSBackendError",
    "create_backend",
    "get_default_backend_name",
    "get_tts_backend",
    "register_backend",
]

