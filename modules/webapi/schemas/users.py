"""Schemas for user administration endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ManagedUserPayload(BaseModel):
    """Public representation of a stored user account."""

    username: str
    roles: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: Optional[Literal["active", "suspended", "inactive"]] = None
    is_active: Optional[bool] = None
    is_suspended: Optional[bool] = None
    last_login: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserListResponse(BaseModel):
    """Envelope returned when listing user accounts."""

    users: List[ManagedUserPayload] = Field(default_factory=list)


class UserAccountResponse(BaseModel):
    """Envelope returned when a single account is mutated or retrieved."""

    user: ManagedUserPayload


class UserCreateRequestPayload(BaseModel):
    """Payload for provisioning a new managed user."""

    username: str
    password: str
    roles: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdateRequestPayload(BaseModel):
    """Payload for updating profile metadata for an existing managed user."""

    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserPasswordResetRequestPayload(BaseModel):
    """Payload for administrators resetting another user's password."""

    password: str
