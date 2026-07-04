"""Helpers for Library media route response shaping."""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from ...services.media_diagnostics import build_media_diagnostic_counts
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

    return PipelineMediaDiagnostics(
        **build_media_diagnostic_counts(media_entries, chunk_entries)
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
