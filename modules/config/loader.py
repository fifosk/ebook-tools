"""Rendering configuration loader and validation utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

import yaml

_DEFAULT_RENDERING_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "conf" / "rendering.yaml"
)

_DEFAULT_CONFIG = {
    "video_concurrency": 1,
    "audio_concurrency": 2,
    "text_concurrency": 2,
    "video_backend": "ffmpeg",
    "audio_backend": "polly",
    "ramdisk_enabled": True,
    "ramdisk_path": "tmp/render",
    "video_backend_settings": {},
}


def _coerce_positive_int(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer, not a boolean")
    if isinstance(value, int):
        candidate = value
    elif isinstance(value, str) and value.strip():
        if not value.strip().isdigit():
            raise ValueError(f"{name} must be a positive integer")
        candidate = int(value.strip())
    else:
        raise ValueError(f"{name} must be a positive integer")
    if candidate <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return candidate


def _coerce_backend_name(name: str, value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"{name} must be a non-empty string")


def _coerce_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"{name} must be a boolean value")


def _coerce_path_string(name: str, value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"{name} must be a non-empty path string")


def _coerce_settings_mapping(name: str, value: Any) -> MutableMapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping of backend settings")
    result: MutableMapping[str, Any] = {}
    for key, payload in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{name} keys must be non-empty strings")
        if payload is None:
            result[key.strip()] = {}
            continue
        if not isinstance(payload, Mapping):
            raise ValueError(f"{name}.{key} must be a mapping of settings")
        result[key.strip()] = dict(payload)
    return result


def _normalise_payload(data: Mapping[str, Any] | None) -> MutableMapping[str, Any]:
    payload: MutableMapping[str, Any] = dict(_DEFAULT_CONFIG)
    if not data:
        return payload
    for key, value in data.items():
        if key not in payload:
            continue
        payload[key] = value
    return payload


@dataclass(frozen=True, slots=True)
class RenderingConfig:
    """Validated rendering configuration values."""

    video_concurrency: int
    audio_concurrency: int
    text_concurrency: int
    video_backend: str
    audio_backend: str
    ramdisk_enabled: bool
    ramdisk_path: str
    video_backend_settings: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "RenderingConfig":
        normalised = _normalise_payload(payload)
        video = _coerce_positive_int("video_concurrency", normalised["video_concurrency"])
        audio = _coerce_positive_int("audio_concurrency", normalised["audio_concurrency"])
        text = _coerce_positive_int("text_concurrency", normalised["text_concurrency"])
        env_video_backend = os.environ.get("EBOOK_VIDEO_BACKEND")
        selected_video_backend = (
            env_video_backend if env_video_backend else normalised["video_backend"]
        )
        video_backend = _coerce_backend_name("video_backend", selected_video_backend)
        audio_backend = _coerce_backend_name("audio_backend", normalised["audio_backend"])
        ramdisk_enabled = _coerce_bool("ramdisk_enabled", normalised["ramdisk_enabled"])
        ramdisk_path = _coerce_path_string("ramdisk_path", normalised["ramdisk_path"])
        backend_settings = _coerce_settings_mapping(
            "video_backend_settings", normalised.get("video_backend_settings")
        )
        return cls(
            video_concurrency=video,
            audio_concurrency=audio,
            text_concurrency=text,
            video_backend=video_backend,
            audio_backend=audio_backend,
            ramdisk_enabled=ramdisk_enabled,
            ramdisk_path=ramdisk_path,
            video_backend_settings=backend_settings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_concurrency": self.video_concurrency,
            "audio_concurrency": self.audio_concurrency,
            "text_concurrency": self.text_concurrency,
            "video_backend": self.video_backend,
            "audio_backend": self.audio_backend,
            "ramdisk_enabled": self.ramdisk_enabled,
            "ramdisk_path": self.ramdisk_path,
            "video_backend_settings": dict(self.video_backend_settings),
        }


def load_rendering_config(path: Optional[Path | str] = None) -> RenderingConfig:
    """Load and validate the rendering configuration from disk."""

    config_path = Path(path) if path else _DEFAULT_RENDERING_CONFIG_PATH
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            raw_data = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        raw_data = {}
    return RenderingConfig.from_mapping(raw_data)


@lru_cache(maxsize=1)
def get_rendering_config() -> RenderingConfig:
    """Return the cached rendering configuration."""

    return load_rendering_config()


__all__ = ["RenderingConfig", "get_rendering_config", "load_rendering_config"]
