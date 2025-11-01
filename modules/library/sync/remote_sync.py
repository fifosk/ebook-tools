"""Remote metadata synchronization utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Type

from modules import logging_manager
from modules.library.library_metadata import LibraryMetadataError, LibraryMetadataManager

from . import file_ops, metadata as metadata_utils

LOGGER = logging_manager.get_logger().getChild("library.sync.remote")


def refresh_metadata(
    job_id: str,
    job_root: Path,
    metadata: Dict[str, Any],
    metadata_manager: LibraryMetadataManager,
    *,
    error_cls: Type[Exception],
    current_timestamp,
) -> Dict[str, Any]:
    """Refresh metadata for a library entry using local and remote sources."""

    source_relative = file_ops.ensure_source_material(job_root, metadata)
    if source_relative:
        metadata_utils.apply_source_reference(metadata, source_relative)

    book_metadata_raw = metadata.get("book_metadata")
    if isinstance(book_metadata_raw, Mapping):
        existing_metadata = {
            key: str(value) if isinstance(value, str) else None
            for key, value in book_metadata_raw.items()
        }
    else:
        existing_metadata = {}

    epub_path = file_ops.locate_input_epub(metadata, job_root)
    local_metadata: Dict[str, Optional[str]] = {}
    if epub_path is not None and epub_path.exists():
        try:
            local_metadata = metadata_manager.infer_metadata_from_epub(
                epub_path,
                existing_metadata=existing_metadata,
                force_refresh=True,
            )
        except LibraryMetadataError as exc:
            raise error_cls(f"Metadata refresh failed: {exc}") from exc

    isbn_value = metadata_utils.extract_isbn(metadata)
    isbn_metadata: Dict[str, Optional[str]] = {}
    if isbn_value:
        try:
            isbn_metadata = metadata_manager.fetch_metadata_from_isbn(isbn_value)
        except LibraryMetadataError as exc:  # pragma: no cover - defensive logging
            LOGGER.debug(
                "Unable to fetch ISBN metadata for job %s (%s): %s",
                job_id,
                isbn_value,
                exc,
            )

    if (epub_path is None or not (epub_path.exists() if epub_path else False)) and not isbn_metadata:
        raise error_cls(
            f"Unable to locate a source EPUB or ISBN metadata for job {job_id}; cannot refresh metadata"
        )

    updated_metadata = metadata_utils.merge_metadata_payloads(
        metadata_manager,
        existing_metadata,
        local_metadata,
        isbn_metadata,
    )
    if isbn_value:
        updated_metadata["isbn"] = isbn_value

    metadata["book_metadata"] = dict(updated_metadata)

    if updated_metadata.get("book_title"):
        metadata["book_title"] = updated_metadata["book_title"]
    if updated_metadata.get("book_author"):
        metadata["author"] = updated_metadata["book_author"]
    if updated_metadata.get("book_language"):
        metadata["language"] = updated_metadata["book_language"] or metadata.get("language")
    if updated_metadata.get("book_genre"):
        metadata["genre"] = updated_metadata.get("book_genre")

    if source_relative:
        metadata_utils.apply_source_reference(metadata, source_relative)

    if isbn_value:
        metadata_utils.apply_isbn(metadata, isbn_value)

    cover_reference = updated_metadata.get("book_cover_file") or updated_metadata.get("job_cover_asset")
    cover_asset = file_ops.mirror_cover_asset(job_root, cover_reference)
    if cover_asset:
        metadata["job_cover_asset"] = cover_asset
        updated_metadata["job_cover_asset"] = cover_asset
        updated_metadata["book_cover_file"] = cover_asset
    else:
        metadata.pop("job_cover_asset", None)
        updated_metadata.pop("job_cover_asset", None)
        if "book_cover_file" in updated_metadata and not updated_metadata["book_cover_file"]:
            updated_metadata.pop("book_cover_file", None)

    try:
        metadata["book_metadata"] = dict(updated_metadata)
    except TypeError:
        metadata["book_metadata"] = dict(updated_metadata or {})

    metadata["updated_at"] = current_timestamp()
    return metadata


def apply_isbn_metadata(
    metadata: Dict[str, Any],
    *,
    isbn: str,
    error_cls: Type[Exception],
    current_timestamp,
) -> Dict[str, Any]:
    """Apply a normalized ISBN to metadata and update timestamps."""

    normalized = metadata_utils.normalize_isbn(isbn)
    if not normalized:
        raise error_cls("ISBN must contain 10 or 13 digits (optionally including X)")

    metadata_utils.apply_isbn(metadata, normalized)
    metadata["updated_at"] = current_timestamp()
    return metadata


def lookup_isbn_metadata(
    metadata_manager: LibraryMetadataManager,
    isbn: str,
    *,
    error_cls: Type[Exception],
) -> Dict[str, Optional[str]]:
    """Fetch ISBN metadata via the shared manager."""

    normalized = metadata_utils.normalize_isbn(isbn)
    if not normalized:
        raise error_cls("ISBN must contain 10 or 13 digits (optionally including X)")
    return metadata_manager.fetch_metadata_from_isbn(normalized)


__all__ = [
    "apply_isbn_metadata",
    "lookup_isbn_metadata",
    "refresh_metadata",
]

