"""Routes powering the Library feature."""

from __future__ import annotations

import mimetypes
from typing import Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from ..dependencies import get_library_service
from ..schemas import (
    LibraryItemPayload,
    LibraryMediaRemovalResponse,
    LibraryMetadataUpdateRequest,
    LibraryMoveRequest,
    LibraryMoveResponse,
    LibraryReindexResponse,
    LibrarySearchResponse,
    PipelineMediaChunk,
    PipelineMediaFile,
    PipelineMediaResponse,
)
from ...library.library_service import (
    LibraryConflictError,
    LibraryError,
    LibraryNotFoundError,
    LibraryService,
)


router = APIRouter(prefix="/api/library", tags=["library"])


@router.post("/move/{job_id}", response_model=LibraryMoveResponse)
async def move_job_to_library(
    job_id: str,
    payload: LibraryMoveRequest | None = None,
    service: LibraryService = Depends(get_library_service),
):
    try:
        item = service.move_to_library(
            job_id,
            status_override=payload.status_override if payload else None,
        )
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized = service.serialize_item(item)
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
    service: LibraryService = Depends(get_library_service),
):
    try:
        result = service.search(
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
        )
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    items = [LibraryItemPayload.model_validate(service.serialize_item(entry)) for entry in result.items]

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
    service: LibraryService = Depends(get_library_service),
):
    try:
        updated_item, removed = service.remove_media(job_id)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    location = "library" if updated_item is not None else "queue"
    payload_item = (
        LibraryItemPayload.model_validate(service.serialize_item(updated_item))
        if updated_item is not None
        else None
    )
    return LibraryMediaRemovalResponse(job_id=job_id, location=location, removed=removed, item=payload_item)


@router.delete("/remove/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_library_entry(
    job_id: str,
    service: LibraryService = Depends(get_library_service),
):
    try:
        service.remove_entry(job_id)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/items/{job_id}", response_model=LibraryItemPayload)
async def update_library_metadata(
    job_id: str,
    payload: LibraryMetadataUpdateRequest,
    service: LibraryService = Depends(get_library_service),
):
    try:
        updated_item = service.update_metadata(
            job_id,
            title=payload.title,
            author=payload.author,
            genre=payload.genre,
            language=payload.language,
        )
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized = service.serialize_item(updated_item)
    return LibraryItemPayload.model_validate(serialized)


@router.post("/items/{job_id}/refresh", response_model=LibraryItemPayload)
async def refresh_library_metadata(
    job_id: str,
    service: LibraryService = Depends(get_library_service),
):
    try:
        refreshed_item = service.refresh_metadata(job_id)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized = service.serialize_item(refreshed_item)
    return LibraryItemPayload.model_validate(serialized)


@router.post("/reindex", response_model=LibraryReindexResponse)
async def reindex_library(service: LibraryService = Depends(get_library_service)):
    indexed = service.reindex_from_fs()
    return LibraryReindexResponse(indexed=indexed)


@router.get("/media/{job_id}", response_model=PipelineMediaResponse)
async def get_library_media(
    job_id: str,
    service: LibraryService = Depends(get_library_service),
):
    try:
        media_map, chunk_records, complete = service.get_media(job_id)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    serialized_media: Dict[str, list[PipelineMediaFile]] = {}
    for category, entries in media_map.items():
        serialized_media[category] = [PipelineMediaFile.model_validate(entry) for entry in entries]

    serialized_chunks: list[PipelineMediaChunk] = []
    for chunk in chunk_records:
        files = [PipelineMediaFile.model_validate(entry) for entry in chunk.get("files", [])]
        serialized_chunks.append(
            PipelineMediaChunk(
                chunk_id=chunk.get("chunk_id"),
                range_fragment=chunk.get("range_fragment"),
                start_sentence=chunk.get("start_sentence"),
                end_sentence=chunk.get("end_sentence"),
                files=files,
            )
        )

    return PipelineMediaResponse(media=serialized_media, chunks=serialized_chunks, complete=complete)


@router.get("/media/{job_id}/file/{relative_path:path}")
async def download_library_media(
    job_id: str,
    relative_path: str,
    service: LibraryService = Depends(get_library_service),
):
    try:
        resolved = service.resolve_media_file(job_id, relative_path)
    except LibraryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LibraryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    media_type, _ = mimetypes.guess_type(resolved.name)
    return FileResponse(
        resolved,
        media_type=media_type or "application/octet-stream",
        filename=resolved.name,
    )
