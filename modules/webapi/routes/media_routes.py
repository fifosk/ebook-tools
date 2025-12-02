"""Routes for pipeline media metadata and downloads."""

from __future__ import annotations

import copy
import json
import mimetypes
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from ... import config_manager as cfg
from ...metadata_manager import MetadataLoader
from ...services.file_locator import FileLocator
from ...services.pipeline_service import PipelineService
from ..dependencies import (
    RequestUserContext,
    get_file_locator,
    get_pipeline_job_manager,
    get_pipeline_service,
    get_request_user,
)

from ..jobs import PipelineJob
from ..schemas import PipelineMediaChunk, PipelineMediaFile, PipelineMediaResponse

router = APIRouter()
storage_router = APIRouter()
jobs_timing_router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def normalize_timings(
    tokens: Sequence[Mapping[str, Any]],
    start_offset: float = 0.0,
    *,
    lane: str = "tran",
    seg_prefix: str = "seg",
) -> list[dict[str, Any]]:
    """Normalise timing tokens into the frontend payload format."""

    norm: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        raw_start = float(token.get("start", 0.0))
        raw_end = float(token.get("end", raw_start))
        t0 = round(raw_start - start_offset, 3)
        t1 = round(raw_end - start_offset, 3)
        norm.append(
            {
                "id": f"{seg_prefix}_{index}",
                "text": token.get("text", ""),
                "t0": max(t0, 0.0),
                "t1": max(t1, 0.0),
                "lane": lane,
                "segId": seg_prefix,
            }
        )
    return norm


def smooth_token_edges(
    tokens: Sequence[Mapping[str, Any]], min_len: float = 0.04
) -> list[dict[str, Any]]:
    """Ensure every token spans at least ``min_len`` seconds and clamps overlaps."""

    smoothed: list[dict[str, Any]] = []
    total = len(tokens)
    for index, token in enumerate(tokens):
        mutable = dict(token)
        start_val = float(mutable.get("start", 0.0))
        end_val = float(mutable.get("end", start_val))
        duration = end_val - start_val
        if duration < min_len:
            if index + 1 < total:
                next_start = float(tokens[index + 1].get("start", end_val))
            else:
                next_start = end_val + min_len
            end_val = min(next_start, start_val + min_len)
            mutable["end"] = end_val
        smoothed.append(mutable)
    return smoothed


def _iter_sentence_payloads(payload: Any) -> Iterator[Mapping[str, Any]]:
    """Yield flattened sentence entries from chunk payloads."""

    if isinstance(payload, Mapping):
        sentences = payload.get("sentences")
        if isinstance(sentences, Sequence) and not isinstance(sentences, (str, bytes)):
            for entry in sentences:
                yield from _iter_sentence_payloads(entry)
            return
        yield payload
        return
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        for entry in payload:
            yield from _iter_sentence_payloads(entry)


def _extract_highlighting_policy(entry: Mapping[str, Any]) -> Optional[str]:
    """Return the highlighting policy encoded on a sentence entry."""

    summary = entry.get("highlighting_summary")
    if isinstance(summary, Mapping):
        policy = summary.get("policy")
        if isinstance(policy, str) and policy.strip():
            return policy.strip()
    candidate = entry.get("highlighting_policy") or entry.get("alignment_policy")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None


def _is_estimated_policy(policy: Optional[str]) -> bool:
    if not isinstance(policy, str):
        return False
    normalized = policy.strip().lower()
    return normalized.startswith("estimated")


def _probe_highlighting_policy(
    job_id: str,
    locator: FileLocator,
    default_policy: Optional[str],
) -> tuple[Optional[str], bool]:
    """Resolve the highlighting policy and whether estimated timings exist."""

    metadata_root = locator.metadata_root(job_id)
    normalized_default = None
    if isinstance(default_policy, str) and default_policy.strip():
        normalized_default = default_policy.strip()
    estimated_detected = _is_estimated_policy(normalized_default)
    fallback_policy: Optional[str] = normalized_default

    if metadata_root.exists():
        for chunk_path in sorted(metadata_root.glob("chunk_*.json")):
            try:
                with chunk_path.open("r", encoding="utf-8") as handle:
                    chunk_payload = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            for entry in _iter_sentence_payloads(chunk_payload):
                if isinstance(entry, Mapping):
                    policy = _extract_highlighting_policy(entry)
                    if policy:
                        normalized = policy.strip()
                        if _is_estimated_policy(normalized):
                            return normalized, True
                        if fallback_policy is None:
                            fallback_policy = normalized
    if fallback_policy is not None:
        estimated_detected = estimated_detected or _is_estimated_policy(fallback_policy)
    return fallback_policy, estimated_detected


@jobs_timing_router.get("/{job_id}/timing", response_class=JSONResponse)
async def get_job_timing(
    job_id: str,
    *,
    job_manager = Depends(get_pipeline_job_manager),
    locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
) -> JSONResponse:
    """Return flattened per-word timing data for ``job_id``."""

    try:
        job: PipelineJob = job_manager.get(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    result_payload = job.result_payload if isinstance(job.result_payload, Mapping) else {}
    timing_tracks = result_payload.get("timing_tracks") if isinstance(result_payload, Mapping) else None
    if not isinstance(timing_tracks, Mapping):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No timing track available")

    requested_tracks = {
        key: path
        for key, path in timing_tracks.items()
        if key in {"mix", "translation"} and isinstance(path, str) and path.strip()
    }
    if not requested_tracks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No timing track available")

    resolved_paths: Dict[str, Path] = {}
    for track_name, rel_path in requested_tracks.items():
        try:
            abs_path = locator.resolve_path(job_id, rel_path)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timing index missing",
            ) from exc
        if not abs_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timing index missing")
        resolved_paths[track_name] = abs_path

    data_cache: Dict[Path, Any] = {}
    resolved_segments: Dict[str, List[Any]] = {"mix": [], "translation": []}
    for track_name, abs_path in resolved_paths.items():
        if abs_path not in data_cache:
            try:
                with abs_path.open("r", encoding="utf-8") as handle:
                    data_cache[abs_path] = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Timing index missing",
                ) from exc
        payload = data_cache[abs_path]
        segments: list[Any]
        if isinstance(payload, Mapping):
            track_entries = payload.get(track_name)
            if isinstance(track_entries, list):
                segments = track_entries
            elif track_name == "translation" and isinstance(payload.get("segments"), list):
                segments = payload["segments"]  # legacy
            elif track_name == "translation" and isinstance(payload.get("translation"), list):
                segments = payload["translation"]
            else:
                segments = []
        elif isinstance(payload, list):
            segments = payload
        else:
            segments = []
        resolved_segments[track_name] = segments

    unique_paths = sorted({path for path in resolved_paths.values()})
    try:
        stats = [path.stat() for path in unique_paths]
        digest = "-".join(f"{st.st_mtime_ns:x}-{st.st_size:x}" for st in stats)
        etag = f'W/"{digest}"'
    except OSError:
        fallback_count = sum(len(resolved_segments.get(name, [])) for name in resolved_segments)
        etag = f'W/"{job_id}-{fallback_count}"'

    playback_meta = result_payload.get("timing_meta") if isinstance(result_payload, Mapping) else None
    playback_rate = 1.0
    if isinstance(playback_meta, Mapping):
        try:
            playback_rate = float(playback_meta.get("playbackRate", 1.0))
        except (TypeError, ValueError):
            playback_rate = 1.0

    highlighting_policy, has_estimated_segments = _probe_highlighting_policy(
        job_id,
        locator,
        result_payload.get("highlighting_policy") if isinstance(result_payload, Mapping) else None,
    )

    def _collect_audio_availability() -> Dict[str, Dict[str, Any]]:
        audio_summary: Dict[str, Dict[str, Any]] = {}
        generated_payload = result_payload.get("generated_files") if isinstance(result_payload, Mapping) else None
        chunk_audio_keys: set[str] = set()
        if isinstance(generated_payload, Mapping):
            chunks = generated_payload.get("chunks")
            if isinstance(chunks, list):
                for chunk in chunks:
                    if not isinstance(chunk, Mapping):
                        continue
                    tracks = chunk.get("audio_tracks") or chunk.get("audioTracks")
                    if not isinstance(tracks, Mapping):
                        continue
                    for raw_key, raw_value in tracks.items():
                        if not isinstance(raw_key, str):
                            continue
                        key = raw_key.strip()
                        if not key:
                            continue
                        if key == "trans":
                            key = "translation"
                        chunk_audio_keys.add(key)
        audio_summary["orig_trans"] = {
            "track": "mix",
            "available": "orig_trans" in chunk_audio_keys,
        }
        audio_summary["translation"] = {
            "track": "translation",
            "available": "translation" in chunk_audio_keys or "trans" in chunk_audio_keys,
        }
        return audio_summary

    headers = {
        "Cache-Control": "public, max-age=60",
        "ETag": etag,
    }
    return JSONResponse(
        content={
            "job_id": job_id,
            "tracks": {
                "mix": {
                    "track": "mix",
                    "segments": resolved_segments.get("mix", []),
                    "playback_rate": playback_rate,
                },
                "translation": {
                    "track": "translation",
                    "segments": resolved_segments.get("translation", []),
                    "playback_rate": playback_rate,
                },
            },
            "audio": _collect_audio_availability(),
            "highlighting_policy": highlighting_policy,
            "has_estimated_segments": has_estimated_segments,
        },
        headers=headers,
    )

def _resolve_media_path(
    job_id: str,
    entry: Mapping[str, Any],
    locator: FileLocator,
    job_root: Path,
) -> tuple[Optional[Path], Optional[str]]:
    """Return the absolute and relative paths for a generated media entry."""

    relative_value = entry.get("relative_path")
    resolved_path: Optional[Path] = None
    relative_path: Optional[str] = None

    if relative_value:
        relative_path = Path(str(relative_value)).as_posix()
        try:
            resolved_path = locator.resolve_path(job_id, relative_path)
        except ValueError:
            resolved_path = None

    path_value = entry.get("path")
    if resolved_path is None and path_value:
        candidate = Path(str(path_value))
        if candidate.is_absolute():
            resolved_path = candidate
            try:
                relative_candidate = candidate.relative_to(job_root)
            except ValueError:
                pass
            else:
                relative_path = relative_candidate.as_posix()
        else:
            try:
                resolved_path = locator.resolve_path(job_id, candidate)
            except ValueError:
                resolved_path = None
            else:
                relative_path = candidate.as_posix()

    return resolved_path, relative_path


def _coerce_int(value: Any) -> Optional[int]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number


def _build_media_file(
    job_id: str,
    entry: Mapping[str, Any],
    locator: FileLocator,
    job_root: Path,
    *,
    source: str,
) -> tuple[Optional[PipelineMediaFile], Optional[str], tuple[str, str]]:
    file_type_raw = entry.get("type") or "unknown"
    file_type = str(file_type_raw).lower() or "unknown"

    resolved_path, relative_path = _resolve_media_path(job_id, entry, locator, job_root)

    url_value = entry.get("url")
    url: Optional[str] = url_value if isinstance(url_value, str) else None
    if not url and relative_path:
        try:
            url = locator.resolve_url(job_id, relative_path)
        except ValueError:
            url = None

    size: Optional[int] = None
    updated_at: Optional[datetime] = None
    if resolved_path is not None and resolved_path.exists():
        try:
            stat_result = resolved_path.stat()
        except OSError:
            pass
        else:
            size = int(stat_result.st_size)
            updated_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)

    name_value = entry.get("name")
    name = str(name_value) if name_value else None
    if not name:
        if resolved_path is not None:
            name = resolved_path.name
        elif relative_path:
            name = Path(relative_path).name
        else:
            path_value = entry.get("path")
            if path_value:
                name = Path(str(path_value)).name
    if not name:
        name = "media" if file_type == "unknown" else file_type

    path_value = entry.get("path") if isinstance(entry.get("path"), str) else None

    chunk_id_value = entry.get("chunk_id")
    chunk_id = str(chunk_id_value) if chunk_id_value not in {None, ""} else None
    range_fragment_value = entry.get("range_fragment")
    range_fragment = str(range_fragment_value) if range_fragment_value not in {None, ""} else None
    start_sentence = _coerce_int(entry.get("start_sentence"))
    end_sentence = _coerce_int(entry.get("end_sentence"))

    record = PipelineMediaFile(
        name=name,
        url=url,
        size=size,
        updated_at=updated_at,
        source=source,
        relative_path=relative_path,
        path=path_value,
        chunk_id=chunk_id,
        range_fragment=range_fragment,
        start_sentence=start_sentence,
        end_sentence=end_sentence,
        type=file_type,
    )
    signature_key = path_value or relative_path or url or name
    signature = (signature_key or name, file_type)
    return record, file_type, signature


def _serialize_media_entries(
    job_id: str,
    generated_files: Optional[Mapping[str, Any]],
    locator: FileLocator,
    *,
    source: str,
    metadata_loader: Optional[MetadataLoader] = None,
) -> tuple[Dict[str, List[PipelineMediaFile]], List[PipelineMediaChunk], bool]:
    """Return serialized media metadata grouped by type and chunk."""

    media_map: Dict[str, List[PipelineMediaFile]] = {}
    chunk_records: List[PipelineMediaChunk] = []
    complete = False

    if not isinstance(generated_files, Mapping):
        return media_map, chunk_records, complete

    job_root = locator.resolve_path(job_id)
    seen: set[tuple[str, str]] = set()

    loader = metadata_loader
    loader_attempted = metadata_loader is not None

    def _resolve_loader() -> Optional[MetadataLoader]:
        nonlocal loader, loader_attempted
        if loader is not None:
            return loader
        if loader_attempted:
            return None
        loader_attempted = True
        manifest_path = job_root / "metadata" / "job.json"
        if not manifest_path.exists():
            return None
        try:
            loader = MetadataLoader(job_root)
        except Exception:  # pragma: no cover - defensive logging
            loader = None
        return loader

    chunks_section = generated_files.get("chunks")
    if isinstance(chunks_section, list):
        for chunk in chunks_section:
            if not isinstance(chunk, Mapping):
                continue
            chunk_files: List[PipelineMediaFile] = []
            files_raw = chunk.get("files")
            if not isinstance(files_raw, list):
                files_raw = []
            for file_entry in files_raw:
                if not isinstance(file_entry, Mapping):
                    continue
                enriched_entry = dict(file_entry)
                enriched_entry.setdefault("chunk_id", chunk.get("chunk_id"))
                enriched_entry.setdefault("range_fragment", chunk.get("range_fragment"))
                enriched_entry.setdefault("start_sentence", chunk.get("start_sentence"))
                enriched_entry.setdefault("end_sentence", chunk.get("end_sentence"))
                record, file_type, signature = _build_media_file(
                    job_id,
                    enriched_entry,
                    locator,
                    job_root,
                    source=source,
                )
                if record is None or file_type is None:
                    continue
                if signature in seen:
                    chunk_files.append(record)
                    continue
                seen.add(signature)
                media_map.setdefault(file_type, []).append(record)
                chunk_files.append(record)
            if not chunk_files:
                continue

            summary: Mapping[str, Any] = chunk
            active_loader = _resolve_loader()
            if active_loader is not None:
                try:
                    summary = active_loader.load_chunk(chunk, include_sentences=False)
                except Exception:  # pragma: no cover - defensive logging
                    summary = chunk

            metadata_path = summary.get("metadata_path")
            metadata_url = summary.get("metadata_url")
            sentence_count = _coerce_int(summary.get("sentence_count"))

            sentences_payload: List[Any] = []
            if isinstance(metadata_path, str) and metadata_path.strip():
                sentences_payload = []
            else:
                if active_loader is not None:
                    sentences_payload = active_loader.load_chunk_sentences(chunk)
                else:
                    inline_sentences = summary.get("sentences") or chunk.get("sentences")
                    if isinstance(inline_sentences, list):
                        sentences_payload = copy.deepcopy(inline_sentences)
                if sentence_count is None:
                    sentence_count = len(sentences_payload)

            audio_tracks_payload: Dict[str, Dict[str, Any]] = {}

            def _register_track(raw_key: Any, raw_value: Any) -> None:
                if not isinstance(raw_key, str):
                    return
                key = raw_key.strip()
                if not key:
                    return

                entry: Dict[str, Any] = {}
                if isinstance(raw_value, str):
                    value = raw_value.strip()
                    if not value:
                        return
                    entry["path"] = value
                elif isinstance(raw_value, Mapping):
                    path_value = raw_value.get("path")
                    url_value = raw_value.get("url")
                    duration_value = raw_value.get("duration")
                    sample_rate_value = raw_value.get("sampleRate")
                    if isinstance(path_value, str) and path_value.strip():
                        entry["path"] = path_value.strip()
                    if isinstance(url_value, str) and url_value.strip():
                        entry["url"] = url_value.strip()
                    try:
                        entry["duration"] = round(float(duration_value), 6)
                    except (TypeError, ValueError):
                        pass
                    try:
                        entry["sampleRate"] = int(sample_rate_value)
                    except (TypeError, ValueError):
                        pass
                if not entry:
                    return

                existing = audio_tracks_payload.get(key, {})
                merged = dict(existing)
                merged.update(entry)
                audio_tracks_payload[key] = merged

            def _ingest_tracks(candidate: Any) -> None:
                if isinstance(candidate, Mapping):
                    for track_key, track_value in candidate.items():
                        _register_track(track_key, track_value)
                elif isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                    for entry in candidate:
                        if not isinstance(entry, Mapping):
                            continue
                        track_key = entry.get("key") or entry.get("kind")
                        track_value = entry.get("url") or entry.get("path")
                        if track_value is None:
                            track_value = entry.get("source")
                        _register_track(track_key, track_value)

            _ingest_tracks(summary.get("audio_tracks"))
            _ingest_tracks(summary.get("audioTracks"))
            _ingest_tracks(chunk.get("audio_tracks"))
            _ingest_tracks(chunk.get("audioTracks"))

            chunk_records.append(
                PipelineMediaChunk(
                    chunk_id=str(summary.get("chunk_id")) if summary.get("chunk_id") else None,
                    range_fragment=str(summary.get("range_fragment"))
                    if summary.get("range_fragment")
                    else None,
                    start_sentence=_coerce_int(summary.get("start_sentence")),
                    end_sentence=_coerce_int(summary.get("end_sentence")),
                    files=chunk_files,
                    sentences=sentences_payload,
                    metadata_path=metadata_path if isinstance(metadata_path, str) else None,
                    metadata_url=metadata_url if isinstance(metadata_url, str) else None,
                    sentence_count=sentence_count,
                    audio_tracks=audio_tracks_payload,
                )
            )

    files_section = generated_files.get("files")
    if isinstance(files_section, list):
        for entry in files_section:
            if not isinstance(entry, Mapping):
                continue
            record, file_type, signature = _build_media_file(
                job_id,
                entry,
                locator,
                job_root,
                source=source,
            )
            if record is None or file_type is None:
                continue
            if signature in seen:
                continue
            seen.add(signature)
            media_map.setdefault(file_type, []).append(record)

    complete_flag = generated_files.get("complete")
    complete = bool(complete_flag) if isinstance(complete_flag, bool) else False

    return media_map, chunk_records, complete


@router.get("/jobs/{job_id}/media", response_model=PipelineMediaResponse)
async def get_job_media(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return generated media metadata for a completed or persisted job."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    media_entries, chunk_entries, complete = _serialize_media_entries(
        job.job_id,
        job.generated_files,
        file_locator,
        source="completed",
    )
    return PipelineMediaResponse(media=media_entries, chunks=chunk_entries, complete=complete)


@router.get("/jobs/{job_id}/media/live", response_model=PipelineMediaResponse)
async def get_job_media_live(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return live generated media metadata from the active progress tracker."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    generated_payload: Optional[Mapping[str, Any]] = None
    if job.tracker is not None:
        generated_payload = job.tracker.get_generated_files()
    elif job.generated_files is not None:
        generated_payload = job.generated_files

    media_entries, chunk_entries, complete = _serialize_media_entries(
        job.job_id,
        generated_payload,
        file_locator,
        source="live",
    )
    return PipelineMediaResponse(media=media_entries, chunks=chunk_entries, complete=complete)


class _RangeParseError(Exception):
    """Raised when the supplied Range header cannot be satisfied."""


def _parse_byte_range(range_value: str, file_size: int) -> Tuple[int, int]:
    """Return the inclusive byte range requested by ``range_value``.

    ``range_value`` must follow the ``bytes=start-end`` syntax. Only a single range is
    supported and the resulting indices are clamped to the available file size. A
    :class:`_RangeParseError` is raised when the header is malformed or does not
    overlap the file contents.
    """

    if file_size <= 0:
        raise _RangeParseError

    if not range_value.startswith("bytes="):
        raise _RangeParseError

    raw_spec = range_value[len("bytes=") :].strip()
    if "," in raw_spec:
        raise _RangeParseError

    if "-" not in raw_spec:
        raise _RangeParseError

    start_token, end_token = raw_spec.split("-", 1)

    if not start_token:
        # suffix-byte-range-spec: bytes=-N
        if not end_token.isdigit():
            raise _RangeParseError
        length = int(end_token)
        if length <= 0:
            raise _RangeParseError
        start = max(file_size - length, 0)
        end = file_size - 1
    else:
        if not start_token.isdigit():
            raise _RangeParseError
        start = int(start_token)
        if start >= file_size:
            raise _RangeParseError

        if end_token:
            if not end_token.isdigit():
                raise _RangeParseError
            end = int(end_token)
            if end < start:
                raise _RangeParseError
            end = min(end, file_size - 1)
        else:
            end = file_size - 1

    return start, end


def _iter_file_chunks(path: Path, start: int, end: int) -> Iterator[bytes]:
    """Yield chunks from ``path`` between ``start`` and ``end`` (inclusive)."""

    chunk_size = 1 << 16
    total = max(end - start + 1, 0)
    if total <= 0:
        return

    with path.open("rb") as stream:
        stream.seek(start)
        remaining = total
        while remaining > 0:
            chunk = stream.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _stream_local_file(resolved_path: Path, range_header: str | None = None) -> StreamingResponse:
    try:
        stat_result = resolved_path.stat()
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    file_size = int(stat_result.st_size)

    if range_header:
        try:
            start, end = _parse_byte_range(range_header, file_size)
        except _RangeParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Requested range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            ) from exc
        status_code = status.HTTP_206_PARTIAL_CONTENT
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
        }
    else:
        start = 0
        end = file_size - 1 if file_size > 0 else -1
        status_code = status.HTTP_200_OK
        headers = {"Accept-Ranges": "bytes"}

    content_length = max(end - start + 1, 0)
    headers["Content-Length"] = str(content_length)
    # Latin-1 header encoding will fail on filenames with accents; provide a
    # safe ASCII fallback while still advertising the UTF-8 name via RFC 5987.
    original_name = resolved_path.name
    safe_ascii = re.sub(r"[^0-9A-Za-z._-]", "_", original_name) or "download"
    quoted_utf8 = urllib.parse.quote(original_name)
    headers["Content-Disposition"] = (
        f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{quoted_utf8}'
    )

    body_iterator = _iter_file_chunks(resolved_path, start, end)
    media_type = mimetypes.guess_type(resolved_path.name)[0] or "application/octet-stream"
    return StreamingResponse(
        body_iterator,
        status_code=status_code,
        media_type=media_type,
        headers=headers,
    )


async def _download_job_file(
    job_id: str,
    filename: str,
    file_locator: FileLocator,
    range_header: str | None,
):
    """Return a streaming response for the requested job file."""

    try:
        resolved_path = file_locator.resolve_path(job_id, filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return _stream_local_file(resolved_path, range_header)


def _resolve_cover_download_path(filename: str) -> Path:
    root = cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)
    candidate = (root / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return candidate


@storage_router.get("/jobs/{job_id}/files/{filename:path}")
async def download_job_file(
    job_id: str,
    filename: str,
    file_locator: FileLocator = Depends(get_file_locator),
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Stream the requested job file supporting optional byte ranges."""

    return await _download_job_file(job_id, filename, file_locator, range_header)


@storage_router.get("/jobs/{job_id}/{filename:path}")
async def download_job_file_without_prefix(
    job_id: str,
    filename: str,
    file_locator: FileLocator = Depends(get_file_locator),
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Stream job files that were referenced without the legacy ``/files`` prefix."""

    return await _download_job_file(job_id, filename, file_locator, range_header)


@storage_router.get("/covers/{filename:path}")
async def download_cover_file(
    filename: str,
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Serve cover images stored in the shared covers directory."""

    resolved_path = _resolve_cover_download_path(filename)
    return _stream_local_file(resolved_path, range_header)


def register_exception_handlers(app) -> None:
    """Compatibility shim; legacy media routes register their own handlers."""
    return None


__all__ = ["router", "storage_router", "jobs_timing_router", "register_exception_handlers"]
