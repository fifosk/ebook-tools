"""Shared helpers for media manifest diagnostics."""

from __future__ import annotations


def count_media_gaps(
    *,
    chunks_without_files: int,
    chunks_without_metadata: int,
    files_without_url: int,
    files_without_size: int,
) -> int:
    """Return the backend-owned media-gap warning count shared by all surfaces."""

    return chunks_without_files + chunks_without_metadata + files_without_url + files_without_size
