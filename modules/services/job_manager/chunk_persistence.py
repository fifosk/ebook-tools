"""Utilities for persisting and managing chunk metadata files."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ... import logging_manager
from ..file_locator import FileLocator

_LOGGER = logging_manager.get_logger().getChild("job_manager.chunk_persistence")


def normalize_audio_track_entry(value: Any) -> Optional[Dict[str, Any]]:
    """Return a normalized audio track entry with stable fields."""

    if isinstance(value, Mapping):
        entry: Dict[str, Any] = {}
        path = value.get("path")
        url = value.get("url")
        duration = value.get("duration")
        sample_rate = value.get("sampleRate") or value.get("sample_rate")
        if isinstance(path, str) and path.strip():
            entry["path"] = path.strip()
        if isinstance(url, str) and url.strip():
            entry["url"] = url.strip()
        try:
            entry["duration"] = round(float(duration), 6)
        except (TypeError, ValueError):
            pass
        try:
            entry["sampleRate"] = int(sample_rate)
        except (TypeError, ValueError):
            pass
        return entry or None
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return {"path": trimmed}
    return None


def coerce_chunk_id(chunk: Mapping[str, Any]) -> Optional[str]:
    """Extract and normalize chunk_id from a chunk mapping."""

    value = chunk.get("chunk_id") or chunk.get("chunkId")
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


def format_chunk_filename(index: int) -> str:
    """Return the standardized chunk filename for the given index."""

    return f"chunk_{index:04d}.json"


def write_chunk_file(destination: Path, payload: Mapping[str, Any]) -> None:
    """Atomically write chunk payload to destination."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False
    )
    try:
        with tmp_handle as handle:
            handle.write(serialized)
            handle.flush()
        Path(tmp_handle.name).replace(destination)
    except Exception:
        Path(tmp_handle.name).unlink(missing_ok=True)
        raise


def cleanup_unused_chunk_files(metadata_root: Path, preserved: set[str]) -> None:
    """Remove chunk files not in the preserved set."""

    for existing in metadata_root.glob("chunk_*.json"):
        if existing.name in preserved:
            continue
        try:
            existing.unlink()
        except FileNotFoundError:
            continue
        except OSError:  # pragma: no cover - defensive logging
            _LOGGER.debug(
                "Unable to remove stale chunk metadata file %s", existing, exc_info=True
            )


def write_chunk_metadata(
    job_id: str,
    metadata_root: Path,
    generated: Mapping[str, Any],
    file_locator: FileLocator,
) -> Dict[str, Any]:
    """Write chunk metadata files and return updated payload."""

    chunks_raw = generated.get("chunks")
    payload = dict(generated)
    if not isinstance(chunks_raw, list):
        payload["chunks"] = []
        cleanup_unused_chunk_files(metadata_root, set())
        return payload

    updated_chunks: list[Dict[str, Any]] = []
    preserved_files: set[str] = set()

    for index, chunk in enumerate(chunks_raw):
        if not isinstance(chunk, Mapping):
            continue
        chunk_entry = {
            key: copy.deepcopy(value)
            for key, value in chunk.items()
            if key != "sentences"
        }
        sentences_raw = chunk.get("sentences")
        sentences: list[Any]
        if isinstance(sentences_raw, list):
            sentences = copy.deepcopy(sentences_raw)
        else:
            sentences = []

        metadata_path_str = chunk_entry.get("metadata_path")
        metadata_url_str = chunk_entry.get("metadata_url")

        sentence_count = chunk_entry.get("sentence_count")
        if not isinstance(sentence_count, int):
            sentence_count = len(sentences)

        wrote_chunk_file = False
        if sentences:
            filename = format_chunk_filename(index)
            destination = metadata_root / filename
            chunk_payload = {
                "version": 3,
                "chunk_id": chunk_entry.get("chunk_id"),
                "range_fragment": chunk_entry.get("range_fragment"),
                "start_sentence": chunk_entry.get("start_sentence"),
                "end_sentence": chunk_entry.get("end_sentence"),
                "sentence_count": len(sentences),
                "sentences": sentences,
            }
            audio_tracks_raw = chunk_entry.get("audio_tracks") or chunk_entry.get("audioTracks")
            if isinstance(audio_tracks_raw, Mapping):
                normalized_tracks: Dict[str, Dict[str, Any]] = {}
                for track_key, track_value in audio_tracks_raw.items():
                    if not isinstance(track_key, str):
                        continue
                    normalized_entry = normalize_audio_track_entry(track_value)
                    if normalized_entry:
                        normalized_tracks[track_key] = normalized_entry
                if normalized_tracks:
                    chunk_payload["audioTracks"] = normalized_tracks
                    chunk_entry["audioTracks"] = normalized_tracks
            timing_tracks_raw = chunk_entry.get("timing_tracks") or chunk_entry.get("timingTracks")
            if isinstance(timing_tracks_raw, Mapping):
                normalized_timing = copy.deepcopy(dict(timing_tracks_raw))
                chunk_payload["timingTracks"] = normalized_timing
                chunk_entry["timingTracks"] = normalized_timing
            highlight_policy = chunk_entry.get("highlighting_policy")
            if isinstance(highlight_policy, str) and highlight_policy.strip():
                normalized_policy = highlight_policy.strip()
                chunk_payload["highlighting_policy"] = normalized_policy
                chunk_entry["highlighting_policy"] = normalized_policy
            timing_version = chunk_entry.get("timing_version") or chunk_entry.get("timingVersion")
            if isinstance(timing_version, str) and timing_version.strip():
                normalized_version = timing_version.strip()
                chunk_payload["timingVersion"] = normalized_version
                chunk_entry["timingVersion"] = normalized_version
            try:
                write_chunk_file(destination, chunk_payload)
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.debug(
                    "Unable to persist chunk metadata for job %s", job_id, exc_info=True
                )
                chunk_entry["sentences"] = sentences
            else:
                metadata_rel = Path("metadata") / filename
                metadata_path_str = metadata_rel.as_posix()
                chunk_entry["metadata_path"] = metadata_path_str
                url_candidate = file_locator.resolve_url(job_id, metadata_path_str)
                if url_candidate:
                    chunk_entry["metadata_url"] = url_candidate
                    metadata_url_str = url_candidate
                sentence_count = len(sentences)
                preserved_files.add(destination.name)
                wrote_chunk_file = True
        elif isinstance(metadata_path_str, str):
            preserved_files.add(Path(metadata_path_str).name)
            if not metadata_url_str:
                url_candidate = file_locator.resolve_url(job_id, metadata_path_str)
                if url_candidate:
                    chunk_entry["metadata_url"] = url_candidate
                    metadata_url_str = url_candidate

        chunk_entry["sentence_count"] = sentence_count
        if isinstance(metadata_path_str, str) and metadata_path_str.strip():
            for heavy_key in (
                "sentences",
                "audio_tracks",
                "audioTracks",
                "timing_tracks",
                "timingTracks",
                "timing_version",
                "timingVersion",
            ):
                chunk_entry.pop(heavy_key, None)
        if isinstance(metadata_path_str, str) and metadata_path_str:
            chunk_entry.pop("sentences", None)

        updated_chunks.append(chunk_entry)

    cleanup_unused_chunk_files(metadata_root, preserved_files)

    payload["chunks"] = updated_chunks
    return payload


__all__ = [
    "normalize_audio_track_entry",
    "coerce_chunk_id",
    "format_chunk_filename",
    "write_chunk_file",
    "cleanup_unused_chunk_files",
    "write_chunk_metadata",
]
