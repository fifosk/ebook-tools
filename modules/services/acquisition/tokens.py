"""Signed tokens for reviewed acquisition handoffs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit


_PROCESS_TOKEN_SECRET = secrets.token_bytes(32)
_TOKEN_PREFIX = "v1"
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "apikey",
    "auth_key",
    "authkey",
    "authorization",
    "cookie",
    "pass_key",
    "passkey",
    "password",
    "rss_key",
    "rsskey",
    "secret",
    "sid",
    "token",
)


def encode_acquisition_token(payload: Mapping[str, Any]) -> str:
    """Return a signed, URL-safe token for a discovery/acquisition payload."""

    _ensure_payload_is_safe(payload)
    body = _b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature = _b64encode(
        hmac.new(_token_secret(), body.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{_TOKEN_PREFIX}.{body}.{signature}"


def decode_acquisition_token(token: str) -> Mapping[str, Any]:
    """Decode and verify a signed acquisition token."""

    normalized = (token or "").strip()
    if not normalized:
        raise ValueError("candidate_token is required")
    parts = normalized.split(".")
    if len(parts) != 3 or parts[0] != _TOKEN_PREFIX:
        raise ValueError("candidate_token is invalid")
    body, signature = parts[1], parts[2]
    expected = _b64encode(
        hmac.new(_token_secret(), body.encode("ascii"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(signature, expected):
        raise ValueError("candidate_token is invalid")
    try:
        decoded = base64.urlsafe_b64decode(_pad_b64(body))
        payload = json.loads(decoded.decode("utf-8"))
    except (UnicodeEncodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("candidate_token is invalid") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("candidate_token is invalid")
    return payload


def _token_secret() -> bytes:
    configured = (
        os.environ.get("EBOOK_ACQUISITION_TOKEN_SECRET")
        or os.environ.get("EBOOK_CONFIG_SECRET")
        or os.environ.get("SECRET_KEY")
    )
    if configured:
        return configured.encode("utf-8")
    return _PROCESS_TOKEN_SECRET


def _ensure_payload_is_safe(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if _looks_sensitive_key(key_text):
                raise ValueError(f"acquisition token payload contains sensitive field: {path}.{key_text}")
            _ensure_payload_is_safe(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _ensure_payload_is_safe(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        _ensure_url_has_no_sensitive_query(value, path=path)


def _looks_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").casefold()
    return any(marker in normalized for marker in _SENSITIVE_KEY_MARKERS)


def _ensure_url_has_no_sensitive_query(value: str, *, path: str) -> None:
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValueError("acquisition token payload contains an invalid URL") from exc
    if parsed.scheme not in {"http", "https", "magnet"}:
        return
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if _looks_sensitive_key(key):
            raise ValueError(f"acquisition token payload contains sensitive URL query field: {path}.{key}")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _pad_b64(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")
