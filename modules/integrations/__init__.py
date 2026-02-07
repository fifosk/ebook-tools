"""External service clients used by ebook-tools integrations."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing helpers only
    from .audio_client import AudioAPIClient as _AudioAPIClient

__all__ = ["AudioAPIClient"]


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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
