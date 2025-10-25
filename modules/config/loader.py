"""Rendering configuration loader and validation utilities."""
from __future__ import annotations

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

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "RenderingConfig":
        normalised = _normalise_payload(payload)
        video = _coerce_positive_int("video_concurrency", normalised["video_concurrency"])
        audio = _coerce_positive_int("audio_concurrency", normalised["audio_concurrency"])
        text = _coerce_positive_int("text_concurrency", normalised["text_concurrency"])
        video_backend = _coerce_backend_name("video_backend", normalised["video_backend"])
        audio_backend = _coerce_backend_name("audio_backend", normalised["audio_backend"])
        return cls(
            video_concurrency=video,
            audio_concurrency=audio,
            text_concurrency=text,
            video_backend=video_backend,
            audio_backend=audio_backend,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "video_concurrency": self.video_concurrency,
            "audio_concurrency": self.audio_concurrency,
            "text_concurrency": self.text_concurrency,
            "video_backend": self.video_backend,
            "audio_backend": self.audio_backend,
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
