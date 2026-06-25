"""Server-side references for sensitive acquisition source URLs."""

from __future__ import annotations

import json
import os
import re
import secrets
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.services.file_locator import FileLocator


_REFERENCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,96}$")


def store_acquisition_reference(
    *,
    provider: str,
    media_kind: str,
    source_uri: str,
    config: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> str:
    """Persist a sensitive source URI server-side and return a safe reference id."""

    normalized_source_uri = (source_uri or "").strip()
    if not normalized_source_uri:
        raise ValueError("source_uri is required")
    reference_id = secrets.token_urlsafe(24)
    record = {
        "id": reference_id,
        "provider": provider,
        "media_kind": media_kind,
        "source_uri": normalized_source_uri,
        "metadata": dict(metadata or {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    root = _reference_root(config or {})
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    path = root / f"{reference_id}.json"
    path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    os.chmod(path, 0o600)
    return reference_id


def resolve_acquisition_reference(
    reference_id: str,
    *,
    provider: str | None = None,
    media_kind: str | None = None,
    config: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Resolve a server-side acquisition reference without exposing it to clients."""

    normalized_id = (reference_id or "").strip()
    if not _REFERENCE_ID_PATTERN.fullmatch(normalized_id):
        raise ValueError("source reference is invalid")
    path = _reference_root(config or {}) / f"{normalized_id}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("source reference was not found") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("source reference is invalid") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("source reference is invalid")
    if provider and payload.get("provider") != provider:
        raise ValueError("source reference provider does not match")
    if media_kind and payload.get("media_kind") != media_kind:
        raise ValueError("source reference media kind does not match")
    return payload


def _reference_root(config: Mapping[str, Any]) -> Path:
    configured = (
        config.get("acquisition_reference_root")
        or os.environ.get("EBOOK_ACQUISITION_REFERENCE_ROOT")
    )
    if configured:
        return Path(str(configured)).expanduser().resolve()
    return FileLocator().storage_root / "acquisition_refs"
