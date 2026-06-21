"""Shared authentication helpers for FastAPI route modules."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from fastapi import HTTPException, status

from ..user_management import AuthService
from ..user_management.user_store_base import UserRecord


THTTPException = TypeVar("THTTPException", bound=HTTPException)


def extract_session_token(authorization: str | None) -> str | None:
    """Extract a session token from an Authorization header.

    Bearer tokens are the canonical API contract. A bare token without an auth
    scheme is still accepted for older scripts, but explicit non-Bearer schemes
    are rejected instead of being treated as opaque tokens.
    """

    if not authorization:
        return None

    value = authorization.strip()
    if not value:
        return None

    scheme, separator, token = value.partition(" ")
    if separator:
        if scheme.lower() != "bearer":
            return None
        return token.strip() or None

    return value


def require_authenticated_user(
    authorization: str | None,
    auth_service: AuthService,
    *,
    missing_detail: object = "Missing session token",
    invalid_detail: object = "Invalid session token",
    exception_type: type[THTTPException] = HTTPException,
) -> tuple[str, UserRecord]:
    """Return the authenticated user for a request Authorization header."""

    token = extract_session_token(authorization)
    if not token:
        raise exception_type(status_code=status.HTTP_401_UNAUTHORIZED, detail=missing_detail)

    user = auth_service.authenticate(token)
    if user is None:
        raise exception_type(status_code=status.HTTP_401_UNAUTHORIZED, detail=invalid_detail)

    return token, user


def require_user_role(
    authorization: str | None,
    auth_service: AuthService,
    *,
    roles: Iterable[str],
    forbidden_detail: object = "Insufficient permissions",
) -> tuple[str, UserRecord]:
    """Return the authenticated user when they have at least one required role."""

    token, user = require_authenticated_user(authorization, auth_service)
    required_roles = set(roles)
    if required_roles and not (required_roles & set(user.roles or [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=forbidden_detail)
    return token, user


def require_admin_user(
    authorization: str | None,
    auth_service: AuthService,
) -> tuple[str, UserRecord]:
    """Return the authenticated admin user for an admin-only route."""

    return require_user_role(
        authorization,
        auth_service,
        roles={"admin"},
        forbidden_detail="Administrator role required",
    )


__all__ = [
    "extract_session_token",
    "require_admin_user",
    "require_authenticated_user",
    "require_user_role",
]
