"""API routes for pipeline orchestration."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Mapping, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Header, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse, Response

from .dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_file_locator,
    get_library_service,
    get_pipeline_service,
    get_request_user,
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
    PipelineMediaChunk,
    PipelineMediaResponse,
    PipelineFileBrowserResponse,
    PipelineFileEntry,
    PipelineFileDeleteRequest,
    PipelineDefaultsResponse,
    PipelineRequestPayload,
    PipelineStatusResponse,
    PipelineSubmissionResponse,
    ProgressEventPayload,
)
from modules.library.library_service import LibraryError, LibraryNotFoundError, LibraryService

router = APIRouter()
storage_router = APIRouter()


class _LibrarySearchJobAdapter:
    """Minimal adapter that exposes library metadata to the media search helpers."""

    __slots__ = ("job_id", "generated_files", "request", "resume_context", "request_payload")

    def __init__(
        self,
        job_id: str,
        generated_files: Mapping[str, Any],
        *,
        label: Optional[str] = None,
    ) -> None:
        self.job_id = job_id
        self.generated_files = generated_files
        self.request: Any = None
        self.resume_context: Optional[Mapping[str, Any]] = None
        if label:
            self.request_payload: Optional[Mapping[str, Any]] = {
                "inputs": {"book_metadata": {"title": label}}
            }
        else:
            self.request_payload = None


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


def _extract_match_snippet(text: Any, query: str) -> Optional[str]:
    if not isinstance(text, str):
        return None
    stripped_query = query.strip()
    if not stripped_query:
        return None

    tokens = [token for token in stripped_query.split() if token]
    if not tokens:
        return None

    lower_text = text.lower()
    for token in tokens:
        lower_token = token.lower()
        index = lower_text.find(lower_token)
        if index == -1:
            continue
        window = 60
        start = max(0, index - window)
        end = min(len(text), index + len(lower_token) + window)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = f"…{snippet}"
        if end < len(text):
            snippet = f"{snippet}…"
        return snippet
    return None


def _build_library_search_snippet(item: Mapping[str, Any], query: str) -> str:
    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        book_metadata = metadata.get("book_metadata")
        if isinstance(book_metadata, Mapping):
            preferred_keys = [
                "book_summary",
                "summary",
                "description",
                "synopsis",
            ]
            for key in preferred_keys:
                snippet = _extract_match_snippet(book_metadata.get(key), query)
                if snippet:
                    return snippet

    fallback_candidates = [
        item.get("book_title"),
        item.get("author"),
        item.get("genre"),
    ]
    for candidate in fallback_candidates:
        snippet = _extract_match_snippet(candidate, query)
        if snippet:
            return snippet

    title = item.get("book_title") or "Library entry"
    author = item.get("author") or ""
    language = item.get("language") or ""
    genre = item.get("genre") or ""

    parts = [title]
    if author:
        parts.append(f"by {author}")
    summary_parts: List[str] = []
    if language:
        summary_parts.append(language)
    if genre:
        summary_parts.append(genre)
    if summary_parts:
        parts.append(f"({' • '.join(summary_parts)})")

    return " ".join(parts).strip()


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


def _find_job_cover_path(metadata_root: Path) -> Optional[Path]:
    if not metadata_root.exists():
        return None
    for candidate in sorted(metadata_root.glob("cover.*")):
        if candidate.is_file():
            return candidate
    return None


def _guess_cover_media_type(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(path.name)
    return media_type or "image/jpeg"


@router.get("/jobs", response_model=PipelineJobListResponse)
async def list_jobs(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return all persisted jobs ordered by creation time."""

    jobs = pipeline_service.list_jobs(
        user_id=request_user.user_id,
        user_role=request_user.user_role,
    ).values()
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


@router.delete("/files", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline_ebook(
    payload: PipelineFileDeleteRequest,
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Remove an existing EPUB from the configured books directory."""

    with context_provider.activation({}, {}) as context:
        books_dir = context.books_dir
        target = (books_dir / payload.path).resolve()

        try:
            target.relative_to(books_dir)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ebook path",
            ) from exc

        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ebook not found",
            )

        if not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only files can be deleted",
            )

        try:
            target.unlink()
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to delete ebook: {exc}",
            ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    library_service: LibraryService = Depends(get_library_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Search across generated ebook media for the provided query."""

    normalized_query = query.strip()
    if not normalized_query:
        return MediaSearchResponse(query=query, limit=limit, count=0, results=[])

    library_item = library_service.get_item(job_id) if library_service is not None else None

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError:
        job = None
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if job is None and library_item is None:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    jobs_to_search: List[PipelineJob | _LibrarySearchJobAdapter] = []
    if job is not None:
        jobs_to_search.append(job)
    elif library_item is not None:
        serialized_item = library_service.serialize_item(library_item)
        metadata_payload = serialized_item.get("metadata")
        generated_files = (
            metadata_payload.get("generated_files") if isinstance(metadata_payload, Mapping) else None
        )
        if isinstance(generated_files, Mapping):
            label = serialized_item.get("book_title") or metadata_payload.get("book_title")
            jobs_to_search.append(
                _LibrarySearchJobAdapter(
                    job_id=job_id,
                    generated_files=generated_files,
                    label=label if isinstance(label, str) and label.strip() else None,
                )
            )

    hits = search_generated_media(
        query=normalized_query,
        jobs=tuple(jobs_to_search),
        locator=file_locator,
        limit=limit,
    ) if jobs_to_search else []

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
                source="pipeline",
            )
        )

    available_slots = max(limit - len(serialized_hits), 0)
    library_hits: list[MediaSearchHit] = []
    if library_service is not None and available_slots > 0:
        try:
            library_search = library_service.search(
                query=normalized_query,
                page=1,
                limit=min(available_slots, limit),
            )
        except LibraryError:
            library_search = None

        if library_search is not None:
            seen_ids = {hit.job_id for hit in serialized_hits}
            for entry in library_search.items:
                serialized_item = library_service.serialize_item(entry)
                job_identifier = serialized_item.get("job_id") or entry.id
                if job_identifier in seen_ids:
                    continue
                snippet = _build_library_search_snippet(serialized_item, normalized_query)
                library_hits.append(
                    MediaSearchHit(
                        job_id=job_identifier,
                        job_label=serialized_item.get("book_title") or job_identifier,
                        base_id=None,
                        chunk_id=None,
                        range_fragment=None,
                        start_sentence=None,
                        end_sentence=None,
                        snippet=snippet,
                        occurrence_count=1,
                        match_start=None,
                        match_end=None,
                        text_length=None,
                        offset_ratio=None,
                        approximate_time_seconds=None,
                        media={},
                        source="library",
                        library_author=serialized_item.get("author"),
                        library_genre=serialized_item.get("genre"),
                        library_language=serialized_item.get("language"),
                        cover_path=serialized_item.get("cover_path"),
                        library_path=serialized_item.get("library_path"),
                    )
                )
                seen_ids.add(job_identifier)
                if len(library_hits) >= available_slots:
                    break

    combined_results = serialized_hits + library_hits

    return MediaSearchResponse(
        query=normalized_query,
        limit=limit,
        count=len(combined_results),
        results=combined_results,
    )


@router.post("/", response_model=PipelineSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_pipeline(
    payload: PipelineRequestPayload,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
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
    job = pipeline_service.enqueue(
        request,
        user_id=request_user.user_id,
        user_role=request_user.user_role,
    )
    return PipelineSubmissionResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
    )


@router.post("/{job_id}/metadata/refresh", response_model=PipelineStatusResponse)
async def refresh_pipeline_metadata(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Trigger metadata inference again for ``job_id`` and return the updated status."""

    try:
        job = pipeline_service.refresh_metadata(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
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
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return the latest status for the requested job."""

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

    return PipelineStatusResponse.from_job(job)


@router.get("/{job_id}/cover")
async def fetch_job_cover(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    library_service: LibraryService = Depends(get_library_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return the stored cover image for ``job_id`` if available."""

    permission_denied = False
    job_missing = False
    try:
        pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except PermissionError:
        permission_denied = True
    except KeyError:
        job_missing = True

    metadata_root = file_locator.metadata_root(job_id)
    cover_path = _find_job_cover_path(metadata_root)

    if (cover_path is None or not cover_path.is_file()) and library_service is not None:
        try:
            library_cover = library_service.find_cover_asset(job_id)
        except LibraryNotFoundError:
            library_cover = None
        if library_cover is not None and library_cover.is_file():
            cover_path = library_cover

    if cover_path is None or not cover_path.is_file():
        if job_missing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")
        if permission_denied:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access cover")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found")

    media_type = _guess_cover_media_type(cover_path)
    response = FileResponse(
        cover_path,
        media_type=media_type,
        filename=cover_path.name,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{cover_path.name}"'
    return response


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


def _handle_job_action(
    job_id: str,
    action: Callable[..., PipelineJob],
    *,
    request_user: RequestUserContext,
) -> PipelineJobActionResponse:
    try:
        job = action(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
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
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Pause the specified job if possible."""

    return _handle_job_action(
        job_id,
        pipeline_service.pause_job,
        request_user=request_user,
    )


@router.post("/jobs/{job_id}/resume", response_model=PipelineJobActionResponse)
async def resume_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Resume a paused job."""

    return _handle_job_action(
        job_id,
        pipeline_service.resume_job,
        request_user=request_user,
    )


@router.post("/jobs/{job_id}/cancel", response_model=PipelineJobActionResponse)
async def cancel_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Cancel a running or pending job."""

    return _handle_job_action(
        job_id,
        pipeline_service.cancel_job,
        request_user=request_user,
    )


@router.post("/jobs/{job_id}/delete", response_model=PipelineJobActionResponse)
async def delete_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Delete persisted metadata for a job."""

    return _handle_job_action(
        job_id,
        pipeline_service.delete_job,
        request_user=request_user,
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
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Stream progress events for ``job_id`` as Server-Sent Events."""

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


@storage_router.get("/covers/{filename:path}")
async def download_cover_file(
    filename: str,
    range_header: str | None = Header(default=None, alias="Range"),
):
    """Serve cover images stored in the shared covers directory."""

    resolved_path = _resolve_cover_download_path(filename)
    return _stream_local_file(resolved_path, range_header)


__all__ = ["router", "storage_router"]
