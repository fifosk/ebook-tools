"""Configuration helpers for audio and text-to-speech services."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

import yaml

_MEDIA_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "media.yaml"


@lru_cache(maxsize=1)
def load_media_config(path: Optional[str] = None) -> Mapping[str, Any]:
    """Return the parsed media configuration document.

    The loader accepts an optional ``path`` override primarily intended for
    testing. When omitted, the canonical ``config/media.yaml`` file bundled with
    the repository is used.  Missing configuration files are treated as an
    empty mapping to preserve backwards compatibility with earlier deployments
    that relied exclusively on JSON configuration.
    """

    candidate = Path(path) if path else _MEDIA_CONFIG_PATH
    if not candidate.exists():
        return {}

    try:
        with candidate.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(f"Unable to parse media configuration at {candidate}") from exc

    if not isinstance(payload, MutableMapping):
        raise RuntimeError(
            f"Media configuration at {candidate} must evaluate to a mapping"
        )

    return payload


def get_tts_config(path: Optional[str] = None) -> Mapping[str, Any]:
    """Return the ``tts`` configuration subsection."""

    payload = load_media_config(path)
    tts_section = payload.get("tts", {})
    if isinstance(tts_section, Mapping):
        return tts_section
    return {}


def get_tts_backend_config(name: str, *, path: Optional[str] = None) -> Mapping[str, Any]:
    """Return configuration specific to the backend identified by ``name``."""

    tts_config = get_tts_config(path)
    backends = tts_config.get("backends", {})
    if isinstance(backends, Mapping):
        backend_cfg = backends.get(name, {})
        if isinstance(backend_cfg, Mapping):
            return backend_cfg
    return {}


__all__ = [
    "get_tts_backend_config",
    "get_tts_config",
    "load_media_config",
]
