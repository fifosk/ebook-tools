"""Administrative user management routes for the FastAPI backend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..user_management import AuthService
from ..user_management.user_store_base import UserRecord
from .dependencies import get_auth_service
from .schemas import (
    ManagedUserPayload,
    UserAccountResponse,
    UserCreateRequestPayload,
    UserListResponse,
    UserPasswordResetRequestPayload,
)


router = APIRouter()


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return authorization.strip() or None


def _require_admin(
    authorization: str | None,
    auth_service: AuthService,
) -> Tuple[str, UserRecord]:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session token")

    user = auth_service.authenticate(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")

    if "admin" not in user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")

    return token, user


def _normalise_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalised = value.strip().lower()
        if normalised in {"true", "1", "yes", "y"}:
            return True
        if normalised in {"false", "0", "no", "n"}:
            return False
    return None


def _resolve_account_status(record: UserRecord) -> Tuple[str, bool, bool]:
    metadata = record.metadata or {}
    suspended = _normalise_bool(metadata.get("suspended"))
    if suspended is None:
        suspended = _normalise_bool(metadata.get("is_suspended"))

    if suspended is True:
        return "suspended", False, True

    if suspended is False:
        return "active", True, False

    return "active", True, False


def _resolve_last_login(metadata: Dict[str, Any]) -> str | None:
    value = metadata.get("last_login")
    if isinstance(value, str) and value:
        return value
    return None


def _serialize_user(record: UserRecord) -> ManagedUserPayload:
    metadata = dict(record.metadata or {})
    status, is_active, is_suspended = _resolve_account_status(record)

    return ManagedUserPayload(
        username=record.username,
        roles=list(record.roles),
        status=status,
        is_active=is_active,
        is_suspended=is_suspended,
        last_login=_resolve_last_login(metadata),
        created_at=metadata.get("created_at"),
        updated_at=metadata.get("updated_at"),
        metadata=metadata,
    )


def _touch_timestamp(metadata: Dict[str, Any], key: str) -> None:
    metadata[key] = datetime.now(timezone.utc).isoformat()


@router.get("/users", response_model=UserListResponse)
def list_users(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserListResponse:
    _require_admin(authorization, auth_service)
    records = auth_service.user_store.list_users()
    users = [_serialize_user(record) for record in records]
    return UserListResponse(users=users)


@router.post(
    "/users",
    response_model=UserAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreateRequestPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserAccountResponse:
    _require_admin(authorization, auth_service)

    metadata: Dict[str, Any] = {}
    _touch_timestamp(metadata, "created_at")

    try:
        record = auth_service.user_store.create_user(
            payload.username,
            payload.password,
            roles=payload.roles,
            metadata=metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return UserAccountResponse(user=_serialize_user(record))


@router.post("/users/{username}/suspend", response_model=UserAccountResponse)
def suspend_user(
    username: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserAccountResponse:
    _require_admin(authorization, auth_service)

    record = auth_service.user_store.get_user(username)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    metadata = dict(record.metadata or {})
    metadata["suspended"] = True
    metadata["is_suspended"] = True
    _touch_timestamp(metadata, "updated_at")

    try:
        record = auth_service.user_store.update_user(username, metadata=metadata)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from exc

    auth_service.session_manager.clear_sessions_for_user(username)
    return UserAccountResponse(user=_serialize_user(record))


@router.post("/users/{username}/activate", response_model=UserAccountResponse)
def activate_user(
    username: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserAccountResponse:
    _require_admin(authorization, auth_service)

    record = auth_service.user_store.get_user(username)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    metadata = dict(record.metadata or {})
    metadata["suspended"] = False
    metadata["is_suspended"] = False
    _touch_timestamp(metadata, "updated_at")

    try:
        record = auth_service.user_store.update_user(username, metadata=metadata)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from exc

    return UserAccountResponse(user=_serialize_user(record))


@router.post("/users/{username}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    username: str,
    payload: UserPasswordResetRequestPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    _require_admin(authorization, auth_service)

    try:
        auth_service.user_store.update_user(username, password=payload.password)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from exc

    auth_service.session_manager.clear_sessions_for_user(username)


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    username: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    _token, caller = _require_admin(authorization, auth_service)

    if caller.username == username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot delete their own account")

    removed = auth_service.user_store.delete_user(username)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    auth_service.session_manager.clear_sessions_for_user(username)


__all__ = ["router"]
