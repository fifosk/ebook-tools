"""Minimal bcrypt-compatible interface for test environments without the real library."""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Final

_SEPARATOR: Final[bytes] = b"$"


def gensalt(rounds: int | None = None) -> bytes:  # pragma: no cover - trivial wrapper
    _ = rounds  # ignored to maintain signature compatibility
    raw = os.urandom(16)
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def hashpw(password: bytes, salt: bytes) -> bytes:
    if not isinstance(password, (bytes, bytearray)):
        raise TypeError("password must be bytes")
    if not isinstance(salt, (bytes, bytearray)):
        raise TypeError("salt must be bytes")
    salt_bytes = bytes(salt)
    digest = hashlib.sha256(salt_bytes + bytes(password)).hexdigest().encode("utf-8")
    return salt_bytes + _SEPARATOR + digest


def checkpw(password: bytes, hashed: bytes) -> bool:
    if not isinstance(password, (bytes, bytearray)):
        raise TypeError("password must be bytes")
    if not isinstance(hashed, (bytes, bytearray)):
        raise TypeError("hashed must be bytes")
    try:
        salt, stored_digest = bytes(hashed).split(_SEPARATOR, 1)
    except ValueError:
        return False
    expected = hashlib.sha256(salt + bytes(password)).hexdigest().encode("utf-8")
    return stored_digest == expected


__all__ = ["gensalt", "hashpw", "checkpw"]
