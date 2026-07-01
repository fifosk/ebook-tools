"""Media metadata routes for pipeline outputs."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from ....metadata_manager import MetadataLoader
from ....services.file_locator import FileLocator
from ....services.pipeline_service import PipelineService
from ....services.source_discovery import safe_stat
from ...dependencies import (
    RequestUserContext,
    get_file_locator,
    get_pipeline_service,
    get_request_user,
)
from ...route_telemetry import log_started_route_result
from ...schemas import (
    PipelineMediaChunk,
    PipelineMediaDiagnostics,
    PipelineMediaFile,
    PipelineMediaResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

MEDIA_JOB_NOT_FOUND_MESSAGE = "Job not found"
MEDIA_JOB_FORBIDDEN_MESSAGE = "Not authorized to access job media"


def _normalize_route_id(value: str) -> str:
    return value.strip()


def _get_media_job(
    job_id: str,
    *,
    pipeline_service: PipelineService,
    request_user: RequestUserContext,
    operation: str | None = None,
    source: str | None = None,
    started_at: float | None = None,
) -> Any:
    normalized_job_id = _normalize_route_id(job_id)
    if not normalized_job_id:
        if operation and source and started_at is not None:
            _log_media_manifest(operation, started_at, result="not_found", source=source)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MEDIA_JOB_NOT_FOUND_MESSAGE,
        )
    try:
        return pipeline_service.get_job(
            normalized_job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        if operation and source and started_at is not None:
            _log_media_manifest(operation, started_at, result="not_found", source=source)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MEDIA_JOB_NOT_FOUND_MESSAGE,
        ) from exc
    except PermissionError as exc:
        if operation and source and started_at is not None:
            _log_media_manifest(operation, started_at, result="forbidden", source=source)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MEDIA_JOB_FORBIDDEN_MESSAGE,
        ) from exc


def _log_media_manifest(
    operation: str,
    started_at: float,
    *,
    result: str,
    source: str,
    category_count: int = 0,
    media_file_count: int = 0,
    chunk_count: int = 0,
    complete: Optional[bool] = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="MEDIA_ROUTE_DURATION",
        message="Pipeline media manifest",
        operation=operation,
        result=result,
        started_at=started_at,
        duration_first=False,
        source=source,
        categories=category_count,
        files=media_file_count,
        chunks=chunk_count,
        complete=str(complete) if complete is not None else None,
    )


def _file_type_matches(file: PipelineMediaFile, candidates: set[str]) -> bool:
    value = (file.type or file.name or "").lower()
    return any(candidate in value for candidate in candidates)


def _chunk_has_timing(chunk: PipelineMediaChunk) -> bool:
    if chunk.timing_tracks:
        return any(entries for entries in chunk.timing_tracks.values())
    return any(sentence.timeline for sentence in chunk.sentences)


def _chunk_has_image(chunk: PipelineMediaChunk) -> bool:
    if any(_file_type_matches(file, {"image", "png", "jpg", "jpeg", "webp"}) for file in chunk.files):
        return True
    return any(sentence.image is not None or sentence.image_path for sentence in chunk.sentences)


def _build_media_diagnostics(
    media_entries: Mapping[str, Sequence[PipelineMediaFile]],
    chunk_entries: Sequence[PipelineMediaChunk],
) -> PipelineMediaDiagnostics:
    media_files = [file for entries in media_entries.values() for file in entries]
    chunk_files = [file for chunk in chunk_entries for file in chunk.files]

    return PipelineMediaDiagnostics(
        media_file_count=len(media_files),
        chunk_count=len(chunk_entries),
        chunk_file_count=len(chunk_files),
        audio_file_count=sum(
            1 for file in media_files if _file_type_matches(file, {"audio", "mp3", "wav", "m4a"})
        ),
        image_file_count=sum(
            1
            for file in media_files
            if _file_type_matches(file, {"image", "png", "jpg", "jpeg", "webp"})
        ),
        chunks_with_audio=sum(
            1
            for chunk in chunk_entries
            if chunk.audio_tracks
            or any(_file_type_matches(file, {"audio", "mp3", "wav", "m4a"}) for file in chunk.files)
        ),
        chunks_with_timing=sum(1 for chunk in chunk_entries if _chunk_has_timing(chunk)),
        chunks_with_images=sum(1 for chunk in chunk_entries if _chunk_has_image(chunk)),
        chunks_without_files=sum(1 for chunk in chunk_entries if not chunk.files),
        chunks_without_metadata=sum(
            1
            for chunk in chunk_entries
            if not chunk.metadata_path and not chunk.metadata_url and not chunk.sentences
        ),
        files_without_url=sum(1 for file in media_files if not file.url),
        files_without_size=sum(1 for file in media_files if file.size is None),
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


def _range_fragment_bounds(value: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    if not isinstance(value, str):
        return None, None
    numbers = re.findall(r"\d+", value)
    if not numbers:
        return None, None
    start = _coerce_int(numbers[0])
    end = _coerce_int(numbers[1]) if len(numbers) > 1 else None
    return start, end


def _chunk_sentence_sort_key(chunk: PipelineMediaChunk, index: int) -> tuple[int, int, int, int]:
    start = chunk.start_sentence
    end = chunk.end_sentence

    if start is None and chunk.sentences:
        start = chunk.sentences[0].sentence_number

    if start is None:
        start, parsed_end = _range_fragment_bounds(chunk.range_fragment)
        if end is None:
            end = parsed_end

    if start is None:
        start, parsed_end = _range_fragment_bounds(chunk.chunk_id)
        if end is None:
            end = parsed_end

    if end is None:
        end = start

    if start is None:
        return (1, index, index, index)
    return (0, start, end if end is not None else start, index)


def _sort_media_chunks(chunks: Sequence[PipelineMediaChunk]) -> List[PipelineMediaChunk]:
    return [
        chunk
        for _index, chunk in sorted(
            enumerate(chunks),
            key=lambda item: _chunk_sentence_sort_key(item[1], item[0]),
        )
    ]


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
    if resolved_path is not None:
        stat_result = safe_stat(resolved_path)
        if stat_result is not None:
            size = int(stat_result.st_size)
            updated_at = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)
    if size is None:
        for size_key in ("size", "size_bytes", "sizeBytes"):
            size_candidate = _coerce_int(entry.get(size_key))
            if size_candidate is not None and size_candidate >= 0:
                size = size_candidate
                break

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
        if safe_stat(manifest_path) is None:
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

            # Fallback: derive sentence_count from start/end when still missing.
            if not sentence_count:
                start = _coerce_int(summary.get("start_sentence"))
                end = _coerce_int(summary.get("end_sentence"))
                if start is not None and end is not None and end > start:
                    sentence_count = end - start

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

            timing_tracks_payload: Optional[Dict[str, List[Dict[str, Any]]]] = None
            raw_timing = summary.get("timing_tracks") or summary.get("timingTracks")
            if raw_timing is None:
                raw_timing = chunk.get("timing_tracks") or chunk.get("timingTracks")
            if isinstance(raw_timing, Mapping):
                timing_tracks_payload = {}
                for track_key, track_entries in raw_timing.items():
                    if isinstance(track_key, str) and isinstance(track_entries, list):
                        timing_tracks_payload[track_key] = copy.deepcopy(track_entries)

            # Extract timing version (v2 = pre-scaled timing from backend)
            raw_timing_version = (
                summary.get("timing_version")
                or summary.get("timingVersion")
                or chunk.get("timing_version")
                or chunk.get("timingVersion")
            )
            timing_version = str(raw_timing_version).strip() if raw_timing_version else ("2" if timing_tracks_payload else None)

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
                    timing_tracks=timing_tracks_payload,
                    timing_version=timing_version,
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

    return media_map, _sort_media_chunks(chunk_records), complete


def _resolve_chunk_entry(
    chunks: Sequence[Any],
    chunk_id: str,
) -> Optional[Mapping[str, Any]]:
    chunk_id = chunk_id.strip()
    if not chunk_id:
        return None
    if chunk_id.startswith("chunk-"):
        raw_index = chunk_id.replace("chunk-", "", 1)
        try:
            index = int(raw_index)
        except ValueError:
            index = None
        if index is not None and 0 <= index < len(chunks):
            entry = chunks[index]
            if isinstance(entry, Mapping):
                return entry
    for entry in chunks:
        if not isinstance(entry, Mapping):
            continue
        raw_id = entry.get("chunk_id") or entry.get("chunkId")
        if raw_id is not None and str(raw_id) == chunk_id:
            return entry
        range_fragment = entry.get("range_fragment") or entry.get("rangeFragment")
        if range_fragment is not None and str(range_fragment) == chunk_id:
            return entry
    return None


def _serialize_chunk_entry(
    job_id: str,
    chunk: Mapping[str, Any],
    locator: FileLocator,
    *,
    source: str,
    include_sentences: bool,
    metadata_loader: Optional[MetadataLoader] = None,
) -> Optional[PipelineMediaChunk]:
    job_root = locator.resolve_path(job_id)
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
        record, _file_type, _signature = _build_media_file(
            job_id,
            enriched_entry,
            locator,
            job_root,
            source=source,
        )
        if record is None:
            continue
        chunk_files.append(record)

    summary: Mapping[str, Any] = chunk
    if metadata_loader is not None:
        try:
            summary = metadata_loader.load_chunk(chunk, include_sentences=include_sentences)
        except Exception:  # pragma: no cover - defensive logging
            summary = chunk

    metadata_path = summary.get("metadata_path")
    metadata_url = summary.get("metadata_url")
    sentence_count = _coerce_int(summary.get("sentence_count"))

    sentences_payload: List[Any] = []
    if include_sentences:
        if metadata_loader is not None:
            sentences_payload = metadata_loader.load_chunk_sentences(chunk)
        else:
            inline_sentences = summary.get("sentences") or chunk.get("sentences")
            if isinstance(inline_sentences, list):
                sentences_payload = copy.deepcopy(inline_sentences)
        if sentence_count is None:
            sentence_count = len(sentences_payload)

    # Fallback: derive sentence_count from start/end when still missing.
    if not sentence_count:
        start = _coerce_int(summary.get("start_sentence"))
        end = _coerce_int(summary.get("end_sentence"))
        if start is not None and end is not None and end > start:
            sentence_count = end - start

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

    timing_tracks_payload: Optional[Dict[str, List[Dict[str, Any]]]] = None
    raw_timing = summary.get("timing_tracks") or summary.get("timingTracks")
    if raw_timing is None:
        raw_timing = chunk.get("timing_tracks") or chunk.get("timingTracks")
    if isinstance(raw_timing, Mapping):
        timing_tracks_payload = {}
        for track_key, track_entries in raw_timing.items():
            if isinstance(track_key, str) and isinstance(track_entries, list):
                timing_tracks_payload[track_key] = copy.deepcopy(track_entries)

    # Extract timing version (v2 = pre-scaled timing from backend)
    raw_timing_version = (
        summary.get("timing_version")
        or summary.get("timingVersion")
        or chunk.get("timing_version")
        or chunk.get("timingVersion")
    )
    timing_version = str(raw_timing_version).strip() if raw_timing_version else ("2" if timing_tracks_payload else None)

    return PipelineMediaChunk(
        chunk_id=str(summary.get("chunk_id")) if summary.get("chunk_id") else None,
        range_fragment=str(summary.get("range_fragment")) if summary.get("range_fragment") else None,
        start_sentence=_coerce_int(summary.get("start_sentence")),
        end_sentence=_coerce_int(summary.get("end_sentence")),
        files=chunk_files,
        sentences=sentences_payload,
        metadata_path=metadata_path if isinstance(metadata_path, str) else None,
        metadata_url=metadata_url if isinstance(metadata_url, str) else None,
        sentence_count=sentence_count,
        audio_tracks=audio_tracks_payload,
        timing_tracks=timing_tracks_payload,
        timing_version=timing_version,
    )


@router.get("/jobs/{job_id}/media", response_model=PipelineMediaResponse)
async def get_job_media(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return generated media metadata for a job."""

    started_at = time.perf_counter()
    operation = "job_media"
    job = _get_media_job(
        job_id,
        pipeline_service=pipeline_service,
        request_user=request_user,
        operation=operation,
        source="completed",
        started_at=started_at,
    )

    try:
        generated_payload: Optional[Mapping[str, Any]] = None
        if job.media_completed and job.generated_files is not None:
            generated_payload = job.generated_files
        elif job.tracker is not None:
            generated_payload = job.tracker.get_generated_files()
        elif job.generated_files is not None:
            generated_payload = job.generated_files

        media_entries, chunk_entries, complete = _serialize_media_entries(
            job.job_id,
            generated_payload,
            file_locator,
            source="completed",
        )
    except Exception:
        _log_media_manifest(operation, started_at, result="error", source="completed")
        raise
    media_file_count = sum(len(entries) for entries in media_entries.values())
    _log_media_manifest(
        operation,
        started_at,
        result="success",
        source="completed",
        category_count=len(media_entries),
        media_file_count=media_file_count,
        chunk_count=len(chunk_entries),
        complete=complete,
    )
    return PipelineMediaResponse(
        media=media_entries,
        chunks=chunk_entries,
        complete=complete,
        diagnostics=_build_media_diagnostics(media_entries, chunk_entries),
    )


@router.get(
    "/jobs/{job_id}/media/chunks/{chunk_id}",
    response_model=PipelineMediaChunk,
    status_code=status.HTTP_200_OK,
)
async def get_job_media_chunk(
    job_id: str,
    chunk_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
) -> PipelineMediaChunk:
    """Return sentence metadata for a single chunk."""

    job = _get_media_job(
        job_id,
        pipeline_service=pipeline_service,
        request_user=request_user,
    )

    generated_payload: Optional[Mapping[str, Any]] = None
    if job.media_completed and job.generated_files is not None:
        generated_payload = job.generated_files
    elif job.tracker is not None:
        generated_payload = job.tracker.get_generated_files()
    elif job.generated_files is not None:
        generated_payload = job.generated_files

    if not isinstance(generated_payload, Mapping):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    chunks_section = generated_payload.get("chunks")
    if not isinstance(chunks_section, list):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    chunk_entry = _resolve_chunk_entry(chunks_section, chunk_id)
    if not isinstance(chunk_entry, Mapping):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    loader: Optional[MetadataLoader] = None
    try:
        loader = MetadataLoader(file_locator.resolve_path(job.job_id))
    except Exception:  # pragma: no cover - defensive logging
        loader = None

    serialized = _serialize_chunk_entry(
        job.job_id,
        chunk_entry,
        file_locator,
        source="completed",
        include_sentences=True,
        metadata_loader=loader,
    )
    if serialized is None or not serialized.sentences:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk metadata unavailable")
    return serialized


@router.get("/jobs/{job_id}/media/live", response_model=PipelineMediaResponse)
async def get_job_media_live(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return live generated media metadata from the active progress tracker."""

    started_at = time.perf_counter()
    operation = "job_media_live"
    job = _get_media_job(
        job_id,
        pipeline_service=pipeline_service,
        request_user=request_user,
        operation=operation,
        source="live",
        started_at=started_at,
    )

    try:
        generated_payload: Optional[Mapping[str, Any]] = None
        if job.media_completed and job.generated_files is not None:
            generated_payload = job.generated_files
        elif job.tracker is not None:
            generated_payload = job.tracker.get_generated_files()
        elif job.generated_files is not None:
            generated_payload = job.generated_files

        media_entries, chunk_entries, complete = _serialize_media_entries(
            job.job_id,
            generated_payload,
            file_locator,
            source="live",
        )
    except Exception:
        _log_media_manifest(operation, started_at, result="error", source="live")
        raise
    media_file_count = sum(len(entries) for entries in media_entries.values())
    _log_media_manifest(
        operation,
        started_at,
        result="success",
        source="live",
        category_count=len(media_entries),
        media_file_count=media_file_count,
        chunk_count=len(chunk_entries),
        complete=complete,
    )
    return PipelineMediaResponse(
        media=media_entries,
        chunks=chunk_entries,
        complete=complete,
        diagnostics=_build_media_diagnostics(media_entries, chunk_entries),
    )
