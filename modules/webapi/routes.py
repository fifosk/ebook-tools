"""API routes for pipeline orchestration."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import AsyncIterator, Callable, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from .dependencies import (
    RuntimeContextProvider,
    get_pipeline_service,
    get_runtime_context_provider,
)
from .jobs import PipelineJob, PipelineJobTransitionError
from .. import config_manager as cfg
from ..services.pipeline_service import PipelineService
from .schemas import (
    PipelineJobActionResponse,
    PipelineJobListResponse,
    PipelineFileBrowserResponse,
    PipelineFileEntry,
    PipelineDefaultsResponse,
    PipelineRequestPayload,
    PipelineStatusResponse,
    PipelineSubmissionResponse,
    ProgressEventPayload,
)

router = APIRouter()


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
                path=str(path),
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
                path=str(path),
                type=entry_type,
            )
        )
    return entries


def _build_action_response(
    job: PipelineJob, *, error: str | None = None
) -> PipelineJobActionResponse:
    return PipelineJobActionResponse(
        job=PipelineStatusResponse.from_job(job),
        error=error,
    )


@router.get("/jobs", response_model=PipelineJobListResponse)
async def list_jobs(
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Return all persisted jobs ordered by creation time."""

    jobs = pipeline_service.list_jobs().values()
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

    return PipelineFileBrowserResponse(ebooks=ebooks, outputs=outputs)


@router.get("/defaults", response_model=PipelineDefaultsResponse)
async def get_pipeline_defaults(
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Return the resolved baseline configuration for client defaults."""

    resolved = context_provider.resolve_config()
    stripped = cfg.strip_derived_config(resolved)
    return PipelineDefaultsResponse(config=stripped)


@router.post("/", response_model=PipelineSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_pipeline(
    payload: PipelineRequestPayload,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
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
    job = pipeline_service.enqueue(request)
    return PipelineSubmissionResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
    )


@router.post("/{job_id}/metadata/refresh", response_model=PipelineStatusResponse)
async def refresh_pipeline_metadata(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Trigger metadata inference again for ``job_id`` and return the updated status."""

    try:
        job = pipeline_service.refresh_metadata(job_id)
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return PipelineStatusResponse.from_job(job)


@router.get("/{job_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Return the latest status for the requested job."""

    try:
        job = pipeline_service.get_job(job_id)
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc

    return PipelineStatusResponse.from_job(job)


def _handle_job_action(
    job_id: str,
    action: Callable[[str], PipelineJob],
) -> PipelineJobActionResponse:
    try:
        job = action(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except PipelineJobTransitionError as exc:
        return _build_action_response(exc.job, error=str(exc))
    return _build_action_response(job)


@router.post("/jobs/{job_id}/pause", response_model=PipelineJobActionResponse)
async def pause_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Pause the specified job if possible."""

    return _handle_job_action(job_id, pipeline_service.pause_job)


@router.post("/jobs/{job_id}/resume", response_model=PipelineJobActionResponse)
async def resume_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Resume a paused job."""

    return _handle_job_action(job_id, pipeline_service.resume_job)


@router.post("/jobs/{job_id}/cancel", response_model=PipelineJobActionResponse)
async def cancel_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Cancel a running or pending job."""

    return _handle_job_action(job_id, pipeline_service.cancel_job)


@router.post("/jobs/{job_id}/delete", response_model=PipelineJobActionResponse)
async def delete_job(
    job_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Delete persisted metadata for a job."""

    return _handle_job_action(job_id, pipeline_service.delete_job)


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
):
    """Stream progress events for ``job_id`` as Server-Sent Events."""

    try:
        job = pipeline_service.get_job(job_id)
    except KeyError as exc:  # pragma: no cover - FastAPI handles error path
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc

    generator = _event_stream(job)
    return StreamingResponse(generator, media_type="text/event-stream")
