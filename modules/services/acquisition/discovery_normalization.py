"""Request normalization helpers for acquisition discovery."""

from __future__ import annotations

import re

from modules.language_constants import LANGUAGE_CODES
from modules.services.acquisition.provider_catalog import normalized_provider_id

DEFAULT_DISCOVERY_LIMIT = 20
MAX_DISCOVERY_LIMIT = 50

_LANGUAGE_NAME_TO_CODE = {name.casefold(): code for name, code in LANGUAGE_CODES.items()}


def normalize_media_kind(media_kind: str) -> str:
    value = (media_kind or "").strip().lower()
    if value not in {"book", "video"}:
        raise ValueError("media_kind must be book or video")
    return value


def normalize_provider(provider: str | None) -> str | None:
    value = normalized_provider_id(provider)
    if value == "backend_defaults":
        return None
    return value or None


def normalize_source_id_filters(source_ids: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_source_id in source_ids or []:
        source_id = str(raw_source_id).strip()
        if not source_id:
            continue
        key = source_id.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(source_id)
    return normalized


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().casefold())


def normalize_limit(
    limit: int,
    *,
    default: int = DEFAULT_DISCOVERY_LIMIT,
    maximum: int = MAX_DISCOVERY_LIMIT,
) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = default
    return max(0, min(value, maximum))


def normalize_language_code(value: str | None) -> str | None:
    raw_value = (value or "").strip()
    if not raw_value:
        return None
    mapped = _LANGUAGE_NAME_TO_CODE.get(raw_value.casefold())
    normalized = (mapped or raw_value).replace("_", "-").strip().casefold()
    if re.fullmatch(r"[a-z]{2,3}(?:-[a-z]{2})?", normalized):
        return normalized.split("-", 1)[0]
    return None
