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
        item_type=str(metadata.get("item_type") or infer_item_type(metadata)).strip() or "book",
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
        if normalized in {"book", "video", "narrated_subtitle"}:
            return normalized

    job_type = metadata.get("job_type")
    if isinstance(job_type, str) and job_type.strip().lower() == "youtube_dub":
        return "video"

    if is_narrated_subtitle_job(metadata):
        return "narrated_subtitle"

    if isinstance(metadata.get("youtube_dub"), Mapping):
        return "video"

    result_section = metadata.get("result")
    if isinstance(result_section, Mapping):
        if isinstance(result_section.get("youtube_dub"), Mapping):
            return "video"

    return "book"


def is_narrated_subtitle_job(metadata: Mapping[str, Any]) -> bool:
    """Return ``True`` when metadata represents a narrated subtitle job."""

    job_type = metadata.get("job_type")
    if not isinstance(job_type, str) or job_type.strip().lower() != "subtitle":
        return False

    def _extract_flag(payload: Any) -> Optional[bool]:
        if isinstance(payload, Mapping):
            value = payload.get("generate_audio_book")
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                trimmed = value.strip().lower()
                if trimmed in {"true", "1", "yes", "on"}:
                    return True
                if trimmed in {"false", "0", "no", "off"}:
                    return False
        return None

    result_section = metadata.get("result")
    if isinstance(result_section, Mapping):
        subtitle_section = result_section.get("subtitle")
        if isinstance(subtitle_section, Mapping):
            subtitle_metadata = subtitle_section.get("metadata")
            flag = _extract_flag(subtitle_metadata)
            if flag is not None:
                return flag

    request_section = metadata.get("request")
    if isinstance(request_section, Mapping):
        options_section = request_section.get("options")
        flag = _extract_flag(options_section)
        if flag is not None:
            return flag

    return False


def apply_narrated_subtitle_defaults(metadata: Dict[str, Any], job_root: Path) -> None:
    """Populate sensible defaults for narrated subtitle entries."""

    metadata["item_type"] = "narrated_subtitle"

    def _set_if_blank(key: str, value: Optional[str]) -> None:
        if value is None:
            return
        trimmed = str(value).strip()
        if not trimmed:
            return
        current = metadata.get(key)
        if current is None:
            metadata[key] = trimmed
            return
        if isinstance(current, str) and not current.strip():
            metadata[key] = trimmed

    result_section = metadata.get("result")
    book_metadata: Optional[Mapping[str, Any]] = None
    if isinstance(result_section, Mapping) and isinstance(result_section.get("book_metadata"), Mapping):
        book_metadata = result_section.get("book_metadata")  # type: ignore[assignment]

    if book_metadata is None and isinstance(metadata.get("book_metadata"), Mapping):
        book_metadata = metadata.get("book_metadata")  # type: ignore[assignment]

    title_candidate: Optional[str] = None
    author_candidate: Optional[str] = None
    genre_candidate: Optional[str] = None
    language_candidate: Optional[str] = None

    if book_metadata is not None:
        title_candidate = (
            str(book_metadata.get("book_title") or book_metadata.get("title") or "").strip() or None
        )
        author_candidate = (
            str(book_metadata.get("book_author") or book_metadata.get("author") or "").strip() or None
        )
        genre_candidate = (
            str(book_metadata.get("book_genre") or book_metadata.get("genre") or "").strip() or None
        )
        language_candidate = (
            str(book_metadata.get("book_language") or book_metadata.get("language") or "").strip() or None
        )

    request_section = metadata.get("request")
    if isinstance(request_section, Mapping):
        original_name = request_section.get("original_name")
        if title_candidate is None and isinstance(original_name, str) and original_name.strip():
            try:
                title_candidate = Path(original_name.strip()).stem or original_name.strip()
            except Exception:
                title_candidate = original_name.strip()

        options_section = request_section.get("options")
        if isinstance(options_section, Mapping):
            if language_candidate is None:
                target_language = options_section.get("target_language")
                if isinstance(target_language, str) and target_language.strip():
                    language_candidate = target_language.strip()

    _set_if_blank("author", author_candidate or "Subtitles")
    _set_if_blank("book_title", title_candidate)
    _set_if_blank("genre", genre_candidate or "Subtitles")
    _set_if_blank("language", language_candidate)

    source_relative = file_ops.resolve_source_relative(metadata, job_root)
    if source_relative:
        apply_source_reference(metadata, source_relative)


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
    "apply_narrated_subtitle_defaults",
    "apply_source_reference",
    "build_entry",
    "extract_isbn",
    "infer_item_type",
    "is_narrated_subtitle_job",
    "merge_metadata_payloads",
    "apply_video_defaults",
    "normalize_isbn",
]
