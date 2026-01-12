"""Authentication endpoints for the FastAPI backend."""

from __future__ import annotations

from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..user_management import AuthService
from ..user_management.oauth_providers import (
    OAuthConfigurationError,
    OAuthVerificationError,
    resolve_oauth_identity,
)
from modules.permissions import normalize_role
from ..user_management.user_store_base import UserRecord
from .dependencies import get_auth_service
from .schemas import (
    LoginRequestPayload,
    OAuthLoginRequestPayload,
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


def _normalise_email(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip().lower()
    return candidate or None


def _normalise_name(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    return candidate or None


def _find_user_by_email(auth_service: AuthService, email: str) -> UserRecord | None:
    record = auth_service.user_store.get_user(email)
    if record is not None:
        return record
    for candidate in auth_service.user_store.list_users():
        if candidate.username.strip().lower() == email:
            return candidate
        metadata_email = candidate.metadata.get("email")
        if isinstance(metadata_email, str) and metadata_email.strip().lower() == email:
            return candidate
    return None


def _merge_oauth_metadata(
    metadata: dict[str, object],
    *,
    email: str,
    provider: str,
    subject: str,
    first_name: str | None,
    last_name: str | None,
) -> None:
    metadata.setdefault("email", email)
    if first_name and not metadata.get("first_name"):
        metadata["first_name"] = first_name
    if last_name and not metadata.get("last_name"):
        metadata["last_name"] = last_name

    providers: set[str] = set()
    raw_providers = metadata.get("auth_providers")
    if isinstance(raw_providers, list):
        for entry in raw_providers:
            if isinstance(entry, str):
                providers.add(entry)
    providers.add(provider)
    metadata["auth_providers"] = sorted(providers)

    subjects: dict[str, str] = {}
    raw_subjects = metadata.get("auth_subjects")
    if isinstance(raw_subjects, dict):
        for key, value in raw_subjects.items():
            if isinstance(key, str) and isinstance(value, str):
                subjects[key] = value
    if subject:
        subjects[provider] = subject
    if subjects:
        metadata["auth_subjects"] = subjects


def _touch_timestamp(metadata: dict[str, object], key: str) -> None:
    metadata[key] = datetime.now(timezone.utc).isoformat()


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


@router.post("/oauth", response_model=SessionStatusResponse)
def oauth_login(
    payload: OAuthLoginRequestPayload,
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionStatusResponse:
    try:
        identity = resolve_oauth_identity(payload.provider, payload.id_token)
    except OAuthConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except OAuthVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    email_override = _normalise_email(payload.email)
    if email_override and email_override != identity.email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OAuth email mismatch.")

    email = email_override or identity.email
    first_name = identity.first_name or _normalise_name(payload.first_name)
    last_name = identity.last_name or _normalise_name(payload.last_name)

    record = _find_user_by_email(auth_service, email)
    metadata: dict[str, object] = {}
    if record is None:
        _merge_oauth_metadata(
            metadata,
            email=email,
            provider=identity.provider,
            subject=identity.subject,
            first_name=first_name,
            last_name=last_name,
        )
        _touch_timestamp(metadata, "created_at")
        _touch_timestamp(metadata, "updated_at")
        metadata["last_login"] = metadata["updated_at"]
        try:
            record = auth_service.user_store.create_user(
                email,
                password=secrets.token_urlsafe(32),
                roles=["viewer"],
                metadata=metadata,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        metadata = dict(record.metadata or {})
        _merge_oauth_metadata(
            metadata,
            email=email,
            provider=identity.provider,
            subject=identity.subject,
            first_name=first_name,
            last_name=last_name,
        )
        _touch_timestamp(metadata, "updated_at")
        metadata["last_login"] = metadata["updated_at"]
        try:
            record = auth_service.user_store.update_user(record.username, metadata=metadata)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User record not found") from exc

    token = auth_service.session_manager.create_session(record.username)
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
