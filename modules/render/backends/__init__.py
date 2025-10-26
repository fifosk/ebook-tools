"""Helpers for resolving configured media rendering backends."""
from __future__ import annotations

from typing import Dict, Type

from modules.config.loader import get_rendering_config

from .base import (
    AudioSynthesizer,
    ExternalAudioSynthesizer,
    GolangVideoRenderer,
    VideoRenderer,
)
from modules.video.backends import FFmpegVideoRenderer
from .polly import PollyAudioSynthesizer

_AUDIO_BACKENDS: Dict[str, Type[AudioSynthesizer]] = {
    "polly": PollyAudioSynthesizer,
    "external": ExternalAudioSynthesizer,
}

_VIDEO_BACKENDS: Dict[str, Type[VideoRenderer]] = {
    "ffmpeg": FFmpegVideoRenderer,
    "golang": GolangVideoRenderer,
}


def get_audio_synthesizer(name: str | None = None) -> AudioSynthesizer:
    """Instantiate the configured audio synthesizer backend."""

    backend_name = (name or get_rendering_config().audio_backend).lower()
    try:
        backend_cls = _AUDIO_BACKENDS[backend_name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown audio backend '{backend_name}'") from exc
    return backend_cls()


def get_video_renderer(name: str | None = None) -> VideoRenderer:
    """Instantiate the configured video renderer backend."""

    backend_name = (name or get_rendering_config().video_backend).lower()
    try:
        backend_cls = _VIDEO_BACKENDS[backend_name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown video backend '{backend_name}'") from exc
    return backend_cls()


__all__ = [
    "AudioSynthesizer",
    "FFmpegVideoRenderer",
    "GolangVideoRenderer",
    "PollyAudioSynthesizer",
    "VideoRenderer",
    "get_audio_synthesizer",
    "get_video_renderer",
]
