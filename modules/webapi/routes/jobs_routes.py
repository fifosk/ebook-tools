"""Routes for pipeline job lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import AsyncIterator, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ...services.book_metadata_service import BookMetadataService
from ... import config_manager as cfg
from ...services.pipeline_service import PipelineService
from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_book_metadata_service,
    get_pipeline_service,
    get_request_user,
    get_runtime_context_provider,
)
from ..jobs import PipelineJob, PipelineJobTransitionError
from ..schemas import (
    PipelineJobActionResponse,
    PipelineJobListResponse,
    PipelineRequestPayload,
    PipelineStatusResponse,
    PipelineSubmissionResponse,
    ProgressEventPayload,
    BookOpenLibraryMetadataLookupRequest,
    BookOpenLibraryMetadataPreviewLookupRequest,
    BookOpenLibraryMetadataPreviewResponse,
    BookOpenLibraryMetadataResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

def _build_action_response(
    job: PipelineJob, *, error: str | None = None
) -> PipelineJobActionResponse:
    return PipelineJobActionResponse(
        job=PipelineStatusResponse.from_job(job),
        error=error,
    )


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
        job_type=job.job_type,
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


@router.get("/{job_id}/metadata/book", response_model=BookOpenLibraryMetadataResponse)
async def get_book_openlibrary_metadata(
    job_id: str,
    metadata_service: BookMetadataService = Depends(get_book_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> BookOpenLibraryMetadataResponse:
    """Return stored (or inferred) Open Library metadata for a book-like job without triggering a lookup."""

    try:
        payload = metadata_service.get_openlibrary_metadata(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return BookOpenLibraryMetadataResponse(**payload)


@router.post(
    "/{job_id}/metadata/book/lookup",
    response_model=BookOpenLibraryMetadataResponse,
)
async def lookup_book_openlibrary_metadata(
    job_id: str,
    lookup: BookOpenLibraryMetadataLookupRequest,
    metadata_service: BookMetadataService = Depends(get_book_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> BookOpenLibraryMetadataResponse:
    """Trigger Open Library metadata enrichment for the job and persist the result."""

    try:
        payload = metadata_service.lookup_openlibrary_metadata(
            job_id,
            force=bool(lookup.force),
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return BookOpenLibraryMetadataResponse(**payload)


@router.post(
    "/metadata/book/lookup",
    response_model=BookOpenLibraryMetadataPreviewResponse,
)
async def lookup_book_openlibrary_metadata_preview(
    lookup: BookOpenLibraryMetadataPreviewLookupRequest,
    metadata_service: BookMetadataService = Depends(get_book_metadata_service),
    request_user: RequestUserContext = Depends(get_request_user),
) -> BookOpenLibraryMetadataPreviewResponse:
    """Lookup Open Library metadata for a filename/title/ISBN (used before submitting jobs)."""

    try:
        payload = metadata_service.lookup_openlibrary_metadata_for_query(
            lookup.query,
            force=bool(lookup.force),
        )
    except Exception as exc:
        logger.warning(
            "Unable to lookup Open Library metadata for query %s",
            lookup.query,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to lookup Open Library metadata: {exc}",
        ) from exc

    return BookOpenLibraryMetadataPreviewResponse(**payload)


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


@router.get("/jobs/{job_id}", response_model=PipelineStatusResponse, include_in_schema=False)
async def get_pipeline_status_legacy(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Legacy alias for /api/pipelines/{job_id}."""

    return await get_pipeline_status(
        job_id=job_id,
        pipeline_service=pipeline_service,
        request_user=request_user,
    )


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


@router.post("/jobs/{job_id}/restart", response_model=PipelineJobActionResponse)
async def restart_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Restart a non-running job with the same settings, overwriting generated outputs."""

    return _handle_job_action(
        job_id,
        pipeline_service.restart_job,
        request_user=request_user,
    )


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


__all__ = ["router"]
