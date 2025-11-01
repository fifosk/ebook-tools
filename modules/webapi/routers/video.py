"""Video rendering API endpoints."""

from __future__ import annotations

from uuid import uuid4
from typing import Annotated, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse

from modules import logging_manager as log_mgr
from modules.services.video_service import VideoService, VideoTaskSnapshot
from modules.user_management import AuthService
from modules.user_management.user_store_base import UserRecord

from ..dependencies import get_auth_service, get_video_service
from ..schemas.video import VideoGenerationRequest, VideoGenerationResponse

router = APIRouter()
logger = log_mgr.get_logger().getChild("webapi.video")

AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
VideoServiceDep = Annotated[VideoService, Depends(get_video_service)]

_ALLOWED_ROLES = frozenset({"editor", "admin"})


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if token and scheme.lower() == "bearer":
        return token.strip() or None
    return authorization.strip() or None


def _require_authorized_user(
    authorization: str | None,
    auth_service: AuthService,
) -> Tuple[UserRecord, str]:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    user = auth_service.authenticate(token)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    roles = set(user.roles or [])
    if not roles.intersection(_ALLOWED_ROLES):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return user, token


def _snapshot_to_response(snapshot: VideoTaskSnapshot) -> VideoGenerationResponse:
    return VideoGenerationResponse(
        request_id=snapshot.request_id,
        job_id=snapshot.job_id,
        status=snapshot.status,
        output_path=snapshot.output_path,
        logs_url=snapshot.logs_url,
    )


@router.post(
    "/generate",
    response_model=VideoGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_video(
    payload: VideoGenerationRequest,
    request: Request,
    video_service: VideoServiceDep,
    auth_service: AuthServiceDep,
    authorization: AuthorizationHeader = None,
) -> VideoGenerationResponse:
    user, _ = _require_authorized_user(authorization, auth_service)
    correlation_id = request.headers.get("x-request-id") or uuid4().hex

    with log_mgr.log_context(
        correlation_id=correlation_id,
        job_id=payload.job_id,
        stage="api.video.generate",
    ):
        logger.info(
            "Video generation requested",
            extra={
                "event": "video.generate.request",
                "attributes": {"job_id": payload.job_id, "requested_by": user.username},
            },
        )
        snapshot = video_service.enqueue(
            payload.job_id,
            payload.parameters,
            correlation_id=correlation_id,
        )
        response = _snapshot_to_response(snapshot)
        logger.info(
            "Video generation queued",
            extra={
                "event": "video.generate.queued",
                "attributes": {
                    "job_id": response.job_id,
                    "request_id": response.request_id,
                    "status": response.status,
                },
            },
        )
        return response


@router.get(
    "/status/{job_id}",
    response_model=VideoGenerationResponse,
)
def get_video_status(
    job_id: str,
    video_service: VideoServiceDep,
    auth_service: AuthServiceDep,
    authorization: AuthorizationHeader = None,
) -> VideoGenerationResponse:
    _require_authorized_user(authorization, auth_service)
    snapshot = video_service.get_status(job_id)
    if snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Video request not found.")
    return _snapshot_to_response(snapshot)


@router.get("/preview/{job_id}")
def get_video_preview(
    job_id: str,
    video_service: VideoServiceDep,
    auth_service: AuthServiceDep,
    authorization: AuthorizationHeader = None,
) -> FileResponse:
    _require_authorized_user(authorization, auth_service)
    try:
        video_path = video_service.get_preview_path(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Video preview not available for this job.",
        ) from exc
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=video_path.name,
    )


__all__ = ["router"]
