"""Routes powering the Library feature."""

from __future__ import annotations

import mimetypes
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Literal, Mapping, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from ..dependencies import (
    get_library_service,
    get_library_sync,
    get_pipeline_service,
    get_request_user,
    RequestUserContext,
)
from ..routes.media_routes import _stream_local_file
from ..schemas import (
    LibraryItemPayload,
    LibraryMediaRemovalResponse,
    LibraryMetadataUpdateRequest,
    LibraryMoveRequest,
    LibraryMoveResponse,
    LibraryIsbnLookupResponse,
    LibraryIsbnUpdateRequest,
    LibraryReindexResponse,
    LibrarySearchResponse,
    AccessPolicyPayload,
    AccessPolicyUpdateRequest,
    PipelineMediaChunk,
    PipelineMediaFile,
    PipelineMediaResponse,
)
from ...library import (
    LibraryConflictError,
    LibraryError,
    LibraryEntry,
    LibraryNotFoundError,
    LibraryService,
    LibrarySync,
)
from ... import logging_manager
from ...services.pipeline_service import PipelineService
from modules.permissions import can_access, resolve_access_policy


router = APIRouter(prefix="/api/library", tags=["library"])
LOGGER = logging_manager.get_logger().getChild("webapi.library")

# Ensure common subtitle MIME types are recognized when serving from the library.
mimetypes.add_type("text/vtt", ".vtt")
mimetypes.add_type("text/x-srt", ".srt")
mimetypes.add_type("text/plain", ".ass")


def _library_owner_id(item: LibraryEntry) -> str | None:
    if item.owner_id:
        return item.owner_id
    metadata = item.metadata.data if hasattr(item.metadata, "data") else {}
    owner = metadata.get("user_id") or metadata.get("owner_id")
    if isinstance(owner, str):
        trimmed = owner.strip()
        return trimmed or None
    return None


def _resolve_library_access(item: LibraryEntry):
    metadata = item.metadata.data if hasattr(item.metadata, "data") else {}
    return resolve_access_policy(metadata.get("access"), default_visibility="public")


def _ensure_library_access(
    item: LibraryEntry,
    request_user: RequestUserContext,
    *,
    permission: str,
) -> None:
    policy = _resolve_library_access(item)
    owner_id = _library_owner_id(item)
    if can_access(
        policy,
        owner_id=owner_id,
        user_id=request_user.user_id,
        user_role=request_user.user_role,
        permission=permission,
    ):
        return
    detail = "Not authorized to access library item"
    if permission == "edit":
        detail = "Not authorized to modify library item"
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


@router.post("/move/{job_id}", response_model=LibraryMoveResponse)
async def move_job_to_library(
    job_id: str,
    payload: LibraryMoveRequest | None = None,
    sync: LibrarySync = Depends(get_library_sync),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    try:
        pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
            permission="edit",
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    try:
        item = sync.move_to_library(
            job_id,
            status_override=payload.status_override if payload else None,
        )
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized = sync.serialize_item(item)
    return LibraryMoveResponse(item=LibraryItemPayload.model_validate(serialized))


@router.get("/items", response_model=LibrarySearchResponse)
async def list_library_items(
    query: str | None = Query(default=None, alias="q"),
    author: str | None = Query(default=None),
    book: str | None = Query(default=None, alias="book"),
    genre: str | None = Query(default=None),
    language: str | None = Query(default=None),
    status_filter: Literal["finished", "paused"] | None = Query(default=None, alias="status"),
    view: Literal["flat", "by_author", "by_genre", "by_language"] = Query(default="flat"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    sort: Literal["updated_at_desc", "updated_at_asc"] = Query(default="updated_at_desc"),
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    try:
        result = sync.search(
            query=query,
            author=author,
            book_title=book,
            genre=genre,
            language=language,
            status=status_filter,
            view=view,
            page=page,
            limit=limit,
            sort=sort,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    items = [LibraryItemPayload.model_validate(sync.serialize_item(entry)) for entry in result.items]

    return LibrarySearchResponse(
        total=result.total,
        page=result.page,
        limit=result.limit,
        view=result.view,
        items=items,
        groups=result.groups,
    )


@router.post("/remove-media/{job_id}", response_model=LibraryMediaRemovalResponse)
async def remove_library_media(
    job_id: str,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="edit")
    try:
        updated_item, removed = sync.remove_media(job_id)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    location = "library" if updated_item is not None else "queue"
    payload_item = (
        LibraryItemPayload.model_validate(sync.serialize_item(updated_item))
        if updated_item is not None
        else None
    )
    return LibraryMediaRemovalResponse(job_id=job_id, location=location, removed=removed, item=payload_item)


@router.delete("/remove/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_library_entry(
    job_id: str,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="edit")
    try:
        sync.remove_entry(job_id)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/items/{job_id}", response_model=LibraryItemPayload)
async def update_library_metadata(
    job_id: str,
    payload: LibraryMetadataUpdateRequest,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="edit")
    try:
        updated_item = sync.update_metadata(
            job_id,
            title=payload.title,
            author=payload.author,
            genre=payload.genre,
            language=payload.language,
            isbn=payload.isbn,
        )
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized = sync.serialize_item(updated_item)
    return LibraryItemPayload.model_validate(serialized)


@router.get("/items/{job_id}/access", response_model=AccessPolicyPayload)
async def get_library_access(
    job_id: str,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AccessPolicyPayload:
    item = sync.get_item(job_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library item not found")
    _ensure_library_access(item, request_user, permission="view")
    policy = _resolve_library_access(item)
    return AccessPolicyPayload.model_validate(policy.to_dict())


@router.patch("/items/{job_id}/access", response_model=LibraryItemPayload)
async def update_library_access(
    job_id: str,
    payload: AccessPolicyUpdateRequest,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
) -> LibraryItemPayload:
    item = sync.get_item(job_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library item not found")
    _ensure_library_access(item, request_user, permission="edit")
    try:
        updated_item = sync.update_access(
            job_id,
            visibility=payload.visibility,
            grants=[grant.model_dump(by_alias=True) for grant in payload.grants]
            if payload.grants is not None
            else None,
            actor_id=request_user.user_id,
        )
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    serialized = sync.serialize_item(updated_item)
    return LibraryItemPayload.model_validate(serialized)


@router.post("/items/{job_id}/upload-source", response_model=LibraryItemPayload)
async def upload_library_source(
    job_id: str,
    file: UploadFile = File(...),
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="edit")
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded source must include a filename.",
        )

    suffix = Path(file.filename).suffix or ".epub"
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=suffix) as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
            temp_path = Path(handle.name)
    finally:
        await file.close()

    if temp_path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process uploaded source file.",
        )

    try:
        updated_item = sync.reupload_source_from_path(job_id, temp_path)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass

    serialized = sync.serialize_item(updated_item)
    return LibraryItemPayload.model_validate(serialized)


@router.post("/items/{job_id}/isbn", response_model=LibraryItemPayload)
async def apply_isbn_metadata(
    job_id: str,
    payload: LibraryIsbnUpdateRequest,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="edit")
    try:
        updated_item = sync.apply_isbn_metadata(job_id, payload.isbn)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized = sync.serialize_item(updated_item)
    return LibraryItemPayload.model_validate(serialized)


@router.post("/items/{job_id}/refresh", response_model=LibraryItemPayload)
async def refresh_library_metadata(
    job_id: str,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="edit")
    try:
        refreshed_item = sync.refresh_metadata(job_id)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized = sync.serialize_item(refreshed_item)
    return LibraryItemPayload.model_validate(serialized)


@router.get("/isbn/lookup", response_model=LibraryIsbnLookupResponse)
async def lookup_isbn_metadata(
    isbn: str = Query(..., min_length=1),
    sync: LibrarySync = Depends(get_library_sync),
):
    try:
        metadata = sync.lookup_isbn_metadata(isbn)
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LibraryIsbnLookupResponse(metadata=metadata)


@router.post("/reindex", response_model=LibraryReindexResponse)
async def reindex_library(
    service: LibraryService = Depends(get_library_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    if (request_user.user_role or "").strip().lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    indexed = service.rebuild_index()
    return LibraryReindexResponse(indexed=indexed)


@router.get("/media/{job_id}", response_model=PipelineMediaResponse)
async def get_library_media(
    job_id: str,
    summary: bool = Query(False),
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="view")
    start = time.perf_counter()
    try:
        media_map, chunk_records, complete = await run_in_threadpool(
            lambda: sync.get_media(job_id, summary=summary),
        )
    except LibraryNotFoundError as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info(
            "Library media lookup failed job_id=%s summary=%s duration_ms=%.1f",
            job_id,
            summary,
            duration_ms,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info(
            "Library media lookup failed job_id=%s summary=%s duration_ms=%.1f",
            job_id,
            summary,
            duration_ms,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    duration_ms = (time.perf_counter() - start) * 1000
    chunk_count = len(chunk_records)
    media_count = sum(len(entries) for entries in media_map.values())
    if duration_ms >= 250:
        LOGGER.info(
            "Library media lookup job_id=%s summary=%s chunks=%s files=%s duration_ms=%.1f",
            job_id,
            summary,
            chunk_count,
            media_count,
            duration_ms,
        )
    else:
        LOGGER.debug(
            "Library media lookup job_id=%s summary=%s chunks=%s files=%s duration_ms=%.1f",
            job_id,
            summary,
            chunk_count,
            media_count,
            duration_ms,
        )

    serialized_media: Dict[str, list[PipelineMediaFile]] = {}
    for category, entries in media_map.items():
        serialized_media[category] = [PipelineMediaFile.model_validate(entry) for entry in entries]

    serialized_chunks: list[PipelineMediaChunk] = []
    for chunk in chunk_records:
        files = [PipelineMediaFile.model_validate(entry) for entry in chunk.get("files", [])]
        raw_tracks = chunk.get("audio_tracks") or {}
        audio_tracks: Dict[str, Any] = {}
        if isinstance(raw_tracks, Mapping):
            for track_key, track_value in raw_tracks.items():
                if not isinstance(track_key, str):
                    continue
                if isinstance(track_value, Mapping):
                    audio_tracks[track_key] = dict(track_value)
                elif isinstance(track_value, str):
                    trimmed = track_value.strip()
                    if trimmed:
                        audio_tracks[track_key] = {"path": trimmed}
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
            )
        )

    return PipelineMediaResponse(media=serialized_media, chunks=serialized_chunks, complete=complete)


@router.get("/media/{job_id}/file/{relative_path:path}")
async def download_library_media(
    job_id: str,
    relative_path: str,
    sync: LibrarySync = Depends(get_library_sync),
    range_header: str | None = Header(default=None, alias="Range"),
    request_user: RequestUserContext = Depends(get_request_user),
):
    item = sync.get_item(job_id)
    if item is not None:
        _ensure_library_access(item, request_user, permission="view")
    try:
        resolved = sync.resolve_media_file(job_id, relative_path)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _stream_local_file(resolved, range_header)
