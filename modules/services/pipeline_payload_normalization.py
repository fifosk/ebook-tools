"""Shared normalization helpers for pipeline request payloads."""

from __future__ import annotations

from typing import Any


DISCOVERY_IDENTIFIER_KEYS = frozenset(
    {
        "acquisition_provider",
        "media_kind",
        "provider",
        "selected_provider",
        "source_kind",
        "source_provider",
    }
)


def normalize_discovery_identifier(value: Any) -> Any:
    """Normalize provider/source identifiers without touching case-sensitive IDs."""

    if isinstance(value, str):
        return value.strip().casefold()
    return value


def normalize_discovery_identifiers(value: Any) -> Any:
    """Normalize discovery/provider IDs in nested request metadata payloads."""

    if isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            normalized[key] = (
                normalize_discovery_identifier(item)
                if str(key) in DISCOVERY_IDENTIFIER_KEYS
                else normalize_discovery_identifiers(item)
            )
        return normalized
    if isinstance(value, list):
        return [normalize_discovery_identifiers(item) for item in value]
    return value
