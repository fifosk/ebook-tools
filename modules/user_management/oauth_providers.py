"""Helpers for verifying OAuth identity tokens."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from typing import Any, Mapping, Optional, Tuple


class OAuthError(Exception):
    """Base class for OAuth verification errors."""


class OAuthConfigurationError(OAuthError):
    """Raised when OAuth configuration is missing or invalid."""


class OAuthVerificationError(OAuthError):
    """Raised when an OAuth token fails verification."""


@dataclass(frozen=True)
class OAuthProviderConfig:
    name: str
    issuers: Tuple[str, ...]
    jwks_url: str
    audiences: Tuple[str, ...]
    require_email_verified: bool = True


@dataclass(frozen=True)
class OAuthIdentity:
    provider: str
    subject: str
    email: str
    email_verified: Optional[bool]
    first_name: Optional[str]
    last_name: Optional[str]
    claims: Mapping[str, Any]


_GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_APPLE_ISSUER = ("https://appleid.apple.com",)
_APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


def _split_env_values(value: Optional[str]) -> Tuple[str, ...]:
    if not value:
        return ()
    parts = []
    for raw in value.replace(",", " ").split():
        candidate = raw.strip()
        if candidate:
            parts.append(candidate)
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in parts:
        if entry not in seen:
            seen.add(entry)
            ordered.append(entry)
    return tuple(ordered)


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return None


def _normalize_provider(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"google", "gmail", "google_oauth", "google-oauth"}:
        return "google"
    if normalized in {"apple", "appleid", "apple-id"}:
        return "apple"
    raise OAuthConfigurationError(f"Unsupported OAuth provider '{value}'")


def _load_pyjwt():
    try:
        import jwt
        from jwt import PyJWKClient
    except Exception as exc:  # pragma: no cover - depends on optional deps
        raise OAuthConfigurationError(
            "PyJWT is required for OAuth login. Install PyJWT[crypto] to enable token verification."
        ) from exc
    return jwt, PyJWKClient


@lru_cache
def _get_jwk_client(jwks_url: str):
    _, pyjwk_client = _load_pyjwt()
    return pyjwk_client(jwks_url)


def _resolve_provider_config(provider: str) -> OAuthProviderConfig:
    normalized = _normalize_provider(provider)
    if normalized == "google":
        audiences = _split_env_values(
            os.environ.get("EBOOK_AUTH_GOOGLE_CLIENT_IDS")
            or os.environ.get("EBOOK_AUTH_GOOGLE_CLIENT_ID")
        )
        if not audiences:
            raise OAuthConfigurationError("Google OAuth client IDs are not configured.")
        return OAuthProviderConfig(
            name="google",
            issuers=_GOOGLE_ISSUERS,
            jwks_url=_GOOGLE_JWKS_URL,
            audiences=audiences,
            require_email_verified=True,
        )
    if normalized == "apple":
        audiences = _split_env_values(
            os.environ.get("EBOOK_AUTH_APPLE_CLIENT_IDS")
            or os.environ.get("EBOOK_AUTH_APPLE_CLIENT_ID")
        )
        if not audiences:
            raise OAuthConfigurationError("Apple OAuth client IDs are not configured.")
        return OAuthProviderConfig(
            name="apple",
            issuers=_APPLE_ISSUER,
            jwks_url=_APPLE_JWKS_URL,
            audiences=audiences,
            require_email_verified=True,
        )
    raise OAuthConfigurationError(f"Unsupported OAuth provider '{provider}'")


def _decode_id_token(config: OAuthProviderConfig, id_token: str) -> Mapping[str, Any]:
    if not id_token:
        raise OAuthVerificationError("Missing identity token.")
    jwt, _ = _load_pyjwt()
    jwk_client = _get_jwk_client(config.jwks_url)
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
    except Exception as exc:  # pragma: no cover - depends on remote provider
        raise OAuthVerificationError("Unable to resolve signing key for identity token.") from exc
    try:
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=list(config.audiences) if config.audiences else None,
            options={"verify_aud": bool(config.audiences), "verify_iss": False},
        )
    except Exception as exc:
        raise OAuthVerificationError("Identity token validation failed.") from exc

    issuer = payload.get("iss")
    if issuer not in config.issuers:
        raise OAuthVerificationError("Unexpected identity token issuer.")
    return payload


def resolve_oauth_identity(provider: str, id_token: str) -> OAuthIdentity:
    config = _resolve_provider_config(provider)
    payload = _decode_id_token(config, id_token)

    subject = str(payload.get("sub") or "").strip()
    if not subject:
        raise OAuthVerificationError("Identity token missing subject.")

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        raise OAuthVerificationError("Identity token missing email.")
    email = email.strip().lower()

    email_verified = _coerce_bool(payload.get("email_verified"))
    if config.require_email_verified and email_verified is False:
        raise OAuthVerificationError("Email address is not verified.")

    first_name = payload.get("given_name")
    last_name = payload.get("family_name")
    if isinstance(first_name, str):
        first_name = first_name.strip() or None
    else:
        first_name = None
    if isinstance(last_name, str):
        last_name = last_name.strip() or None
    else:
        last_name = None

    return OAuthIdentity(
        provider=config.name,
        subject=subject,
        email=email,
        email_verified=email_verified,
        first_name=first_name,
        last_name=last_name,
        claims=payload,
    )


__all__ = [
    "OAuthConfigurationError",
    "OAuthError",
    "OAuthIdentity",
    "OAuthVerificationError",
    "resolve_oauth_identity",
]
