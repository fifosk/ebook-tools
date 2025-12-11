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

    metadata, _ = file_ops.retarget_metadata_generated_files(
        metadata,
        job_id,
        job_root,
    )

    metadata["item_type"] = infer_item_type(metadata)
    if metadata["item_type"] == "video":
        apply_video_defaults(metadata, job_root)

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


def infer_item_type(metadata: Mapping[str, Any]) -> str:
    """Infer whether the library entry should be treated as a book or video."""

    explicit = metadata.get("item_type")
    if isinstance(explicit, str):
        normalized = explicit.strip().lower()
        if normalized in {"book", "video"}:
            return normalized

    job_type = metadata.get("job_type")
    if isinstance(job_type, str) and job_type.strip().lower() == "youtube_dub":
        return "video"

    if isinstance(metadata.get("youtube_dub"), Mapping):
        return "video"

    result_section = metadata.get("result")
    if isinstance(result_section, Mapping):
        if isinstance(result_section.get("youtube_dub"), Mapping):
            return "video"

    return "book"


def apply_video_defaults(metadata: Dict[str, Any], job_root: Path) -> None:
    """Populate sensible defaults for dubbed video entries."""

    metadata["item_type"] = "video"
    dub_section: Optional[Mapping[str, Any]] = None

    if isinstance(metadata.get("youtube_dub"), Mapping):
        dub_section = metadata.get("youtube_dub")  # type: ignore[assignment]

    result_section = metadata.get("result")
    if isinstance(result_section, Mapping) and isinstance(result_section.get("youtube_dub"), Mapping):
        dub_section = result_section.get("youtube_dub")  # type: ignore[assignment]

    resume_context = metadata.get("resume_context")
    request_section = metadata.get("request")

    language = None
    if isinstance(dub_section, Mapping):
        language = dub_section.get("language")
    if language is None and isinstance(resume_context, Mapping):
        language = resume_context.get("target_language") or resume_context.get("language")
    if language is None and isinstance(request_section, Mapping):
        language = request_section.get("target_language") or request_section.get("language")
    if isinstance(language, str) and language.strip():
        metadata.setdefault("language", language.strip())

    video_path: Optional[str] = None
    if isinstance(dub_section, Mapping):
        candidate = dub_section.get("video_path")
        if isinstance(candidate, str) and candidate.strip():
            video_path = candidate.strip()
    if video_path is None and isinstance(resume_context, Mapping):
        candidate = resume_context.get("video_path")
        if isinstance(candidate, str) and candidate.strip():
            video_path = candidate.strip()
    if video_path is None and isinstance(request_section, Mapping):
        candidate = request_section.get("video_path")
        if isinstance(candidate, str) and candidate.strip():
            video_path = candidate.strip()

    title_candidate = None
    author_candidate = None
    if video_path:
        try:
            path_obj = Path(video_path)
            title_candidate = path_obj.stem or path_obj.name
            author_candidate = path_obj.parent.name or None
        except Exception:
            title_candidate = video_path.rsplit("/", 1)[-1]

    if title_candidate:
        metadata.setdefault("book_title", title_candidate)
    if author_candidate:
        metadata.setdefault("author", author_candidate)

    metadata.setdefault("genre", "Video")

    source_reference = file_ops.resolve_source_relative(metadata, job_root)
    if source_reference:
        apply_source_reference(metadata, source_reference)
    elif video_path:
        metadata.setdefault("source_path", video_path)
        metadata.setdefault("source_file", video_path)


__all__ = [
    "apply_isbn",
    "apply_source_reference",
    "build_entry",
    "extract_isbn",
    "infer_item_type",
    "merge_metadata_payloads",
    "apply_video_defaults",
    "normalize_isbn",
]
