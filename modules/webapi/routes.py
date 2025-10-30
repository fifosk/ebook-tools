"""API routes for pipeline orchestration."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Mapping, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Header, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from .dependencies import (
    RuntimeContextProvider,
    get_file_locator,
    get_pipeline_service,
    get_runtime_context_provider,
)
from .jobs import PipelineJob, PipelineJobTransitionError
from .. import config_manager as cfg
from ..services.file_locator import FileLocator
from ..services.pipeline_service import PipelineService
from ..search import search_generated_media
from .schemas import (
    MediaSearchHit,
    MediaSearchResponse,
    PipelineJobActionResponse,
    PipelineJobListResponse,
    PipelineMediaFile,
    PipelineMediaResponse,
    PipelineFileBrowserResponse,
    PipelineFileEntry,
    PipelineDefaultsResponse,
    PipelineRequestPayload,
    PipelineStatusResponse,
    PipelineSubmissionResponse,
    ProgressEventPayload,
)

router = APIRouter()
storage_router = APIRouter()


def _format_relative_path(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` using POSIX separators when possible."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return path.as_posix()
    return relative.as_posix() or path.name


def _list_ebook_files(root: Path) -> List[PipelineFileEntry]:
    entries: List[PipelineFileEntry] = []
    if not root.exists():
        return entries
    for path in sorted(root.glob("*.epub")):
        if not path.is_file():
            continue
        entries.append(
            PipelineFileEntry(
                name=path.name,
                path=_format_relative_path(path, root),
                type="file",
            )
        )
    return entries


def _list_output_entries(root: Path) -> List[PipelineFileEntry]:
    entries: List[PipelineFileEntry] = []
    if not root.exists():
        return entries
    for path in sorted(root.iterdir()):
        if path.name.startswith("."):
            continue
        entry_type = "directory" if path.is_dir() else "file"
        entries.append(
            PipelineFileEntry(
                name=path.name,
                path=_format_relative_path(path, root),
                type=entry_type,
            )
        )
    return entries


def _normalise_epub_name(filename: str | None) -> str:
    raw_name = Path(filename or "uploaded.epub").name or "uploaded.epub"
    if raw_name.lower().endswith(".epub"):
        return raw_name
    return f"{raw_name}.epub"


def _reserve_destination_path(directory: Path, filename: str) -> Path:
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".epub"
    candidate = directory / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def _build_action_response(
    job: PipelineJob, *, error: str | None = None
) -> PipelineJobActionResponse:
    return PipelineJobActionResponse(
        job=PipelineStatusResponse.from_job(job),
        error=error,
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


def _serialize_media_entries(
    job_id: str,
    generated_files: Optional[Mapping[str, Any]],
    locator: FileLocator,
    *,
    source: str,
) -> Dict[str, List[PipelineMediaFile]]:
    """Return a mapping of media types to serialized file metadata."""

    media_map: Dict[str, List[PipelineMediaFile]] = {}
    if not isinstance(generated_files, Mapping):
        return media_map

    files_section = generated_files.get("files")
    if not isinstance(files_section, list):
        return media_map

    job_root = locator.resolve_path(job_id)

    for entry in files_section:
        if not isinstance(entry, Mapping):
            continue
        file_type_raw = entry.get("type") or "unknown"
        file_type = str(file_type_raw).lower() or "unknown"

        resolved_path, relative_path = _resolve_media_path(job_id, entry, locator, job_root)

        url: Optional[str] = entry.get("url") if isinstance(entry.get("url"), str) else None
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

        record = PipelineMediaFile(
            name=name,
            url=url,
            size=size,
            updated_at=updated_at,
            source=source,
            relative_path=relative_path,
            path=path_value,
        )
        media_map.setdefault(file_type, []).append(record)

    return media_map


@router.get("/jobs", response_model=PipelineJobListResponse)
async def list_jobs(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Return all persisted jobs ordered by creation time."""

    jobs = pipeline_service.list_jobs(user_id=user_id, user_role=user_role).values()
    ordered = sorted(
        jobs,
        key=lambda job: job.created_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    payload = [PipelineStatusResponse.from_job(job) for job in ordered]
    return PipelineJobListResponse(jobs=payload)


@router.get("/files", response_model=PipelineFileBrowserResponse)
async def list_pipeline_files(
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Return available ebook and output paths for client-side file pickers."""

    with context_provider.activation({}, {}) as context:
        ebooks = _list_ebook_files(context.books_dir)
        outputs = _list_output_entries(context.output_dir)

    return PipelineFileBrowserResponse(
        ebooks=ebooks,
        outputs=outputs,
        books_root=context.books_dir.as_posix(),
        output_root=context.output_dir.as_posix(),
    )


@router.post("/files/upload", response_model=PipelineFileEntry, status_code=status.HTTP_201_CREATED)
async def upload_pipeline_ebook(
    file: UploadFile = File(...),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Persist an uploaded EPUB file into the configured books directory."""

    content_type = (file.content_type or "").lower()
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

    if content_type and content_type not in {
        "application/epub+zip",
        "application/zip",
        "application/octet-stream",
    }:
        if not file.filename.lower().endswith(".epub"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only EPUB files can be uploaded",
            )

    normalised_name = _normalise_epub_name(file.filename)

    with context_provider.activation({}, {}) as context:
        destination_dir = context.books_dir
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = _reserve_destination_path(destination_dir, normalised_name)

        try:
            with destination.open("wb") as buffer:
                while True:
                    chunk = await file.read(1 << 20)
                    if not chunk:
                        break
                    buffer.write(chunk)
        finally:
            await file.close()

    return PipelineFileEntry(
        name=destination.name,
        path=_format_relative_path(destination, destination_dir),
        type="file",
    )


@router.get("/defaults", response_model=PipelineDefaultsResponse)
async def get_pipeline_defaults(
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Return the resolved baseline configuration for client defaults."""

    resolved = context_provider.resolve_config()
    stripped = cfg.strip_derived_config(resolved)
    return PipelineDefaultsResponse(config=stripped)


@router.get("/search", response_model=MediaSearchResponse)
async def search_pipeline_media(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    job_id: str = Query(..., alias="job_id"),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Search across generated ebook media for the provided query."""

    normalized_query = query.strip()
    if not normalized_query:
        return MediaSearchResponse(query=query, limit=limit, count=0, results=[])

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    hits = search_generated_media(
        query=normalized_query,
        jobs=(job,),
        locator=file_locator,
        limit=limit,
    )

    serialized_hits: list[MediaSearchHit] = []
    for hit in hits:
        media_payload: dict[str, list[PipelineMediaFile]] = {}
        for category, entries in hit.media.items():
            if not entries:
                continue
            files: list[PipelineMediaFile] = []
            for entry in entries:
                size_value = entry.get("size")
                if isinstance(size_value, (int, float)):
                    file_size = int(size_value)
                else:
                    file_size = None
                media_file = PipelineMediaFile(
                    name=str(entry.get("name") or "media"),
                    url=entry.get("url"),
                    size=file_size,
                    updated_at=entry.get("updated_at"),
                    source=str(entry.get("source") or "completed"),
                    relative_path=entry.get("relative_path"),
                    path=entry.get("path"),
                )
                files.append(media_file)
            if files:
                media_payload[category] = files
        serialized_hits.append(
            MediaSearchHit(
                job_id=hit.job_id,
                job_label=hit.job_label,
                base_id=hit.base_id,
                chunk_id=hit.chunk_id,
                range_fragment=hit.range_fragment,
                start_sentence=hit.start_sentence,
                end_sentence=hit.end_sentence,
                snippet=hit.snippet,
                occurrence_count=hit.occurrence_count,
                match_start=hit.match_start,
                match_end=hit.match_end,
                text_length=hit.text_length,
                offset_ratio=hit.offset_ratio,
                approximate_time_seconds=hit.approximate_time_seconds,
                media=media_payload,
            )
        )

    return MediaSearchResponse(
        query=normalized_query,
        limit=limit,
        count=len(serialized_hits),
        results=serialized_hits,
    )


@router.post("/", response_model=PipelineSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_pipeline(
    payload: PipelineRequestPayload,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Submit a pipeline execution request and return an identifier."""

    resolved_config = context_provider.resolve_config(payload.config)
    context_overrides = dict(payload.environment_overrides)
    context_overrides.update(payload.pipeline_overrides)
    context = context_provider.build_context(
        resolved_config,
        context_overrides,
    )
    request = payload.to_pipeline_request(
        context=context,
        resolved_config=resolved_config,
    )
    job = pipeline_service.enqueue(request, user_id=user_id, user_role=user_role)
    return PipelineSubmissionResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
    )


@router.post("/{job_id}/metadata/refresh", response_model=PipelineStatusResponse)
async def refresh_pipeline_metadata(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Trigger metadata inference again for ``job_id`` and return the updated status."""

    try:
        job = pipeline_service.refresh_metadata(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return PipelineStatusResponse.from_job(job)


@router.get("/{job_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Return the latest status for the requested job."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return PipelineStatusResponse.from_job(job)


@router.get("/jobs/{job_id}/media", response_model=PipelineMediaResponse)
async def get_job_media(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Return generated media metadata for a completed or persisted job."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    media_entries = _serialize_media_entries(
        job.job_id,
        job.generated_files,
        file_locator,
        source="completed",
    )
    return PipelineMediaResponse(media=media_entries)


@router.get("/jobs/{job_id}/media/live", response_model=PipelineMediaResponse)
async def get_job_media_live(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Return live generated media metadata from the active progress tracker."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
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

    media_entries = _serialize_media_entries(
        job.job_id,
        generated_payload,
        file_locator,
        source="live",
    )
    return PipelineMediaResponse(media=media_entries)


def _handle_job_action(
    job_id: str,
    action: Callable[..., PipelineJob],
    *,
    user_id: str | None = None,
    user_role: str | None = None,
) -> PipelineJobActionResponse:
    try:
        job = action(job_id, user_id=user_id, user_role=user_role)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PipelineJobTransitionError as exc:
        return _build_action_response(exc.job, error=str(exc))
    return _build_action_response(job)


@router.post("/jobs/{job_id}/pause", response_model=PipelineJobActionResponse)
async def pause_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Pause the specified job if possible."""

    return _handle_job_action(
        job_id,
        pipeline_service.pause_job,
        user_id=user_id,
        user_role=user_role,
    )


@router.post("/jobs/{job_id}/resume", response_model=PipelineJobActionResponse)
async def resume_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Resume a paused job."""

    return _handle_job_action(
        job_id,
        pipeline_service.resume_job,
        user_id=user_id,
        user_role=user_role,
    )


@router.post("/jobs/{job_id}/cancel", response_model=PipelineJobActionResponse)
async def cancel_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Cancel a running or pending job."""

    return _handle_job_action(
        job_id,
        pipeline_service.cancel_job,
        user_id=user_id,
        user_role=user_role,
    )


@router.post("/jobs/{job_id}/delete", response_model=PipelineJobActionResponse)
async def delete_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Delete persisted metadata for a job."""

    return _handle_job_action(
        job_id,
        pipeline_service.delete_job,
        user_id=user_id,
        user_role=user_role,
    )


async def _event_stream(job: PipelineJob) -> AsyncIterator[bytes]:
    if job.completed_at and job.last_event is not None:
        payload = ProgressEventPayload.from_event(job.last_event)
        yield f"data: {payload.model_dump_json()}\n\n".encode("utf-8")
        return

    if job.tracker is None:
        if job.last_event is not None:
            payload = ProgressEventPayload.from_event(job.last_event)
            yield f"data: {payload.model_dump_json()}\n\n".encode("utf-8")
        return

    stream = job.tracker.events()
    try:
        async for event in stream:
            payload = ProgressEventPayload.from_event(event)
            yield f"data: {payload.model_dump_json()}\n\n".encode("utf-8")
            if event.event_type == "complete":
                break
    finally:
        await stream.aclose()


@router.get("/{job_id}/events")
async def stream_pipeline_events(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
):
    """Stream progress events for ``job_id`` as Server-Sent Events."""

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=user_id,
            user_role=user_role,
        )
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    generator = _event_stream(job)
    return StreamingResponse(generator, media_type="text/event-stream")


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
    response = StreamingResponse(
        body_iterator,
        status_code=status_code,
        media_type="application/octet-stream",
        headers=headers,
    )
    return response


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


__all__ = ["router", "storage_router"]
