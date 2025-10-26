"""gTTS backend implementation."""

from __future__ import annotations

import io
from typing import Optional

from gtts import gTTS
from pydub import AudioSegment

from .base import BaseTTSBackend, TTSBackendError


class GTTSBackend(BaseTTSBackend):
    """Backend using the Google Text-to-Speech API."""

    name = "gtts"

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: Optional[str] = None,
    ) -> AudioSegment:
        try:
            tts = gTTS(text=text, lang=lang_code)
        except Exception as exc:  # pragma: no cover - network failure defensive
            raise TTSBackendError("gTTS synthesis failed") from exc

        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return AudioSegment.from_file(buffer, format="mp3")


__all__ = ["GTTSBackend"]

