"""Metadata helpers for library synchronization."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Type

from modules.library.library_models import LibraryEntry, MetadataSnapshot

from conf.sync_config import UNKNOWN_LANGUAGE

from . import file_ops


def normalize_isbn(raw: str) -> Optional[str]:
    """Return a normalized ISBN value or ``None`` when invalid."""

    if not raw:
        return None
    cleaned = re.sub(r"[^0-9Xx]", "", raw)
    if len(cleaned) in {10, 13}:
        return cleaned.upper()
    return None


def extract_isbn(metadata: Mapping[str, Any]) -> Optional[str]:
    """Extract a normalized ISBN from metadata."""

    candidates: list[str] = []

    def push(value: Any) -> None:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                candidates.append(trimmed)

    push(metadata.get("isbn"))
    book_metadata = metadata.get("book_metadata")
    if isinstance(book_metadata, Mapping):
        push(book_metadata.get("isbn"))
        push(book_metadata.get("book_isbn"))

    for raw in candidates:
        normalized = normalize_isbn(raw)
        if normalized:
            return normalized
    return None


def apply_isbn(metadata: Dict[str, Any], isbn: Optional[str]) -> None:
    """Apply ``isbn`` to the metadata payload."""

    if not isbn:
        return
    metadata["isbn"] = isbn
    book_metadata = metadata.get("book_metadata")
    if isinstance(book_metadata, Mapping):
        nested = dict(book_metadata)
        nested["isbn"] = isbn
        nested["book_isbn"] = isbn
        metadata["book_metadata"] = nested


def apply_source_reference(metadata: Dict[str, Any], source_relative: str) -> None:
    """Update metadata with a normalized source reference."""

    metadata["source_path"] = source_relative
    metadata["source_file"] = source_relative
    book_metadata = metadata.get("book_metadata")
    if isinstance(book_metadata, Mapping):
        nested = dict(book_metadata)
        nested["source_path"] = source_relative
        nested["source_file"] = source_relative
        metadata["book_metadata"] = nested


def merge_metadata_payloads(
    metadata_manager,
    *payloads: Mapping[str, Any],
) -> Dict[str, Any]:
    """Merge metadata payloads via the metadata manager."""

    return metadata_manager.merge_metadata_payloads(*payloads)


def build_entry(
    metadata: Dict[str, Any],
    job_root: Path,
    *,
    error_cls: Type[Exception],
    normalize_status,
    current_timestamp,
) -> LibraryEntry:
    """Construct a ``LibraryEntry`` from raw metadata."""

    job_id = str(metadata.get("job_id") or "").strip()
    if not job_id:
        raise error_cls("Job metadata is missing 'job_id'")

    author = str(metadata.get("author") or "").strip()
    book_title = str(metadata.get("book_title") or "").strip()
    genre = metadata.get("genre")
    language = str(metadata.get("language") or "").strip() or UNKNOWN_LANGUAGE
    try:
        status = normalize_status(metadata.get("status"))
    except Exception:
        status = "finished"
    created_at = str(metadata.get("created_at") or current_timestamp())
    updated_at = str(metadata.get("updated_at") or created_at)

    metadata = dict(metadata)
    metadata["job_id"] = job_id
    metadata["status"] = status
    metadata.setdefault("created_at", created_at)
    metadata["updated_at"] = updated_at

    source_relative = file_ops.resolve_source_relative(metadata, job_root)
    if source_relative:
        apply_source_reference(metadata, source_relative)

    isbn = extract_isbn(metadata)
    if isbn:
        apply_isbn(metadata, isbn)

    metadata["generated_files"] = file_ops.retarget_generated_files(
        metadata.get("generated_files"),
        job_id,
        job_root,
    )

    cover_path = file_ops.extract_cover_path(metadata, job_root)
    if cover_path:
        metadata["job_cover_asset"] = cover_path
        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            nested = dict(book_metadata)
            nested["job_cover_asset"] = cover_path
            nested.setdefault("book_cover_file", cover_path)
            metadata["book_metadata"] = nested

    return LibraryEntry(
        id=job_id,
        author=author,
        book_title=book_title,
        genre=str(genre) if genre not in {None, ""} else None,
        language=language,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        library_path=str(job_root.resolve()),
        cover_path=cover_path,
        isbn=isbn,
        source_path=source_relative,
        metadata=MetadataSnapshot(metadata=metadata),
    )


__all__ = [
    "apply_isbn",
    "apply_source_reference",
    "build_entry",
    "extract_isbn",
    "merge_metadata_payloads",
    "normalize_isbn",
]
