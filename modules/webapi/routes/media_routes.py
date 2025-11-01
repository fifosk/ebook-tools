"""Routes for pipeline media metadata and downloads."""

from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from ... import config_manager as cfg
from ...services.file_locator import FileLocator
from ...services.pipeline_service import PipelineService
from ..dependencies import (
    RequestUserContext,
    get_file_locator,
    get_pipeline_service,
    get_request_user,
)
from ..schemas import PipelineMediaChunk, PipelineMediaFile, PipelineMediaResponse

router = APIRouter()
storage_router = APIRouter()

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
) -> tuple[Dict[str, List[PipelineMediaFile]], List[PipelineMediaChunk], bool]:
    """Return serialized media metadata grouped by type and chunk."""

    media_map: Dict[str, List[PipelineMediaFile]] = {}
    chunk_records: List[PipelineMediaChunk] = []
    complete = False

    if not isinstance(generated_files, Mapping):
        return media_map, chunk_records, complete

    job_root = locator.resolve_path(job_id)
    seen: set[tuple[str, str]] = set()

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
            if chunk_files:
                chunk_records.append(
                    PipelineMediaChunk(
                        chunk_id=str(chunk.get("chunk_id")) if chunk.get("chunk_id") else None,
                        range_fragment=str(chunk.get("range_fragment"))
                        if chunk.get("range_fragment")
                        else None,
                        start_sentence=_coerce_int(chunk.get("start_sentence")),
                        end_sentence=_coerce_int(chunk.get("end_sentence")),
                        files=chunk_files,
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
    headers["Content-Disposition"] = f'attachment; filename="{resolved_path.name}"'

    body_iterator = _iter_file_chunks(resolved_path, start, end)
    return StreamingResponse(
        body_iterator,
        status_code=status_code,
        media_type="application/octet-stream",
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


__all__ = ["router", "storage_router"]
