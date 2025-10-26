"""HTTP routes for audio synthesis services."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Mapping

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse

from modules import config_manager as cfg
from modules.audio.api import AudioService
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.media.exceptions import MediaBackendError

from .dependencies import get_audio_service
from .schemas import AudioSynthesisError, AudioSynthesisRequest


router = APIRouter(prefix="/api/audio", tags=["audio"])


def _as_mapping(payload: Any) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    return {}


def _looks_like_lang_code(candidate: str) -> bool:
    stripped = candidate.strip()
    if not stripped:
        return False
    normalized = stripped.replace("-", "_")
    if len(normalized) > 16:
        return False
    return all(part.isalpha() for part in normalized.split("_"))


def _resolve_language(requested: str | None, config: Mapping[str, Any]) -> str:
    if requested:
        return requested

    language_codes = {}
    raw_codes = _as_mapping(config.get("language_codes"))
    if raw_codes:
        language_codes = {
            str(key): str(value)
            for key, value in raw_codes.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    preferred_language = config.get("input_language")
    if isinstance(preferred_language, str):
        stripped = preferred_language.strip()
        if stripped:
            code = language_codes.get(stripped)
            if code:
                return code
            mapped = LANGUAGE_CODES.get(stripped)
            if mapped:
                return mapped
            if _looks_like_lang_code(stripped):
                return stripped

    return "en"


def _resolve_voice(requested: str | None, config: Mapping[str, Any]) -> str:
    if requested:
        return requested

    selected_voice = config.get("selected_voice")
    if isinstance(selected_voice, str) and selected_voice.strip():
        return selected_voice.strip()
    return "gTTS"


def _resolve_speed(requested: int | None, config: Mapping[str, Any]) -> int:
    if requested is not None:
        return requested

    value = config.get("macos_reading_speed")
    try:
        speed = int(value)
    except (TypeError, ValueError):
        return 150
    return speed if speed > 0 else 150


@router.post(
    "",
    response_class=StreamingResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": AudioSynthesisError},
        status.HTTP_502_BAD_GATEWAY: {"model": AudioSynthesisError},
    },
)
def synthesize_audio(
    payload: AudioSynthesisRequest,
    audio_service: AudioService = Depends(get_audio_service),
):
    """Generate speech audio using the configured backend."""

    config = cfg.load_configuration(verbose=False)
    voice = _resolve_voice(payload.voice, config)
    speed = _resolve_speed(payload.speed, config)
    language = _resolve_language(payload.language, config)

    try:
        audio_segment = audio_service.synthesize(
            text=payload.text,
            voice=voice,
            speed=speed,
            lang_code=language,
            output_path=None,
        )
    except MediaBackendError as exc:
        error = AudioSynthesisError(
            error="synthesis_failed",
            message=str(exc) or "Audio synthesis failed.",
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=error.model_dump(),
        )

    buffer = BytesIO()
    audio_segment.export(buffer, format="mp3")
    buffer.seek(0)

    headers = {"Content-Disposition": 'attachment; filename="synthesis.mp3"'}
    return StreamingResponse(buffer, media_type="audio/mpeg", headers=headers)


__all__ = ["router"]
