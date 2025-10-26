"""HTTP routes for ad-hoc media generation requests."""

from __future__ import annotations

from uuid import uuid4
from typing import Iterable

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from modules.user_management import AuthService
from modules.user_management.user_store_base import UserRecord

from .dependencies import get_auth_service
from .schemas import (
    MediaErrorResponse,
    MediaGenerationRequestPayload,
    MediaGenerationResponse,
)

router = APIRouter(prefix="/api/media", tags=["media"])

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
    auth_service: AuthService = Depends(get_auth_service),
) -> MediaGenerationResponse:
    """Queue an on-demand media generation job for an existing pipeline run."""

    _, user = _require_authenticated_user(authorization, auth_service)
    _enforce_media_permissions(user)

    request_id = uuid4().hex
    message = "Media generation request accepted."

    return MediaGenerationResponse(
        request_id=request_id,
        status="accepted",
        job_id=payload.job_id,
        media_type=payload.media_type,
        requested_by=user.username,
        parameters=payload.parameters,
        notes=payload.notes,
        message=message,
    )


__all__ = ["router", "register_exception_handlers", "MediaHTTPException"]
