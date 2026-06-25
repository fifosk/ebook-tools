"""Signed opaque tokens for reviewed acquisition handoffs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from collections.abc import Mapping
from typing import Any


_PROCESS_TOKEN_SECRET = secrets.token_bytes(32)
_TOKEN_PREFIX = "v1"


def encode_acquisition_token(payload: Mapping[str, Any]) -> str:
    """Return a signed, URL-safe token for a discovery/acquisition payload."""

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


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _pad_b64(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")
