"""Small route-parameter normalization helpers shared by Web API routers."""

from __future__ import annotations


def normalize_route_id(value: str) -> str:
    """Return the trimmed route identifier used before service lookups."""

    return value.strip()
