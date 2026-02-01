"""High level audio service interfaces."""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional

from pydub import AudioSegment

from modules import logging_manager as log_mgr, observability

from .backends import BaseTTSBackend, SynthesisResult, create_backend, get_tts_backend

logger = log_mgr.logger


def _is_piper_voice(voice: str) -> bool:
    """Check if the voice identifier is a Piper voice model name."""
    if not voice:
        return False
    lowered = voice.lower()
    # Piper auto selection
    if lowered in ("piper-auto", "piper"):
        return True
    # Explicit Piper model name format: lang_REGION-name-quality
    # e.g., en_US-lessac-medium, ar_JO-kareem-medium
    if "_" in voice and "-" in voice:
        parts = voice.split("-")
        if len(parts) >= 2 and "_" in parts[0]:
            return True
    return False


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

    def _get_backend_for_voice(self, voice: str) -> BaseTTSBackend:
        """Return the appropriate backend for the given voice.

        If the voice is a Piper voice identifier, returns a Piper backend.
        Otherwise returns the configured default backend.
        """
        if _is_piper_voice(voice):
            logger.debug(
                "Voice '%s' detected as Piper voice; using Piper backend.",
                voice,
            )
            return create_backend("piper")
        return self._resolve_backend()

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: Optional[str] = None,
    ) -> AudioSegment:
        """Generate speech audio using the appropriate backend for the voice."""

        backend = self._get_backend_for_voice(voice)
        attributes = {
            "backend": backend.name,
            "voice": voice,
            "speed": speed,
            "language": lang_code,
            "has_output_path": bool(output_path),
        }
        logger.info(
            "Dispatching audio synthesis request",
            extra={
                "event": "audio.service.synthesize.start",
                "attributes": attributes,
                "console_suppress": True,
            },
        )
        start_time = time.perf_counter()
        try:
            synthesis = backend.synthesize(
                text=text,
                voice=voice,
                speed=speed,
                lang_code=lang_code,
                output_path=output_path,
            )
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            observability.record_metric(
                "audio.service.synthesize.duration",
                duration_ms,
                {**attributes, "status": "error"},
            )
            logger.error(
                "Audio synthesis failed",
                extra={
                    "event": "audio.service.synthesize.error",
                    "attributes": attributes,
                    "console_suppress": True,
                },
                exc_info=True,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        observability.record_metric(
            "audio.service.synthesize.duration",
            duration_ms,
            {**attributes, "status": "success"},
        )
        logger.info(
            "Audio synthesis completed",
            extra={
                "event": "audio.service.synthesize.complete",
                "attributes": {**attributes, "duration_ms": round(duration_ms, 2)},
                "console_suppress": True,
            },
        )
        if isinstance(synthesis, SynthesisResult):
            return synthesis.audio
        return synthesis


__all__ = ["AudioService"]
