"""Media metadata routes for pipeline outputs."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from fastapi import APIRouter, Depends, HTTPException, status

from ....metadata_manager import MetadataLoader
from ....services.file_locator import FileLocator
from ....services.pipeline_service import PipelineService
from ...dependencies import (
    RequestUserContext,
    get_file_locator,
    get_pipeline_service,
    get_request_user,
)
from ...schemas import PipelineMediaChunk, PipelineMediaFile, PipelineMediaResponse

router = APIRouter()


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
    )


@router.get("/jobs/{job_id}/media", response_model=PipelineMediaResponse)
async def get_job_media(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return generated media metadata for a job."""

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
    return PipelineMediaResponse(media=media_entries, chunks=chunk_entries, complete=complete)


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
        loader = MetadataLoader(file_locator.resolve_path(job_id))
    except Exception:  # pragma: no cover - defensive logging
        loader = None

    serialized = _serialize_chunk_entry(
        job_id,
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
    return PipelineMediaResponse(media=media_entries, chunks=chunk_entries, complete=complete)
