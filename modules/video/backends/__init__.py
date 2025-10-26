"""Video rendering backend implementations and factory helpers."""

from __future__ import annotations

from typing import Mapping

from .base import BaseVideoRenderer, VideoRenderOptions
from .ffmpeg_renderer import FFmpegVideoRenderer

DEFAULT_VIDEO_BACKEND = "ffmpeg"


def create_video_renderer(
    name: str | None,
    settings: Mapping[str, object] | None = None,
) -> BaseVideoRenderer:
    """Instantiate the configured video renderer backend."""

    backend = (name or DEFAULT_VIDEO_BACKEND).lower()
    backend_settings = settings or {}

    if backend == "ffmpeg":
        ffmpeg_settings = _coerce_ffmpeg_settings(backend_settings)
        return FFmpegVideoRenderer(**ffmpeg_settings)
    if backend == "golang":
        from modules.render.backends.base import GolangVideoRenderer

        return GolangVideoRenderer()

    raise ValueError(f"Unknown video backend '{backend}'")


def _coerce_ffmpeg_settings(settings: Mapping[str, object]) -> dict[str, object]:
    executable = settings.get("executable")
    loglevel = settings.get("loglevel")
    presets = settings.get("presets")

    if presets is not None and not isinstance(presets, Mapping):
        raise ValueError("ffmpeg.presets must be a mapping of preset names to values")

    return {
        "executable": str(executable) if executable else "ffmpeg",
        "loglevel": str(loglevel) if loglevel else "quiet",
        "presets": presets if isinstance(presets, Mapping) else None,
    }


__all__ = [
    "BaseVideoRenderer",
    "VideoRenderOptions",
    "FFmpegVideoRenderer",
    "create_video_renderer",
]

