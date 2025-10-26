"""External service clients used by ebook-tools integrations."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing helpers only
    from .audio_client import AudioAPIClient as _AudioAPIClient
    from .video_client import VideoAPIClient as _VideoAPIClient

__all__ = ["AudioAPIClient", "VideoAPIClient"]


def __getattr__(name: str) -> Any:
    """Dynamically import integration clients when requested."""

    if name == "AudioAPIClient":
        try:
            module = import_module("modules.integrations.audio_client")
        except ImportError as exc:  # pragma: no cover - optional dependency safeguard
            raise AttributeError(
                "AudioAPIClient is unavailable because required dependencies are missing."
            ) from exc
        return module.AudioAPIClient
    if name == "VideoAPIClient":
        try:
            module = import_module("modules.integrations.video_client")
        except ImportError as exc:  # pragma: no cover - optional dependency safeguard
            raise AttributeError(
                "VideoAPIClient is unavailable because required dependencies are missing."
            ) from exc
        return module.VideoAPIClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
