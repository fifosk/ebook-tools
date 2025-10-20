"""Shared configuration assets used by both CLI and web front-ends."""

from .assets import (
    AUDIO_MODE_OPTIONS,
    DEFAULT_ASSET_VALUES,
    TOP_LANGUAGES,
    VOICE_OPTIONS,
    WRITTEN_MODE_OPTIONS,
    get_audio_mode_descriptions,
    get_assets_payload,
    get_top_languages,
    get_written_mode_descriptions,
)

__all__ = [
    "AUDIO_MODE_OPTIONS",
    "DEFAULT_ASSET_VALUES",
    "TOP_LANGUAGES",
    "VOICE_OPTIONS",
    "WRITTEN_MODE_OPTIONS",
    "get_audio_mode_descriptions",
    "get_assets_payload",
    "get_top_languages",
    "get_written_mode_descriptions",
]
