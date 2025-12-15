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

    metadata["item_type"] = infer_item_type(metadata)
    if metadata["item_type"] == "video":
        apply_video_defaults(metadata, job_root)
    elif metadata["item_type"] == "narrated_subtitle":
        apply_narrated_subtitle_defaults(metadata, job_root)
    elif metadata["item_type"] == "book":
        apply_book_defaults(metadata, job_root)

    author = str(metadata.get("author") or "").strip()
    book_title = str(metadata.get("book_title") or "").strip()
    genre = metadata.get("genre")
    language = str(metadata.get("language") or "").strip() or UNKNOWN_LANGUAGE

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

    def _extract_tv_episode_metadata() -> Optional[Mapping[str, Any]]:
        result_section = metadata.get("result")
        if isinstance(result_section, Mapping):
            subtitle_section = result_section.get("subtitle")
            if isinstance(subtitle_section, Mapping):
                subtitle_metadata = subtitle_section.get("metadata")
                if isinstance(subtitle_metadata, Mapping):
                    media_metadata = subtitle_metadata.get("media_metadata")
                    if isinstance(media_metadata, Mapping):
                        return media_metadata
        request_section = metadata.get("request")
        if isinstance(request_section, Mapping):
            media_metadata = request_section.get("media_metadata")
            if isinstance(media_metadata, Mapping):
                return media_metadata
        return None

    def _format_episode_code(season: int, episode: int) -> str:
        return f"S{season:02d}E{episode:02d}"

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

    tv_metadata = _extract_tv_episode_metadata()
    if isinstance(tv_metadata, Mapping) and str(tv_metadata.get("kind", "")).strip().lower() == "tv_episode":
        genre_candidate = "TV"
        show = tv_metadata.get("show")
        episode = tv_metadata.get("episode")
        show_name = show.get("name") if isinstance(show, Mapping) else None
        episode_name = episode.get("name") if isinstance(episode, Mapping) else None
        season_number = episode.get("season") if isinstance(episode, Mapping) else None
        episode_number = episode.get("number") if isinstance(episode, Mapping) else None
        airdate = episode.get("airdate") if isinstance(episode, Mapping) else None
        genres = show.get("genres") if isinstance(show, Mapping) else None

        if isinstance(show_name, str) and show_name.strip():
            author_candidate = show_name.strip()
            metadata.setdefault("series_title", author_candidate)
        if isinstance(season_number, int) and isinstance(episode_number, int) and season_number > 0 and episode_number > 0:
            metadata.setdefault("season_number", season_number)
            metadata.setdefault("episode_number", episode_number)
            metadata.setdefault("episode_code", _format_episode_code(season_number, episode_number))
            title_candidate = metadata.get("episode_code")
        if isinstance(episode_name, str) and episode_name.strip():
            metadata.setdefault("episode_title", episode_name.strip())
        if isinstance(airdate, str) and airdate.strip():
            metadata.setdefault("airdate", airdate.strip())
        if isinstance(genres, list) and genres:
            filtered = [entry.strip() for entry in genres if isinstance(entry, str) and entry.strip()]
            if filtered:
                metadata.setdefault("series_genres", filtered)

        if isinstance(title_candidate, str) and title_candidate and isinstance(episode_name, str) and episode_name.strip():
            title_candidate = f"{title_candidate} - {episode_name.strip()}"
        if title_candidate is None and isinstance(episode_name, str) and episode_name.strip():
            title_candidate = episode_name.strip()

    if book_metadata is not None:
        if title_candidate is None:
            title_candidate = (
                str(book_metadata.get("book_title") or book_metadata.get("title") or "").strip() or None
            )
        if author_candidate is None:
            author_candidate = (
                str(book_metadata.get("book_author") or book_metadata.get("author") or "").strip() or None
            )
        if genre_candidate is None:
            genre_candidate = (
                str(book_metadata.get("book_genre") or book_metadata.get("genre") or "").strip() or None
            )
        if language_candidate is None:
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
            input_language = options_section.get("input_language") or options_section.get("original_language")
            if isinstance(input_language, str) and input_language.strip():
                metadata.setdefault("input_language", input_language.strip())
                metadata.setdefault("original_language", input_language.strip())
            if language_candidate is None:
                target_language = options_section.get("target_language")
                if isinstance(target_language, str) and target_language.strip():
                    language_candidate = target_language.strip()

    _set_if_blank("author", author_candidate or "Subtitles")
    _set_if_blank("book_title", title_candidate)
    _set_if_blank("genre", genre_candidate or "Subtitles")
    _set_if_blank("language", language_candidate)
    if isinstance(language_candidate, str) and language_candidate.strip():
        metadata.setdefault("target_language", language_candidate.strip())
        metadata.setdefault("translation_language", language_candidate.strip())
        metadata.setdefault("target_languages", [language_candidate.strip()])

    source_relative = file_ops.resolve_source_relative(metadata, job_root)
    if source_relative:
        apply_source_reference(metadata, source_relative)


def apply_book_defaults(metadata: Dict[str, Any], job_root: Path) -> None:
    """Populate sensible defaults for book entries."""

    metadata["item_type"] = "book"

    result_section = metadata.get("result")
    request_section = metadata.get("request")
    resume_section = metadata.get("resume_context")
    request_payload_section = metadata.get("request_payload")

    book_metadata: Optional[Mapping[str, Any]] = None
    direct_book_metadata = metadata.get("book_metadata")
    if isinstance(direct_book_metadata, Mapping):
        book_metadata = direct_book_metadata
    if book_metadata is None and isinstance(result_section, Mapping):
        candidate = result_section.get("book_metadata")
        if isinstance(candidate, Mapping):
            book_metadata = candidate
            metadata["book_metadata"] = dict(candidate)
    if book_metadata is None and isinstance(request_section, Mapping):
        inputs = request_section.get("inputs")
        if isinstance(inputs, Mapping):
            candidate = inputs.get("book_metadata")
            if isinstance(candidate, Mapping):
                book_metadata = candidate
                metadata["book_metadata"] = dict(candidate)

    title_candidate: Optional[str] = None
    author_candidate: Optional[str] = None
    genre_candidate: Optional[str] = None
    language_candidate: Optional[str] = None
    input_language_candidate: Optional[str] = None
    target_languages_candidate: list[str] = []
    request_language_candidate: Optional[str] = None
    request_input_language_candidate: Optional[str] = None
    request_target_languages_candidate: list[str] = []

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

    def _extract_language(value: Any) -> Optional[str]:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, str) and entry.strip():
                    return entry.strip()
        return None

    def _extract_languages(value: Any) -> list[str]:
        if isinstance(value, list):
            return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _read_key(section: Mapping[str, Any], key: str) -> Any:
        if key in section:
            return section.get(key)
        camel = "".join([part if i == 0 else part.capitalize() for i, part in enumerate(key.split("_"))])
        if camel in section:
            return section.get(camel)
        return None

    def _iter_request_sections(payload: Any) -> list[Mapping[str, Any]]:
        if not isinstance(payload, Mapping):
            return []
        candidates: list[Any] = [
            payload.get("inputs"),
            payload.get("config"),
            payload.get("options"),
        ]
        sections: list[Mapping[str, Any]] = []
        for candidate in candidates:
            if isinstance(candidate, Mapping):
                sections.append(candidate)
        return sections

    for root_payload in (request_section, resume_section, request_payload_section):
        for section in _iter_request_sections(root_payload):
            extracted_input_language = _extract_language(_read_key(section, "input_language"))
            extracted_target_languages = _extract_languages(
                _read_key(section, "target_languages")
                or _read_key(section, "target_language")
                or _read_key(section, "translation_language")
            )
            extracted_language = _extract_language(
                _read_key(section, "target_language")
                or _read_key(section, "translation_language")
                or _read_key(section, "target_languages")
            )

            if request_input_language_candidate is None and extracted_input_language is not None:
                request_input_language_candidate = extracted_input_language
            if not request_target_languages_candidate and extracted_target_languages:
                request_target_languages_candidate = extracted_target_languages
            if request_language_candidate is None and extracted_language is not None:
                request_language_candidate = extracted_language

            if input_language_candidate is None and extracted_input_language is not None:
                input_language_candidate = extracted_input_language
            if not target_languages_candidate and extracted_target_languages:
                target_languages_candidate = extracted_target_languages
            if language_candidate is None and extracted_language is not None:
                language_candidate = extracted_language

    if language_candidate is None and target_languages_candidate:
        language_candidate = target_languages_candidate[0]

    def _set_if_blank(key: str, value: Optional[str]) -> None:
        if value is None:
            return
        trimmed = value.strip()
        if not trimmed:
            return
        current = metadata.get(key)
        if current is None:
            metadata[key] = trimmed
            return
        if isinstance(current, str) and (
            not current.strip()
            or (key == "language" and current.strip().lower() == UNKNOWN_LANGUAGE.lower())
        ):
            metadata[key] = trimmed

    _set_if_blank("book_title", title_candidate)
    _set_if_blank("author", author_candidate)
    _set_if_blank("genre", genre_candidate)
    if request_language_candidate:
        metadata["language"] = request_language_candidate.strip()
    else:
        _set_if_blank("language", language_candidate or UNKNOWN_LANGUAGE)

    if request_input_language_candidate:
        metadata["input_language"] = request_input_language_candidate.strip()
        metadata["original_language"] = request_input_language_candidate.strip()
    else:
        _set_if_blank("input_language", input_language_candidate)
        _set_if_blank("original_language", input_language_candidate)

    if request_target_languages_candidate:
        metadata["target_languages"] = request_target_languages_candidate
        metadata["target_language"] = request_target_languages_candidate[0]
        metadata["translation_language"] = request_target_languages_candidate[0]
    elif target_languages_candidate:
        metadata.setdefault("target_languages", target_languages_candidate)
        metadata.setdefault("target_language", target_languages_candidate[0])
        metadata.setdefault("translation_language", target_languages_candidate[0])

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

    def _extract_tv_episode_metadata() -> Optional[Mapping[str, Any]]:
        if isinstance(request_section, Mapping):
            candidate = request_section.get("media_metadata")
            if isinstance(candidate, Mapping):
                return candidate
        direct = metadata.get("media_metadata")
        if isinstance(direct, Mapping):
            return direct
        return None

    def _extract_youtube_metadata(media_metadata: Optional[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
        if not isinstance(media_metadata, Mapping):
            return None
        candidate = media_metadata.get("youtube")
        return candidate if isinstance(candidate, Mapping) else None

    def _format_episode_code(season: int, episode: int) -> str:
        return f"S{season:02d}E{episode:02d}"

    language = None
    if isinstance(dub_section, Mapping):
        language = dub_section.get("language")
    if language is None and isinstance(resume_context, Mapping):
        language = resume_context.get("target_language") or resume_context.get("language")
    if language is None and isinstance(request_section, Mapping):
        language = request_section.get("target_language") or request_section.get("language")
    if isinstance(language, str) and language.strip():
        normalized_language = language.strip()
        metadata.setdefault("language", normalized_language)
        metadata.setdefault("target_language", normalized_language)
        metadata.setdefault("translation_language", normalized_language)
        metadata.setdefault("target_languages", [normalized_language])

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

    title_candidate: Optional[str] = None
    author_candidate: Optional[str] = None
    genre_candidate: Optional[str] = None

    tv_metadata = _extract_tv_episode_metadata()
    youtube_metadata = _extract_youtube_metadata(tv_metadata)
    if isinstance(tv_metadata, Mapping) and str(tv_metadata.get("kind", "")).strip().lower() == "tv_episode":
        genre_candidate = "TV"
        show = tv_metadata.get("show")
        episode = tv_metadata.get("episode")
        show_name = show.get("name") if isinstance(show, Mapping) else None
        episode_name = episode.get("name") if isinstance(episode, Mapping) else None
        season_number = episode.get("season") if isinstance(episode, Mapping) else None
        episode_number = episode.get("number") if isinstance(episode, Mapping) else None
        airdate = episode.get("airdate") if isinstance(episode, Mapping) else None
        genres = show.get("genres") if isinstance(show, Mapping) else None

        if isinstance(show_name, str) and show_name.strip():
            author_candidate = show_name.strip()
            metadata.setdefault("series_title", author_candidate)
        if isinstance(season_number, int) and isinstance(episode_number, int) and season_number > 0 and episode_number > 0:
            metadata.setdefault("season_number", season_number)
            metadata.setdefault("episode_number", episode_number)
            metadata.setdefault("episode_code", _format_episode_code(season_number, episode_number))
            title_candidate = metadata.get("episode_code")
        if isinstance(episode_name, str) and episode_name.strip():
            metadata.setdefault("episode_title", episode_name.strip())
        if isinstance(airdate, str) and airdate.strip():
            metadata.setdefault("airdate", airdate.strip())
        if isinstance(genres, list) and genres:
            filtered = [entry.strip() for entry in genres if isinstance(entry, str) and entry.strip()]
            if filtered:
                metadata.setdefault("series_genres", filtered)

        if isinstance(title_candidate, str) and title_candidate and isinstance(episode_name, str) and episode_name.strip():
            title_candidate = f"{title_candidate} - {episode_name.strip()}"
        if title_candidate is None and isinstance(episode_name, str) and episode_name.strip():
            title_candidate = episode_name.strip()

    if title_candidate is None and isinstance(youtube_metadata, Mapping):
        genre_candidate = genre_candidate or "YouTube"
        youtube_title = youtube_metadata.get("title") or youtube_metadata.get("job_label")
        if isinstance(youtube_title, str) and youtube_title.strip():
            title_candidate = youtube_title.strip()
        youtube_channel = youtube_metadata.get("channel") or youtube_metadata.get("uploader")
        if isinstance(youtube_channel, str) and youtube_channel.strip():
            author_candidate = author_candidate or youtube_channel.strip()

    if video_path:
        try:
            path_obj = Path(video_path)
            if title_candidate is None:
                title_candidate = path_obj.stem or path_obj.name
            if author_candidate is None:
                author_candidate = path_obj.parent.name or None
        except Exception:
            if title_candidate is None:
                title_candidate = video_path.rsplit("/", 1)[-1]

    if title_candidate:
        metadata.setdefault("book_title", title_candidate)
    if author_candidate:
        metadata.setdefault("author", author_candidate)

    metadata.setdefault("genre", genre_candidate or "Video")

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
