"""HTTP routes for audio synthesis services."""

from __future__ import annotations

import time
from io import BytesIO
from typing import Any, Mapping
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.audio.api import AudioService
from modules.media.exceptions import MediaBackendError
from modules.observability import record_metric

from .dependencies import get_audio_service
from .schemas import AudioSynthesisError, AudioSynthesisRequest
from .audio_utils import resolve_language, resolve_speed, resolve_voice


router = APIRouter(prefix="/api/audio", tags=["audio"])
logger = log_mgr.get_logger().getChild("webapi.audio")


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
    request: Request,
    audio_service: AudioService = Depends(get_audio_service),
):
    """Generate speech audio using the configured backend."""

    config = cfg.load_configuration(verbose=False)
    voice = resolve_voice(payload.voice, config)
    speed = resolve_speed(payload.speed, config)
    language = resolve_language(payload.language, config)
    correlation_id = (
        request.headers.get("x-request-id")
        or request.headers.get("x-correlation-id")
        or str(uuid4())
    )

    backend_name = "unknown"
    try:
        backend = audio_service.get_backend()
        backend_name = getattr(backend, "name", backend.__class__.__name__)
    except Exception:  # pragma: no cover - defensive logging helper
        logger.debug(
            "Unable to resolve audio backend name before synthesis.",
            extra={
                "event": "audio.synthesis.backend_resolution_failed",
                "stage": "api.audio.synthesize",
            },
        )

    metric_attributes = {
        "backend": backend_name,
        "voice": voice,
        "language": language,
    }
    request_attributes = {
        **metric_attributes,
        "speed": speed,
        "text_length": len(payload.text),
        "path": request.url.path,
    }

    with log_mgr.log_context(
        correlation_id=correlation_id, stage="api.audio.synthesize"
    ):
        logger.info(
            "Audio synthesis request received",
            extra={
                "event": "audio.synthesis.request",
                "attributes": request_attributes,
            },
        )
        record_metric("audio.synthesis.requests", 1.0, metric_attributes)
        start = time.perf_counter()

        try:
            audio_segment = audio_service.synthesize(
                text=payload.text,
                voice=voice,
                speed=speed,
                lang_code=language,
                output_path=None,
            )
        except MediaBackendError as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            record_metric(
                "audio.synthesis.duration_ms",
                duration_ms,
                {**metric_attributes, "status": "error"},
            )
            record_metric(
                "audio.synthesis.failures",
                1.0,
                metric_attributes,
            )
            logger.error(
                "Audio synthesis failed",
                extra={
                    "event": "audio.synthesis.error",
                    "duration_ms": round(duration_ms, 2),
                    "attributes": request_attributes,
                    "error": str(exc) or "Audio synthesis failed.",
                },
                exc_info=True,
            )
            error = AudioSynthesisError(
                error="synthesis_failed",
                message=str(exc) or "Audio synthesis failed.",
            )
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content=error.model_dump(),
            )

        duration_ms = (time.perf_counter() - start) * 1000.0
        record_metric(
            "audio.synthesis.duration_ms",
            duration_ms,
            {**metric_attributes, "status": "success"},
        )
        logger.info(
            "Audio synthesis completed",
            extra={
                "event": "audio.synthesis.success",
                "duration_ms": round(duration_ms, 2),
                "attributes": request_attributes,
            },
        )

        buffer = BytesIO()
        audio_segment.export(buffer, format="mp3")
        buffer.seek(0)

        headers = {"Content-Disposition": 'attachment; filename="synthesis.mp3"'}
        return StreamingResponse(buffer, media_type="audio/mpeg", headers=headers)


__all__ = ["router"]
