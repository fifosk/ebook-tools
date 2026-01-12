"""Schemas for authentication/session endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class OAuthLoginRequestPayload(BaseModel):
    """Incoming payload for OAuth-based login."""

    provider: str
    id_token: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class SessionUserPayload(BaseModel):
    """Lightweight description of an authenticated user."""

    username: str
    role: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    last_login: Optional[str] = None


class SessionStatusResponse(BaseModel):
    """Response payload returned for active session lookups."""

    token: str
    user: SessionUserPayload


class LoginRequestPayload(BaseModel):
    """Incoming payload for the login endpoint."""

    username: str
    password: str


class PasswordChangeRequestPayload(BaseModel):
    """Payload for updating the authenticated user's password."""

    current_password: str
    new_password: str
