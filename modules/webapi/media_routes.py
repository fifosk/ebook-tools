"""HTTP routes for ad-hoc media generation requests."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, Mapping
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.audio.api import AudioService
from modules.media.exceptions import MediaBackendError
from modules.observability import record_metric
from modules.services.file_locator import FileLocator
from modules.user_management import AuthService
from modules.user_management.user_store_base import UserRecord
from modules.video.api import VideoService
from modules.video.jobs import VideoJobManager

from .audio_utils import resolve_language, resolve_speed, resolve_voice
from .dependencies import (
    get_audio_service,
    get_auth_service,
    get_file_locator,
    get_video_job_manager,
    get_video_service,
)
from .schemas import (
    AudioSynthesisRequest,
    MediaErrorResponse,
    MediaGenerationRequestPayload,
    MediaGenerationResponse,
    VideoRenderRequestPayload,
)

router = APIRouter(prefix="/api/media", tags=["media"])
logger = log_mgr.get_logger().getChild("webapi.media")

_MEDIA_ALLOWED_ROLES: frozenset[str] = frozenset({"admin", "media_producer"})


class MediaHTTPException(HTTPException):
    """HTTP error tailored for media routes."""


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if token and scheme.lower() == "bearer":
        return token.strip() or None
    return authorization.strip() or None


def _format_error(error: str, message: str) -> dict[str, str]:
    return MediaErrorResponse(error=error, message=message).model_dump()


def _require_authenticated_user(
    authorization: str | None,
    auth_service: AuthService,
) -> tuple[str, UserRecord]:
    token = _extract_bearer_token(authorization)
    if not token:
        raise MediaHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_format_error("missing_token", "Missing session token"),
        )
    user = auth_service.authenticate(token)
    if user is None:
        raise MediaHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_format_error("invalid_token", "Invalid session token"),
        )
    return token, user


def _user_has_role(user: UserRecord, roles: Iterable[str]) -> bool:
    user_roles = set(user.roles or [])
    return any(role in user_roles for role in roles)


def _enforce_media_permissions(user: UserRecord) -> None:
    if not _MEDIA_ALLOWED_ROLES:
        return
    if _user_has_role(user, _MEDIA_ALLOWED_ROLES):
        return
    raise MediaHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_format_error(
            "insufficient_permissions",
            "Media generation requires an account with elevated permissions.",
        ),
    )


def _normalise_relative_path(root: Path, candidate: Path) -> str:
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return candidate.name


def _select_audio_filename(candidate: str | None) -> str:
    if not candidate:
        return f"audio-{uuid4().hex}.mp3"
    name = Path(candidate).name
    if not name:
        return f"audio-{uuid4().hex}.mp3"
    if not name.lower().endswith(".mp3"):
        name = f"{name}.mp3"
    return name


def _prepare_audio_request(parameters: Mapping[str, object]) -> tuple[str | None, AudioSynthesisRequest]:
    payload = dict(parameters)
    output_name = None
    raw_name = payload.pop("output_filename", None)
    if isinstance(raw_name, str):
        output_name = raw_name.strip() or None
    try:
        request = AudioSynthesisRequest.model_validate(payload)
    except ValidationError as exc:
        raise MediaHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_format_error("invalid_parameters", exc.errors()[0]["msg"]),
        ) from exc
    return output_name, request


def _resolve_audio_defaults(
    request: AudioSynthesisRequest,
    config: Mapping[str, object],
) -> tuple[str, int, str]:
    voice = resolve_voice(request.voice, config)
    speed = resolve_speed(request.speed, config)
    language = resolve_language(request.language, config)
    return voice, speed, language


def _export_audio(
    job_id: str,
    request: AudioSynthesisRequest,
    *,
    locator: FileLocator,
    audio_service: AudioService,
    output_filename: str | None,
) -> tuple[str, str | None, dict[str, object]]:
    config = cfg.load_configuration(verbose=False)
    voice, speed, language = _resolve_audio_defaults(request, config)

    metric_attributes = {
        "voice": voice,
        "language": language,
    }

    logger.info(
        "Generating audio for job %s", job_id,
        extra={
            "event": "media.audio.request",
            "attributes": {**metric_attributes, "text_length": len(request.text)},
        },
    )

    start_time = time.perf_counter()

    try:
        segment = audio_service.synthesize(
            text=request.text,
            voice=voice,
            speed=speed,
            lang_code=language,
            output_path=None,
        )
    except MediaBackendError as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        record_metric(
            "media.audio.duration_ms",
            duration_ms,
            {**metric_attributes, "status": "error"},
        )
        record_metric("media.audio.failures", 1.0, metric_attributes)
        logger.error(
            "Audio synthesis failed for job %s", job_id,
            extra={
                "event": "media.audio.error",
                "error": str(exc) or "Audio synthesis failed",
            },
            exc_info=True,
        )
        raise MediaHTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_format_error("synthesis_failed", str(exc) or "Audio synthesis failed."),
        ) from exc

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    record_metric(
        "media.audio.duration_ms",
        duration_ms,
        {**metric_attributes, "status": "success"},
    )
    record_metric("media.audio.requests", 1.0, metric_attributes)

    job_root = locator.resolve_path(job_id)
    audio_dir = job_root / "media" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    filename = _select_audio_filename(output_filename)
    output_path = audio_dir / filename
    segment.export(output_path, format="mp3")

    relative_path = _normalise_relative_path(job_root, output_path)
    url = locator.resolve_url(job_id, relative_path)

    logger.info(
        "Audio artifact generated for job %s", job_id,
        extra={
            "event": "media.audio.success",
            "duration_ms": round(duration_ms, 2),
            "attributes": {
                **metric_attributes,
                "relative_path": relative_path,
                "job_id": job_id,
            },
        },
    )

    normalized_params: dict[str, object] = {
        "text": request.text,
        "voice": voice,
        "speed": speed,
        "language": language,
    }
    return relative_path, url, normalized_params


def _prepare_video_parameters(
    payload: MediaGenerationRequestPayload,
) -> Mapping[str, object]:
    parameters: dict[str, object] = {}
    for key, value in payload.parameters.items():
        if isinstance(value, (str, int, float, list, dict, bool)) or value is None:
            parameters[key] = value

    audio_entries = parameters.get("audio")
    if isinstance(audio_entries, list):
        normalized_audio: list[Mapping[str, object]] = []
        for entry in audio_entries:
            if not isinstance(entry, Mapping):
                normalized_audio.append(entry)
                continue
            normalized = dict(entry)
            rel_path = normalized.get("relative_path")
            if rel_path and "job_id" not in normalized:
                normalized["job_id"] = payload.job_id
            normalized_audio.append(normalized)
        parameters["audio"] = normalized_audio

    options = parameters.get("options")
    if isinstance(options, Mapping):
        options = dict(options)
        cover_image = options.get("cover_image")
        if isinstance(cover_image, Mapping):
            cover_dict = dict(cover_image)
            rel_path = cover_dict.get("relative_path")
            if rel_path and "job_id" not in cover_dict:
                cover_dict["job_id"] = payload.job_id
            options["cover_image"] = cover_dict
        parameters["options"] = options

    return parameters


def _submit_video_job(
    payload: MediaGenerationRequestPayload,
    *,
    job_manager: VideoJobManager,
    video_service: VideoService,
) -> tuple[str, dict[str, object]]:
    parameters = _prepare_video_parameters(payload)
    try:
        request_payload = VideoRenderRequestPayload.model_validate(parameters)
    except ValidationError as exc:
        raise MediaHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_format_error("invalid_parameters", exc.errors()[0]["msg"]),
        ) from exc

    task = request_payload.to_task(job_manager.locator)
    job = job_manager.submit(task, video_service=video_service)
    logger.info(
        "Video rendering job %s submitted for pipeline job %s",
        job.job_id,
        payload.job_id,
        extra={
            "event": "media.video.submit",
            "attributes": {
                "slides": len(task.slides),
                "audio_tracks": len(task.audio_sources),
                "pipeline_job_id": payload.job_id,
            },
        },
    )

    normalized_params = request_payload.model_dump()
    return job.job_id, normalized_params


async def _handle_media_http_exception(
    _request: Request, exc: MediaHTTPException
) -> JSONResponse:
    if isinstance(exc.detail, dict) and {"error", "message"} <= set(exc.detail):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers required by the media router."""

    app.add_exception_handler(MediaHTTPException, _handle_media_http_exception)


@router.post(
    "/generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MediaGenerationResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": MediaErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": MediaErrorResponse},
    },
)
def request_media_generation(
    payload: MediaGenerationRequestPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    request: Request | None = None,
    auth_service: AuthService = Depends(get_auth_service),
    audio_service: AudioService = Depends(get_audio_service),
    video_service: VideoService = Depends(get_video_service),
    video_job_manager: VideoJobManager = Depends(get_video_job_manager),
    locator: FileLocator = Depends(get_file_locator),
) -> MediaGenerationResponse:
    """Queue an on-demand media generation job for an existing pipeline run."""

    _, user = _require_authenticated_user(authorization, auth_service)
    _enforce_media_permissions(user)

    job_root = locator.resolve_path(payload.job_id)
    job_root.mkdir(parents=True, exist_ok=True)

    correlation_id = request.headers.get("x-request-id") if request else None
    with log_mgr.log_context(
        correlation_id=correlation_id or uuid4().hex,
        job_id=payload.job_id,
        stage="api.media.generate",
    ):
        media_type = payload.media_type.lower().strip()
        if media_type == "audio":
            output_filename, synthesis_request = _prepare_audio_request(payload.parameters)
            relative_path, url, normalized_params = _export_audio(
                payload.job_id,
                synthesis_request,
                locator=locator,
                audio_service=audio_service,
                output_filename=output_filename,
            )
            return MediaGenerationResponse(
                request_id=uuid4().hex,
                status="completed",
                job_id=payload.job_id,
                media_type="audio",
                requested_by=user.username,
                parameters=normalized_params,
                notes=payload.notes,
                message="Audio generation completed.",
                artifact_path=relative_path,
                artifact_url=url,
            )

        if media_type == "video":
            job_id, normalized_params = _submit_video_job(
                payload,
                job_manager=video_job_manager,
                video_service=video_service,
            )
            return MediaGenerationResponse(
                request_id=job_id,
                status="queued",
                job_id=payload.job_id,
                media_type="video",
                requested_by=user.username,
                parameters=normalized_params,
                notes=payload.notes,
                message="Video rendering job submitted.",
            )

        raise MediaHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_format_error(
                "unsupported_media_type",
                f"Media type '{payload.media_type}' is not supported.",
            ),
        )


__all__ = ["router", "register_exception_handlers", "MediaHTTPException"]
