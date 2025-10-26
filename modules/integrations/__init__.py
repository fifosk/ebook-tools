"""External service clients used by ebook-tools integrations."""

from .audio_client import AudioAPIClient
from .video_client import VideoAPIClient

__all__ = ["AudioAPIClient", "VideoAPIClient"]
