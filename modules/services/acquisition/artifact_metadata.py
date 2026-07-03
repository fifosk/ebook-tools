"""Metadata helpers for reviewed acquisition artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .discovery_values import int_value, string_value


def normalized_token_id(value: Any) -> str | None:
    raw = string_value(value)
    return raw.casefold() if raw else None


def source_kind(provider: str, payload: Mapping[str, Any]) -> str:
    return normalized_token_id(payload.get("source_kind")) or provider


def prepare_artifact_metadata(
    provider: str,
    media_kind: str,
    payload: Mapping[str, Any],
    local_path: str,
) -> Mapping[str, Any]:
    source_provider = normalized_token_id(payload.get("source_provider")) or provider
    acquisition_provider = normalized_token_id(payload.get("acquisition_provider")) or provider
    metadata: dict[str, Any] = {
        "source_kind": source_kind(provider, payload),
        "source_path": local_path,
        "source_provider": source_provider,
        "acquisition_provider": acquisition_provider,
    }
    candidate_id = prepared_candidate_id(provider, media_kind, payload)
    if candidate_id:
        metadata["acquisition_candidate_id"] = candidate_id
    for key in (
        "gutenberg_id",
        "identifier",
        "source_url",
        "openlibrary_work_key",
        "openlibrary_book_key",
    ):
        value = payload.get(key)
        if value not in (None, ""):
            metadata[key] = value
    return metadata


def prepared_candidate_id(
    provider: str,
    media_kind: str,
    payload: Mapping[str, Any],
) -> str | None:
    explicit = string_value(payload.get("candidate_id"))
    if explicit:
        return explicit
    path = string_value(payload.get("path"))
    if provider == "local_epub" and path:
        return f"local_epub:{path}"
    if provider == "nas_video" and path:
        return f"nas_video:{path}"
    if provider == "manual_downloads" and path:
        return f"manual_downloads:{media_kind}:{path}"
    gutenberg_id = int_value(payload.get("gutenberg_id"))
    if provider == "gutenberg" and gutenberg_id is not None:
        return f"gutenberg:{gutenberg_id}"
    identifier = string_value(payload.get("identifier"))
    if provider == "internet_archive" and identifier:
        return f"internet_archive:{identifier}"
    video_id = string_value(payload.get("video_id"))
    if provider in {"youtube_search", "youtube_url"} and video_id:
        return f"{provider}:{video_id}"
    guid = string_value(payload.get("guid"))
    if provider == "newznab_torznab" and guid:
        return f"newznab_torznab:{guid}"
    return None
