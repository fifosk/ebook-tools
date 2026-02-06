"""Remote metadata synchronization utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Type

from modules import logging_manager
from modules.library.library_metadata import LibraryMetadataError, LibraryMetadataManager
from modules.services.metadata import enrich_media_metadata

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
    enrich_from_external: bool = True,
) -> Dict[str, Any]:
    """Refresh metadata for a library entry using local and remote sources.

    Args:
        job_id: The job identifier.
        job_root: Path to the job directory.
        metadata: The current metadata dictionary to update.
        metadata_manager: The metadata manager for EPUB extraction.
        error_cls: Exception class to raise on errors.
        current_timestamp: Function returning current timestamp.
        enrich_from_external: If True, also enrich from external sources
            (OpenLibrary, Google Books, TMDB, etc.) via the unified
            metadata pipeline. Defaults to True.

    Returns:
        Updated metadata dictionary.
    """

    source_relative = file_ops.ensure_source_material(job_root, metadata)
    if source_relative:
        metadata_utils.apply_source_reference(metadata, source_relative)

    media_metadata_raw = metadata.get("media_metadata") or metadata.get("book_metadata")
    if isinstance(media_metadata_raw, Mapping):
        existing_metadata = {
            key: str(value) if isinstance(value, str) else None
            for key, value in media_metadata_raw.items()
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

    # Enrich from external sources via unified metadata pipeline
    if enrich_from_external:
        enrichment_result = enrich_media_metadata(updated_metadata, force=True)
        if enrichment_result.enriched:
            # Merge enrichment results, preferring local/ISBN data for non-empty fields
            for key, value in enrichment_result.metadata.items():
                if key.startswith("_"):
                    # Always include provenance metadata
                    updated_metadata[key] = value
                elif key not in updated_metadata or not updated_metadata.get(key):
                    updated_metadata[key] = value
            LOGGER.debug(
                "Enriched metadata for job %s from %s (confidence: %s)",
                job_id,
                enrichment_result.confidence,
                enrichment_result.source_result.primary_source.value
                if enrichment_result.source_result and enrichment_result.source_result.primary_source
                else "unknown",
            )

    metadata["media_metadata"] = dict(updated_metadata)

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
        metadata["media_metadata"] = dict(updated_metadata)
    except TypeError:
        metadata["media_metadata"] = dict(updated_metadata or {})

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


def enrich_metadata(
    job_id: str,
    job_root: Path,
    metadata: Dict[str, Any],
    *,
    error_cls: Type[Exception],
    current_timestamp,
    force: bool = False,
) -> Dict[str, Any]:
    """Enrich metadata from external sources without re-parsing EPUB.

    This function only performs external metadata lookup (OpenLibrary, Google
    Books, TMDB, etc.) using the unified metadata pipeline. It does not
    re-extract metadata from the source file.

    Args:
        job_id: The job identifier.
        job_root: Path to the job directory.
        metadata: The current metadata dictionary to update.
        error_cls: Exception class to raise on errors.
        current_timestamp: Function returning current timestamp.
        force: Force refresh even if enrichment data already exists.

    Returns:
        Updated metadata dictionary.
    """
    media_metadata_raw = metadata.get("media_metadata") or metadata.get("book_metadata")
    if isinstance(media_metadata_raw, Mapping):
        existing_metadata = dict(media_metadata_raw)
    else:
        existing_metadata = {}

    # Skip if already enriched and not forcing
    if not force and existing_metadata.get("_enrichment_source"):
        LOGGER.debug("Skipping enrichment for job %s (already enriched)", job_id)
        return metadata

    enrichment_result = enrich_media_metadata(existing_metadata, force=force)

    if enrichment_result.enriched:
        # Update media_metadata with enrichment results
        updated_metadata = dict(existing_metadata)
        for key, value in enrichment_result.metadata.items():
            if key.startswith("_"):
                # Always include provenance metadata
                updated_metadata[key] = value
            elif key not in updated_metadata or not updated_metadata.get(key):
                updated_metadata[key] = value

        metadata["media_metadata"] = updated_metadata

        # Also update top-level fields
        if updated_metadata.get("book_title") and not metadata.get("book_title"):
            metadata["book_title"] = updated_metadata["book_title"]
        if updated_metadata.get("book_author") and not metadata.get("author"):
            metadata["author"] = updated_metadata["book_author"]
        if updated_metadata.get("book_genre") and not metadata.get("genre"):
            metadata["genre"] = updated_metadata["book_genre"]

        metadata["updated_at"] = current_timestamp()

        LOGGER.debug(
            "Enriched metadata for job %s from %s (confidence: %s)",
            job_id,
            enrichment_result.source_result.primary_source.value
            if enrichment_result.source_result and enrichment_result.source_result.primary_source
            else "unknown",
            enrichment_result.confidence,
        )
    else:
        LOGGER.debug("No enrichment available for job %s", job_id)

    return metadata


__all__ = [
    "apply_isbn_metadata",
    "enrich_metadata",
    "lookup_isbn_metadata",
    "refresh_metadata",
]

