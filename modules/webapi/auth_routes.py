"""Authentication endpoints for the FastAPI backend."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..user_management import AuthService
from modules.permissions import normalize_role
from ..user_management.user_store_base import UserRecord
from .dependencies import get_auth_service
from .schemas import (
    LoginRequestPayload,
    PasswordChangeRequestPayload,
    SessionStatusResponse,
    SessionUserPayload,
)

router = APIRouter()


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return authorization.strip() or None


def _require_token(authorization: str | None) -> str:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")
    return token


def _primary_role(record: UserRecord) -> str:
    if record.roles:
        normalized = normalize_role(record.roles[0])
        return normalized or record.roles[0]
    return "viewer"


def _resolve_last_login(record: UserRecord, session_data: dict[str, str] | None) -> str | None:
    metadata_value = record.metadata.get("last_login")
    if isinstance(metadata_value, str) and metadata_value:
        return metadata_value
    if session_data:
        created_at = session_data.get("created_at")
        if isinstance(created_at, str) and created_at:
            return created_at
    return None


def _metadata_string(record: UserRecord, key: str) -> str | None:
    value = record.metadata.get(key)
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return None


def _build_session_response(token: str, record: UserRecord, session_data: dict[str, str] | None) -> SessionStatusResponse:
    return SessionStatusResponse(
        token=token,
        user=SessionUserPayload(
            username=record.username,
            role=_primary_role(record),
            email=_metadata_string(record, "email"),
            first_name=_metadata_string(record, "first_name"),
            last_name=_metadata_string(record, "last_name"),
            last_login=_resolve_last_login(record, session_data),
        ),
    )


@router.post("/login", response_model=SessionStatusResponse)
def login(payload: LoginRequestPayload, auth_service: AuthService = Depends(get_auth_service)) -> SessionStatusResponse:
    try:
        token = auth_service.login(payload.username, payload.password)
    except ValueError as exc:  # Invalid credentials
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    record = auth_service.user_store.get_user(payload.username)
    if record is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User record not found")

    metadata = dict(record.metadata)
    now = datetime.now(timezone.utc).isoformat()
    metadata["last_login"] = now
    record.metadata = metadata
    try:
        record = auth_service.user_store.update_user(payload.username, metadata=metadata)
    except KeyError:
        # Record removed between reads; fall back to previous snapshot.
        pass

    session_data = auth_service.session_manager.get_session(token)
    return _build_session_response(token, record, session_data)


@router.get("/session", response_model=SessionStatusResponse)
def session_status(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionStatusResponse:
    token = _require_token(authorization)
    record = auth_service.authenticate(token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    session_data = auth_service.session_manager.get_session(token)
    return _build_session_response(token, record, session_data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    token = _require_token(authorization)
    auth_service.logout(token)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequestPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    token = _require_token(authorization)
    record = auth_service.authenticate(token)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")

    if not auth_service.user_store.verify_credentials(record.username, payload.current_password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")

    auth_service.user_store.update_user(record.username, password=payload.new_password)
