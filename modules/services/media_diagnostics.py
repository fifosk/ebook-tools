"""Shared helpers for media manifest diagnostics."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


AUDIO_FILE_HINTS = {"audio", "mp3", "wav", "m4a"}
IMAGE_FILE_HINTS = {"image", "png", "jpg", "jpeg", "webp"}


def count_media_gaps(
    *,
    chunks_without_files: int,
    chunks_without_metadata: int,
    files_without_url: int,
    files_without_size: int,
) -> int:
    """Return the backend-owned media-gap warning count shared by all surfaces."""

    return chunks_without_files + chunks_without_metadata + files_without_url + files_without_size


def build_media_diagnostic_counts(
    media_entries: Mapping[str, Sequence[Any]],
    chunk_entries: Sequence[Any],
) -> dict[str, int]:
    """Return schema-neutral media manifest counters for Web and Apple playback."""

    media_files = [file for entries in media_entries.values() for file in entries]
    chunk_files = [
        file
        for chunk in chunk_entries
        for file in _as_sequence(_field(chunk, "files"))
        if _is_record(file)
    ]
    chunks_without_files = sum(1 for chunk in chunk_entries if not _as_sequence(_field(chunk, "files")))
    chunks_without_metadata = sum(
        1
        for chunk in chunk_entries
        if not _field(chunk, "metadata_path", "metadataPath")
        and not _field(chunk, "metadata_url", "metadataUrl")
        and not _as_sequence(_field(chunk, "sentences"))
    )
    files_without_url = sum(1 for file in media_files if not _field(file, "url"))
    files_without_size = sum(1 for file in media_files if _field(file, "size") is None)

    return {
        "media_file_count": len(media_files),
        "chunk_count": len(chunk_entries),
        "chunk_file_count": len(chunk_files),
        "audio_file_count": sum(1 for file in media_files if _file_type_matches(file, AUDIO_FILE_HINTS)),
        "image_file_count": sum(1 for file in media_files if _file_type_matches(file, IMAGE_FILE_HINTS)),
        "chunks_with_audio": sum(1 for chunk in chunk_entries if _chunk_has_audio(chunk)),
        "chunks_with_timing": sum(1 for chunk in chunk_entries if _chunk_has_timing(chunk)),
        "chunks_with_images": sum(1 for chunk in chunk_entries if _chunk_has_image(chunk)),
        "chunks_without_files": chunks_without_files,
        "chunks_without_metadata": chunks_without_metadata,
        "files_without_url": files_without_url,
        "files_without_size": files_without_size,
        "gap_count": count_media_gaps(
            chunks_without_files=chunks_without_files,
            chunks_without_metadata=chunks_without_metadata,
            files_without_url=files_without_url,
            files_without_size=files_without_size,
        ),
    }


def build_camel_media_diagnostic_counts(
    media_entries: Mapping[str, Sequence[Any]],
    chunk_entries: Sequence[Any],
) -> dict[str, int]:
    """Return media manifest counters with public camelCase response keys."""

    return {
        _camel_case_diagnostic_key(key): value
        for key, value in build_media_diagnostic_counts(media_entries, chunk_entries).items()
    }


def _field(value: Any, *names: str) -> Any:
    for name in names:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _as_sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _is_record(value: Any) -> bool:
    return isinstance(value, Mapping) or hasattr(value, "__dict__")


def _file_type_matches(file: Any, candidates: set[str]) -> bool:
    value = _field(file, "type") or _field(file, "name") or ""
    return any(candidate in str(value).lower() for candidate in candidates)


def _chunk_has_audio(chunk: Any) -> bool:
    if _field(chunk, "audio_tracks", "audioTracks"):
        return True
    return any(_file_type_matches(file, AUDIO_FILE_HINTS) for file in _as_sequence(_field(chunk, "files")))


def _chunk_has_timing(chunk: Any) -> bool:
    timing_tracks = _field(chunk, "timing_tracks", "timingTracks")
    if isinstance(timing_tracks, Mapping):
        return any(bool(_as_sequence(entries)) for entries in timing_tracks.values())
    return any(bool(_as_sequence(_field(sentence, "timeline"))) for sentence in _as_sequence(_field(chunk, "sentences")))


def _chunk_has_image(chunk: Any) -> bool:
    if any(_file_type_matches(file, IMAGE_FILE_HINTS) for file in _as_sequence(_field(chunk, "files"))):
        return True
    return any(
        _field(sentence, "image") is not None or bool(_field(sentence, "image_path", "imagePath"))
        for sentence in _as_sequence(_field(chunk, "sentences"))
    )


def _camel_case_diagnostic_key(key: str) -> str:
    prefix, *parts = key.split("_")
    return prefix + "".join(part.capitalize() for part in parts)
