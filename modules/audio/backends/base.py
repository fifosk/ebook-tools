"""Base interfaces for text-to-speech backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pydub import AudioSegment

from modules.media.exceptions import MediaBackendError


class TTSBackendError(MediaBackendError):
    """Raised when a backend fails to synthesize audio."""


class BaseTTSBackend(ABC):
    """Abstract base class for concrete TTS backends.

    Implementations should surface all operational failures as
    :class:`TTSBackendError` (or a subclass). This ensures callers can handle
    issues consistently irrespective of the underlying mechanism (e.g. command
    execution via :func:`modules.media.command_runner.run_command`).
    """

    name: str = "base"

    def __init__(self, *, executable_path: Optional[str] = None) -> None:
        self._executable_path = executable_path

    @property
    def executable_path(self) -> Optional[str]:
        """Return the user-provided executable path override, if any."""

        return self._executable_path

    @abstractmethod
    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: Optional[str] = None,
    ) -> AudioSegment:
        """Generate speech audio for ``text``.

        Concrete backends must return a :class:`~pydub.AudioSegment` or raise
        :class:`TTSBackendError`. Any unexpected exception should be wrapped in
        :class:`TTSBackendError` so the audio pipeline can handle failure
        uniformly.
        """


__all__ = [
    "BaseTTSBackend",
    "TTSBackendError",
]

