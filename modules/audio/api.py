"""High level audio service interfaces."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from pydub import AudioSegment

from modules import logging_manager as log_mgr

from .backends import BaseTTSBackend, create_backend, get_tts_backend

logger = log_mgr.logger


class AudioService:
    """Facade providing access to configured text-to-speech backends."""

    def __init__(
        self,
        *,
        config: Optional[Any] = None,
        backend_name: Optional[str] = None,
        executable_path: Optional[str] = None,
    ) -> None:
        self._config = config
        self._backend_name_override = backend_name
        self._executable_override = executable_path
        self._backend: Optional[BaseTTSBackend] = None

    def _resolve_backend(self) -> BaseTTSBackend:
        if self._backend is not None:
            return self._backend

        if self._backend_name_override:
            logger.debug(
                "Creating TTS backend '%s' with explicit override.",
                self._backend_name_override,
            )
            self._backend = create_backend(
                self._backend_name_override,
                executable_path=self._executable_override,
            )
            return self._backend

        backend_config = self._config
        if self._executable_override and not self._backend_name_override:
            if isinstance(backend_config, Mapping):
                merged = dict(backend_config)
                merged.setdefault("tts_executable_path", self._executable_override)
                backend_config = merged
            else:
                backend_config = {"tts_executable_path": self._executable_override}

        self._backend = get_tts_backend(backend_config)
        return self._backend

    def get_backend(self) -> BaseTTSBackend:
        """Return the instantiated backend, creating it on demand."""

        return self._resolve_backend()

    def reset_backend(self) -> None:
        """Forget any cached backend instance."""

        self._backend = None

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: Optional[str] = None,
    ) -> AudioSegment:
        """Generate speech audio using the configured backend."""

        backend = self._resolve_backend()
        logger.debug(
            "Synthesizing audio with backend '%s' (voice=%s, speed=%s).",
            backend.name,
            voice,
            speed,
        )
        return backend.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            lang_code=lang_code,
            output_path=output_path,
        )


__all__ = ["AudioService"]
