"""Helpers for Library media route response shaping."""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from ..schemas import (
    PipelineMediaChunk,
    PipelineMediaDiagnostics,
    PipelineMediaFile,
    PipelineMediaResponse,
)


def build_library_media_diagnostics(
    media_entries: Mapping[str, list[PipelineMediaFile]],
    chunk_entries: list[PipelineMediaChunk],
) -> PipelineMediaDiagnostics:
    """Build manifest health counters for Library-backed playback."""

    media_files = [file for entries in media_entries.values() for file in entries]
    chunk_files = [file for chunk in chunk_entries for file in chunk.files]

    def file_type_matches(file: PipelineMediaFile, candidates: set[str]) -> bool:
        value = (file.type or file.name or "").lower()
        return any(candidate in value for candidate in candidates)

    def chunk_has_timing(chunk: PipelineMediaChunk) -> bool:
        if chunk.timing_tracks:
            return any(entries for entries in chunk.timing_tracks.values())
        return any(sentence.timeline for sentence in chunk.sentences)

    def chunk_has_image(chunk: PipelineMediaChunk) -> bool:
        if any(file_type_matches(file, {"image", "png", "jpg", "jpeg", "webp"}) for file in chunk.files):
            return True
        return any(sentence.image is not None or sentence.image_path for sentence in chunk.sentences)

    return PipelineMediaDiagnostics(
        media_file_count=len(media_files),
        chunk_count=len(chunk_entries),
        chunk_file_count=len(chunk_files),
        audio_file_count=sum(
            1 for file in media_files if file_type_matches(file, {"audio", "mp3", "wav", "m4a"})
        ),
        image_file_count=sum(
            1 for file in media_files if file_type_matches(file, {"image", "png", "jpg", "jpeg", "webp"})
        ),
        chunks_with_audio=sum(
            1
            for chunk in chunk_entries
            if chunk.audio_tracks
            or any(file_type_matches(file, {"audio", "mp3", "wav", "m4a"}) for file in chunk.files)
        ),
        chunks_with_timing=sum(1 for chunk in chunk_entries if chunk_has_timing(chunk)),
        chunks_with_images=sum(1 for chunk in chunk_entries if chunk_has_image(chunk)),
        chunks_without_files=sum(1 for chunk in chunk_entries if not chunk.files),
        chunks_without_metadata=sum(
            1
            for chunk in chunk_entries
            if not chunk.metadata_path and not chunk.metadata_url and not chunk.sentences
        ),
        files_without_url=sum(1 for file in media_files if not file.url),
        files_without_size=sum(1 for file in media_files if file.size is None),
    )


def library_media_file_url(job_id: str, relative_path: str) -> str:
    normalized = relative_path.strip().replace("\\", "/").lstrip("/")
    return (
        f"/api/library/media/{quote(str(job_id), safe='')}/file/"
        f"{quote(normalized, safe='/')}"
    )


def build_library_media_response(
    *,
    job_id: str,
    media_map: Mapping[str, list[Mapping[str, Any]]],
    chunk_records: list[Mapping[str, Any]],
    complete: bool,
) -> PipelineMediaResponse:
    serialized_media: dict[str, list[PipelineMediaFile]] = {}
    for category, entries in media_map.items():
        serialized_media[category] = [
            PipelineMediaFile.model_validate(entry) for entry in entries
        ]

    serialized_chunks: list[PipelineMediaChunk] = []
    for chunk in chunk_records:
        files = [PipelineMediaFile.model_validate(entry) for entry in chunk.get("files", [])]
        audio_tracks = _normalize_chunk_audio_tracks(job_id, chunk)
        timing_tracks = _normalize_chunk_timing_tracks(chunk)
        serialized_chunks.append(
            PipelineMediaChunk(
                chunk_id=chunk.get("chunk_id"),
                range_fragment=chunk.get("range_fragment"),
                start_sentence=chunk.get("start_sentence"),
                end_sentence=chunk.get("end_sentence"),
                files=files,
                sentences=chunk.get("sentences") or [],
                metadata_path=chunk.get("metadata_path"),
                metadata_url=chunk.get("metadata_url"),
                sentence_count=chunk.get("sentence_count"),
                audio_tracks=audio_tracks,
                timing_tracks=timing_tracks,
            )
        )

    return PipelineMediaResponse(
        media=serialized_media,
        chunks=serialized_chunks,
        complete=complete,
        diagnostics=build_library_media_diagnostics(serialized_media, serialized_chunks),
    )


def _normalize_chunk_audio_tracks(
    job_id: str,
    chunk: Mapping[str, Any],
) -> dict[str, Any]:
    raw_tracks = chunk.get("audio_tracks") or chunk.get("audioTracks") or {}
    audio_tracks: dict[str, Any] = {}
    if not isinstance(raw_tracks, Mapping):
        return audio_tracks

    for track_key, track_value in raw_tracks.items():
        if not isinstance(track_key, str):
            continue
        if isinstance(track_value, Mapping):
            entry = dict(track_value)
            raw_path = entry.get("path")
            raw_url = entry.get("url")
            if (
                isinstance(raw_path, str)
                and raw_path.strip()
                and not (isinstance(raw_url, str) and raw_url.strip())
            ):
                entry["url"] = library_media_file_url(job_id, raw_path)
            audio_tracks[track_key] = entry
        elif isinstance(track_value, str):
            trimmed = track_value.strip()
            if trimmed:
                audio_tracks[track_key] = {"path": trimmed}
    return audio_tracks


def _normalize_chunk_timing_tracks(
    chunk: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]] | None:
    raw_timing_tracks = chunk.get("timing_tracks") or chunk.get("timingTracks")
    if not isinstance(raw_timing_tracks, Mapping):
        return None

    normalized_timing_tracks: dict[str, list[dict[str, Any]]] = {}
    for track_key, track_entries in raw_timing_tracks.items():
        if not isinstance(track_key, str) or not isinstance(track_entries, list):
            continue
        entries = [
            dict(entry)
            for entry in track_entries
            if isinstance(entry, Mapping)
        ]
        if entries:
            normalized_timing_tracks[track_key] = entries
    return normalized_timing_tracks or None
