"""Utilities for annotating retry failures when LLM responses never stabilize."""

from __future__ import annotations

from typing import Optional

_FAILURE_PREFIX = "[LLM failure]"


def format_retry_failure(
    kind: str,
    attempts: int,
    *,
    reason: Optional[str] = None,
) -> str:
    """Return a descriptive string indicating ``kind`` exhausted its retries."""

    label = (kind or "operation").strip() or "operation"
    attempt_count = max(1, attempts)
    retry_count = max(0, attempt_count - 1)
    normalized_reason = (reason or "no additional details").strip()
    return (
        f"{_FAILURE_PREFIX} {label} failed after {retry_count} retries "
        f"(attempts={attempt_count}; last error: {normalized_reason})"
    )


def is_failure_annotation(text: str) -> bool:
    """Return True if ``text`` matches :func:`format_retry_failure`'s convention."""

    return text.strip().lower().startswith(_FAILURE_PREFIX.lower())


__all__ = ["format_retry_failure", "is_failure_annotation"]
