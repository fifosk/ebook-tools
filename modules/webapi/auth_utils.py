"""Shared authentication helpers for FastAPI route modules."""

from __future__ import annotations


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


__all__ = ["extract_session_token"]
