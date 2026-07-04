"""Routes powering the Library feature."""

from __future__ import annotations

import mimetypes
import tempfile
import time
from pathlib import Path
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from .library_access import (
    ensure_library_access as _ensure_library_access,
    resolve_library_access as _resolve_library_access,
)
from .library_telemetry import (
    _log_library_access_policy,
    _log_library_isbn_apply,
    _log_library_media_file_resolve,
    _log_library_media_remove,
    _log_library_metadata_enrich,
    _log_library_metadata_refresh,
    _log_library_metadata_update,
    _log_library_move_entry,
    _log_library_reindex,
    _log_library_remove_entry,
    _log_library_route_result,
    _log_library_source_upload,
)
from .library_media import build_library_media_response
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
    LibraryMetadataEnrichRequest,
    LibraryMetadataEnrichResponse,
    LibraryMetadataRefreshRequest,
    LibraryMetadataRefreshResponse,
    LibraryMetadataUpdateRequest,
    LibraryMoveRequest,
    LibraryMoveResponse,
    LibraryIsbnLookupResponse,
    LibraryIsbnUpdateRequest,
    LibraryReindexResponse,
    LibrarySearchResponse,
    AccessPolicyPayload,
    AccessPolicyUpdateRequest,
    PipelineMediaResponse,
)
from ...library import (
    LibraryConflictError,
    LibraryEntry,
    LibraryError,
    LibraryNotFoundError,
    LibraryService,
    LibrarySync,
)
from ...services.pipeline_service import PipelineService


router = APIRouter(prefix="/api/library", tags=["library"])

# Ensure common subtitle MIME types are recognized when serving from the library.
mimetypes.add_type("text/vtt", ".vtt")
mimetypes.add_type("text/x-srt", ".srt")
mimetypes.add_type("text/plain", ".ass")


def _get_accessible_library_item(
    sync: LibrarySync,
    job_id: str,
    request_user: RequestUserContext,
    *,
    permission: str,
    on_forbidden: Callable[[], None],
) -> LibraryEntry | None:
    item = sync.get_item(job_id)
    if item is None:
        return None
    try:
        _ensure_library_access(item, request_user, permission=permission)
    except HTTPException:
        on_forbidden()
        raise
    return item


@router.post("/move/{job_id}", response_model=LibraryMoveResponse)
async def move_job_to_library(
    job_id: str,
    payload: LibraryMoveRequest | None = None,
    sync: LibrarySync = Depends(get_library_sync),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    status_override = payload.status_override if payload else None
    status_override_present = bool(status_override)
    try:
        pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
            permission="edit",
        )
    except KeyError as exc:
        _log_library_move_entry(
            result="job_not_found",
            started_at=started_at,
            status_override_present=status_override_present,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.") from exc
    except PermissionError as exc:
        _log_library_move_entry(
            result="forbidden",
            started_at=started_at,
            status_override_present=status_override_present,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify job.",
        ) from exc
    except Exception as exc:
        _log_library_move_entry(
            result="error",
            started_at=started_at,
            status_override_present=status_override_present,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to move job to library.",
        ) from exc
    try:
        item = sync.move_to_library(
            job_id,
            status_override=status_override,
        )
        serialized = sync.serialize_item(item)
        item_payload = LibraryItemPayload.model_validate(serialized)
    except LibraryNotFoundError as exc:
        _log_library_move_entry(
            result="not_found",
            started_at=started_at,
            status_override_present=status_override_present,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.") from exc
    except LibraryConflictError as exc:
        _log_library_move_entry(
            result="conflict",
            started_at=started_at,
            status_override_present=status_override_present,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Library item already exists.",
        ) from exc
    except LibraryError as exc:
        _log_library_move_entry(
            result="bad_request",
            started_at=started_at,
            status_override_present=status_override_present,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to move job to library.",
        ) from exc
    except Exception as exc:
        _log_library_move_entry(
            result="error",
            started_at=started_at,
            status_override_present=status_override_present,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to move job to library.",
        ) from exc

    _log_library_move_entry(
        result="success",
        started_at=started_at,
        status_override_present=status_override_present,
    )
    return LibraryMoveResponse(item=item_payload)


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
    started_at = time.perf_counter()
    filter_count = sum(
        1 for value in (author, book, genre, language, status_filter) if value
    )
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
        items = [
            LibraryItemPayload.model_validate(sync.serialize_item(entry))
            for entry in result.items
        ]
        response_payload = LibrarySearchResponse(
            total=result.total,
            page=result.page,
            limit=result.limit,
            view=result.view,
            items=items,
            groups=result.groups,
        )
    except LibraryError as exc:
        _log_library_route_result(
            message="Library item list failed",
            operation="list_items",
            result="bad_request",
            started_at=started_at,
            view=view,
            page=page,
            limit=limit,
            query_present=bool(query),
            filters=filter_count,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to list library items.",
        ) from exc
    except Exception as exc:
        _log_library_route_result(
            message="Library item list failed",
            operation="list_items",
            result="error",
            started_at=started_at,
            view=view,
            page=page,
            limit=limit,
            query_present=bool(query),
            filters=filter_count,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to list library items.",
        ) from exc

    group_count = len(result.groups or [])
    _log_library_route_result(
        message="Library item list",
        operation="list_items",
        result="success",
        started_at=started_at,
        view=result.view,
        page=result.page,
        limit=result.limit,
        query_present=bool(query),
        filters=filter_count,
        total=result.total,
        items=len(items),
        groups=group_count,
    )

    return response_payload


@router.post("/remove-media/{job_id}", response_model=LibraryMediaRemovalResponse)
async def remove_library_media(
    job_id: str,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_media_remove(
                result="forbidden",
                started_at=started_at,
            ),
        )
        updated_item, removed = sync.remove_media(job_id)
        location = "library" if updated_item is not None else "queue"
        payload_item = (
            LibraryItemPayload.model_validate(sync.serialize_item(updated_item))
            if updated_item is not None
            else None
        )
    except LibraryNotFoundError as exc:
        _log_library_media_remove(result="not_found", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library media not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_media_remove(result="bad_request", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to remove library media.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_media_remove(result="error", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to remove library media.",
        ) from exc
    _log_library_media_remove(
        result="success",
        started_at=started_at,
        location=location,
        removed_count=removed,
    )
    return LibraryMediaRemovalResponse(job_id=job_id, location=location, removed=removed, item=payload_item)


@router.delete("/remove/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_library_entry(
    job_id: str,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_remove_entry(
                result="forbidden",
                started_at=started_at,
            ),
        )
        sync.remove_entry(job_id)
    except LibraryNotFoundError as exc:
        _log_library_remove_entry(result="not_found", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_remove_entry(result="bad_request", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to remove library item.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_remove_entry(result="error", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to remove library item.",
        ) from exc
    _log_library_remove_entry(result="success", started_at=started_at)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/items/{job_id}", response_model=LibraryItemPayload)
async def update_library_metadata(
    job_id: str,
    payload: LibraryMetadataUpdateRequest,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    edited_fields = sum(
        1
        for value in (
            payload.title,
            payload.author,
            payload.genre,
            payload.language,
            payload.isbn,
        )
        if value is not None
    )
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_metadata_update(
                result="forbidden",
                started_at=started_at,
                edited_fields=edited_fields,
            ),
        )
        updated_item = sync.update_metadata(
            job_id,
            title=payload.title,
            author=payload.author,
            genre=payload.genre,
            language=payload.language,
            isbn=payload.isbn,
        )
        serialized = sync.serialize_item(updated_item)
        item_payload = LibraryItemPayload.model_validate(serialized)
    except LibraryNotFoundError as exc:
        _log_library_metadata_update(
            result="not_found",
            started_at=started_at,
            edited_fields=edited_fields,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found.",
        ) from exc
    except LibraryConflictError as exc:
        _log_library_metadata_update(
            result="conflict",
            started_at=started_at,
            edited_fields=edited_fields,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Library metadata update conflicts with an existing item.",
        ) from exc
    except LibraryError as exc:
        _log_library_metadata_update(
            result="bad_request",
            started_at=started_at,
            edited_fields=edited_fields,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to update library metadata.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_metadata_update(
            result="error",
            started_at=started_at,
            edited_fields=edited_fields,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to update library metadata.",
        ) from exc

    _log_library_metadata_update(
        result="success",
        started_at=started_at,
        edited_fields=edited_fields,
    )
    return item_payload


@router.get("/items/{job_id}/access", response_model=AccessPolicyPayload)
async def get_library_access(
    job_id: str,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AccessPolicyPayload:
    started_at = time.perf_counter()
    operation = "access_get"
    try:
        item = _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="view",
            on_forbidden=lambda: _log_library_access_policy(
                operation=operation,
                result="forbidden",
                started_at=started_at,
            ),
        )
        if item is None:
            _log_library_access_policy(
                operation=operation,
                result="not_found",
                started_at=started_at,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library item not found.",
            )
        policy = _resolve_library_access(item)
        payload = AccessPolicyPayload.model_validate(policy.to_dict())
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_access_policy(
            operation=operation,
            result="error",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to load library access policy.",
        ) from exc
    _log_library_access_policy(
        operation=operation,
        result="success",
        started_at=started_at,
        visibility_present=True,
        grant_count=len(payload.grants),
    )
    return payload


@router.patch("/items/{job_id}/access", response_model=LibraryItemPayload)
async def update_library_access(
    job_id: str,
    payload: AccessPolicyUpdateRequest,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
) -> LibraryItemPayload:
    started_at = time.perf_counter()
    operation = "access_update"
    visibility_present = payload.visibility is not None
    grant_count = len(payload.grants) if payload.grants is not None else None
    try:
        item = _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_access_policy(
                operation=operation,
                result="forbidden",
                started_at=started_at,
                visibility_present=visibility_present,
                grant_count=grant_count,
            ),
        )
        if item is None:
            _log_library_access_policy(
                operation=operation,
                result="not_found",
                started_at=started_at,
                visibility_present=visibility_present,
                grant_count=grant_count,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library item not found.",
            )
        updated_item = sync.update_access(
            job_id,
            visibility=payload.visibility,
            grants=[grant.model_dump(by_alias=True) for grant in payload.grants]
            if payload.grants is not None
            else None,
            actor_id=request_user.user_id,
        )
        serialized = sync.serialize_item(updated_item)
        item_payload = LibraryItemPayload.model_validate(serialized)
    except HTTPException:
        raise
    except LibraryNotFoundError as exc:
        _log_library_access_policy(
            operation=operation,
            result="not_found",
            started_at=started_at,
            visibility_present=visibility_present,
            grant_count=grant_count,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_access_policy(
            operation=operation,
            result="bad_request",
            started_at=started_at,
            visibility_present=visibility_present,
            grant_count=grant_count,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to update library access policy.",
        ) from exc
    except Exception as exc:
        _log_library_access_policy(
            operation=operation,
            result="error",
            started_at=started_at,
            visibility_present=visibility_present,
            grant_count=grant_count,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to update library access policy.",
        ) from exc
    _log_library_access_policy(
        operation=operation,
        result="success",
        started_at=started_at,
        visibility_present=visibility_present,
        grant_count=grant_count,
    )
    return item_payload


@router.post("/items/{job_id}/upload-source", response_model=LibraryItemPayload)
async def upload_library_source(
    job_id: str,
    file: UploadFile = File(...),
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    temp_path: Optional[Path] = None
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_source_upload(
                result="forbidden",
                started_at=started_at,
                has_filename=bool(file.filename),
            ),
        )
        if not file.filename:
            _log_library_source_upload(
                result="bad_request",
                started_at=started_at,
                has_filename=False,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded source must include a filename.",
            )

        suffix = Path(file.filename).suffix or ".epub"
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=suffix) as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
            temp_path = Path(handle.name)

        if temp_path is None:
            _log_library_source_upload(
                result="bad_request",
                started_at=started_at,
                has_filename=bool(file.filename),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to process uploaded source file.",
            )

        updated_item = sync.reupload_source_from_path(job_id, temp_path)
        serialized = sync.serialize_item(updated_item)
        item_payload = LibraryItemPayload.model_validate(serialized)
    except LibraryNotFoundError as exc:
        _log_library_source_upload(
            result="not_found",
            started_at=started_at,
            has_filename=bool(file.filename),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_source_upload(
            result="bad_request",
            started_at=started_at,
            has_filename=bool(file.filename),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to replace library source file.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_source_upload(
            result="error",
            started_at=started_at,
            has_filename=bool(file.filename),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to replace library source file.",
        ) from exc
    finally:
        await file.close()
        try:
            if temp_path is not None:
                temp_path.unlink()
        except OSError:
            pass

    _log_library_source_upload(
        result="success",
        started_at=started_at,
        has_filename=bool(file.filename),
    )
    return item_payload


@router.post("/items/{job_id}/isbn", response_model=LibraryItemPayload)
async def apply_isbn_metadata(
    job_id: str,
    payload: LibraryIsbnUpdateRequest,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    has_isbn = bool((payload.isbn or "").strip())
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_isbn_apply(
                result="forbidden",
                started_at=started_at,
                has_isbn=has_isbn,
            ),
        )
        updated_item = sync.apply_isbn_metadata(job_id, payload.isbn)
        serialized = sync.serialize_item(updated_item)
        item_payload = LibraryItemPayload.model_validate(serialized)
    except LibraryNotFoundError as exc:
        _log_library_isbn_apply(
            result="not_found",
            started_at=started_at,
            has_isbn=has_isbn,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_isbn_apply(
            result="bad_request",
            started_at=started_at,
            has_isbn=has_isbn,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to apply ISBN metadata.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_isbn_apply(
            result="error",
            started_at=started_at,
            has_isbn=has_isbn,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to apply ISBN metadata.",
        ) from exc

    _log_library_isbn_apply(
        result="success",
        started_at=started_at,
        has_isbn=has_isbn,
    )
    return item_payload


@router.post("/items/{job_id}/refresh", response_model=LibraryMetadataRefreshResponse)
async def refresh_library_metadata(
    job_id: str,
    payload: LibraryMetadataRefreshRequest | None = None,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Refresh metadata for a library item from source file and external sources.

    This re-extracts metadata from the EPUB and optionally enriches from
    external sources (OpenLibrary, Google Books, TMDB, etc.).
    """
    started_at = time.perf_counter()
    enrich_requested = bool(payload and payload.enrich_from_external)
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_metadata_refresh(
                result="forbidden",
                started_at=started_at,
                enrich_requested=enrich_requested,
            ),
        )
        refreshed_item = sync.refresh_metadata(job_id)
        if enrich_requested:
            refreshed_item = sync.enrich_metadata(job_id, force=True)
        serialized = sync.serialize_item(refreshed_item)
        item_payload = LibraryItemPayload.model_validate(serialized)
    except LibraryNotFoundError as exc:
        _log_library_metadata_refresh(
            result="not_found",
            started_at=started_at,
            enrich_requested=enrich_requested,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_metadata_refresh(
            result="bad_request",
            started_at=started_at,
            enrich_requested=enrich_requested,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to refresh library metadata.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_metadata_refresh(
            result="error",
            started_at=started_at,
            enrich_requested=enrich_requested,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to refresh library metadata.",
        ) from exc

    _log_library_metadata_refresh(
        result="success",
        started_at=started_at,
        enrich_requested=enrich_requested,
    )
    return LibraryMetadataRefreshResponse(item=item_payload)


@router.post("/items/{job_id}/enrich", response_model=LibraryMetadataEnrichResponse)
async def enrich_library_metadata(
    job_id: str,
    payload: LibraryMetadataEnrichRequest | None = None,
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Enrich metadata for a library item from external sources.

    This performs a lookup against external metadata sources (OpenLibrary,
    Google Books, TMDB, etc.) using the unified metadata pipeline and
    fills in missing metadata fields. It does NOT re-extract from the EPUB.

    Use this endpoint when you have existing metadata (e.g., title/author)
    and want to fetch additional information like cover images, summaries,
    genres, ISBNs, etc. from external sources.
    """
    started_at = time.perf_counter()
    force = payload.force if payload else False

    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="edit",
            on_forbidden=lambda: _log_library_metadata_enrich(
                result="forbidden",
                started_at=started_at,
                force=force,
            ),
        )
        enriched_item = sync.enrich_metadata(job_id, force=force)
        serialized = sync.serialize_item(enriched_item)
        item_payload = LibraryItemPayload.model_validate(serialized)

        # Extract enrichment info from metadata
        media_metadata = serialized.get("metadata", {}).get("media_metadata", {})
        enriched = bool(media_metadata.get("_enrichment_source"))
        confidence = media_metadata.get("_enrichment_confidence")
        source = media_metadata.get("_enrichment_source")
    except LibraryNotFoundError as exc:
        _log_library_metadata_enrich(
            result="not_found",
            started_at=started_at,
            force=force,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library item not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_metadata_enrich(
            result="bad_request",
            started_at=started_at,
            force=force,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to enrich library metadata.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_metadata_enrich(
            result="error",
            started_at=started_at,
            force=force,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to enrich library metadata.",
        ) from exc

    _log_library_metadata_enrich(
        result="success",
        started_at=started_at,
        force=force,
    )
    return LibraryMetadataEnrichResponse(
        item=item_payload,
        enriched=enriched,
        confidence=confidence,
        source=source,
    )


@router.get("/isbn/lookup", response_model=LibraryIsbnLookupResponse)
async def lookup_isbn_metadata(
    isbn: str = Query(..., min_length=1),
    sync: LibrarySync = Depends(get_library_sync),
):
    started_at = time.perf_counter()
    try:
        metadata = sync.lookup_isbn_metadata(isbn)
    except LibraryError as exc:
        _log_library_route_result(
            message="Library ISBN lookup failed response detail suppressed",
            operation="isbn_lookup",
            result="bad_request",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to lookup ISBN metadata.",
        ) from exc
    except Exception as exc:
        _log_library_route_result(
            message="Library ISBN lookup failed unexpectedly response detail suppressed",
            operation="isbn_lookup",
            result="error",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to lookup ISBN metadata.",
        ) from exc
    _log_library_route_result(
        message="Library ISBN lookup",
        operation="isbn_lookup",
        result="success",
        started_at=started_at,
    )
    return LibraryIsbnLookupResponse(metadata=metadata)


@router.post("/reindex", response_model=LibraryReindexResponse)
async def reindex_library(
    service: LibraryService = Depends(get_library_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    if (request_user.user_role or "").strip().lower() != "admin":
        _log_library_reindex(result="forbidden", started_at=started_at)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    try:
        indexed = service.rebuild_index()
        response_payload = LibraryReindexResponse(indexed=indexed)
    except LibraryError as exc:
        _log_library_reindex(result="bad_request", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to rebuild library index.",
        ) from exc
    except Exception as exc:
        _log_library_reindex(result="error", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to rebuild library index.",
        ) from exc
    _log_library_reindex(
        result="success",
        started_at=started_at,
        indexed_count=indexed,
    )
    return response_payload


@router.get("/media/{job_id}", response_model=PipelineMediaResponse)
async def get_library_media(
    job_id: str,
    summary: bool = Query(False),
    sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    start = time.perf_counter()
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="view",
            on_forbidden=lambda: _log_library_route_result(
                message="Library media lookup failed",
                operation="media",
                result="forbidden",
                started_at=start,
                include_operation=True,
                summary=summary,
            ),
        )
        media_map, chunk_records, complete = await run_in_threadpool(
            lambda: sync.get_media(job_id, summary=summary),
        )
        response_payload = build_library_media_response(
            job_id=job_id,
            media_map=media_map,
            chunk_records=chunk_records,
            complete=complete,
        )
    except LibraryNotFoundError as exc:
        _log_library_route_result(
            message="Library media lookup failed",
            operation="media",
            result="not_found",
            started_at=start,
            include_operation=True,
            summary=summary,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library media not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_route_result(
            message="Library media lookup failed",
            operation="media",
            result="bad_request",
            started_at=start,
            include_operation=True,
            summary=summary,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to load library media.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_route_result(
            message="Library media lookup failed",
            operation="media",
            result="error",
            started_at=start,
            include_operation=True,
            summary=summary,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to load library media.",
        ) from exc

    chunk_count = len(chunk_records)
    media_count = sum(len(entries) for entries in media_map.values())
    category_count = len(media_map)
    _log_library_route_result(
        message="Library media lookup",
        operation="media",
        result="success",
        started_at=start,
        include_operation=True,
        summary=summary,
        categories=category_count,
        chunks=chunk_count,
        files=media_count,
        complete=complete,
    )

    return response_payload


@router.get("/media/{job_id}/file/{file_path:path}")
async def download_library_media(
    job_id: str,
    file_path: str,
    sync: LibrarySync = Depends(get_library_sync),
    range_header: str | None = Header(default=None, alias="Range"),
    request_user: RequestUserContext = Depends(get_request_user),
):
    started_at = time.perf_counter()
    has_range = bool(range_header)
    try:
        _get_accessible_library_item(
            sync,
            job_id,
            request_user,
            permission="view",
            on_forbidden=lambda: _log_library_media_file_resolve(
                result="forbidden",
                started_at=started_at,
                has_range=has_range,
            ),
        )
        resolved = sync.resolve_media_file(job_id, file_path)
        response = _stream_local_file(resolved, range_header)
    except LibraryNotFoundError as exc:
        _log_library_media_file_resolve(
            result="not_found",
            started_at=started_at,
            has_range=has_range,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library media file not found.",
        ) from exc
    except LibraryError as exc:
        _log_library_media_file_resolve(
            result="bad_request",
            started_at=started_at,
            has_range=has_range,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to resolve library media file.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        _log_library_media_file_resolve(
            result="error",
            started_at=started_at,
            has_range=has_range,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to resolve library media file.",
        ) from exc
    _log_library_media_file_resolve(
        result="success",
        started_at=started_at,
        has_range=has_range,
    )
    return response
