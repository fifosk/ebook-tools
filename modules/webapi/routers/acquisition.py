"""Discovery/acquisition provider routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules import logging_manager as log_mgr
from modules.permissions import normalize_role
from modules.services.acquisition import (
    AcquisitionArtifact,
    AcquisitionCandidate,
    AcquisitionJobStatus,
    AcquisitionProviderDiscoveryError,
    DownloadStationError,
    acquire_acquisition_candidate,
    discover_acquisition_candidates,
    enqueue_download_station_task,
    list_acquisition_providers,
    poll_download_station_task,
    prepare_acquisition_artifact,
)

from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_request_user,
    get_runtime_context_provider,
)
from ..route_telemetry import record_started_route_duration
from ..schemas.acquisition import (
    AcquisitionAcquireRequest,
    AcquisitionArtifactResponse,
    AcquisitionCandidatePayload,
    AcquisitionDiscoveryResponse,
    AcquisitionJobCreateRequest,
    AcquisitionJobStatusResponse,
    AcquisitionPreparedArtifactResponse,
    AcquisitionProviderListResponse,
    AcquisitionProviderPayload,
    AcquisitionSubtitleHintPayload,
)


router = APIRouter(prefix="/api/acquisition", tags=["acquisition"])
LOGGER = log_mgr.get_logger().getChild("webapi.acquisition")
_ALLOWED_DISCOVERY_ROLES = {"admin", "editor"}


def _log_provider_route(
    result: str,
    started_at: float,
    *,
    operation: str = "providers",
    provider_count: int = 0,
) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1000
    record_started_route_duration(
        "ACQUISITION_ROUTE_DURATION",
        operation,
        result,
        started_at,
    )
    log_method = LOGGER.info if result != "success" or duration_ms >= 250 else LOGGER.debug
    log_method(
        "Acquisition %s route result=%s providers=%d duration_ms=%.1f",
        operation,
        result,
        provider_count,
        duration_ms,
    )


def _ensure_discovery_user(request_user: RequestUserContext) -> None:
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_DISCOVERY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _candidate_payload(candidate: AcquisitionCandidate) -> AcquisitionCandidatePayload:
    return AcquisitionCandidatePayload(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        media_kind=candidate.media_kind,
        title=candidate.title,
        rights=candidate.rights,
        capabilities=list(candidate.capabilities),
        candidate_token=candidate.candidate_token,
        subtitle=candidate.subtitle,
        contributors=list(candidate.contributors),
        language=candidate.language,
        year=candidate.year,
        published_at=candidate.published_at,
        source_url=candidate.source_url,
        thumbnail_url=candidate.thumbnail_url,
        cover_url=candidate.cover_url,
        local_path=candidate.local_path,
        size_bytes=candidate.size_bytes,
        modified_at=candidate.modified_at,
        duration_seconds=candidate.duration_seconds,
        subtitles=[
            AcquisitionSubtitleHintPayload(
                path=subtitle.path,
                filename=subtitle.filename,
                language=subtitle.language,
                format=subtitle.format,
            )
            for subtitle in candidate.subtitles
        ],
        metadata=dict(candidate.metadata),
        requires_confirmation=candidate.requires_confirmation,
        policy_notes=list(candidate.policy_notes),
    )


def _artifact_payload(artifact: AcquisitionArtifact) -> AcquisitionArtifactResponse:
    return AcquisitionArtifactResponse(
        provider=artifact.provider,
        media_kind=artifact.media_kind,
        status=artifact.status,
        artifact_id=artifact.artifact_id,
        artifact_path=artifact.artifact_path,
        local_path=artifact.local_path,
        filename=artifact.filename,
        size_bytes=artifact.size_bytes,
        modified_at=artifact.modified_at,
        next_actions=list(artifact.next_actions),
        metadata=dict(artifact.metadata),
    )


def _prepared_artifact_payload(artifact) -> AcquisitionPreparedArtifactResponse:
    return AcquisitionPreparedArtifactResponse(
        provider=artifact.provider,
        media_kind=artifact.media_kind,
        source_kind=artifact.source_kind,
        local_path=artifact.local_path,
        input_file=artifact.input_file,
        video_path=artifact.video_path,
        subtitle_path=artifact.subtitle_path,
        subtitles=[
            AcquisitionSubtitleHintPayload(
                path=str(subtitle.get("path") or ""),
                filename=str(subtitle.get("filename") or ""),
                language=subtitle.get("language") if isinstance(subtitle.get("language"), str) else None,
                format=subtitle.get("format") if isinstance(subtitle.get("format"), str) else None,
            )
            for subtitle in artifact.subtitles
            if subtitle.get("path") and subtitle.get("filename")
        ],
        next_actions=list(artifact.next_actions),
        metadata=dict(artifact.metadata),
    )


def _job_payload(job: AcquisitionJobStatus) -> AcquisitionJobStatusResponse:
    return AcquisitionJobStatusResponse(
        provider=job.provider,
        task_id=job.task_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        external_task_id=job.external_task_id,
        raw_status=job.raw_status,
        started_at=job.started_at,
        updated_at=job.updated_at,
        completed_files=list(job.completed_files),
        next_actions=list(job.next_actions),
        metadata=dict(job.metadata),
    )


@router.get(
    "/providers",
    response_model=AcquisitionProviderListResponse,
    status_code=status.HTTP_200_OK,
)
def list_providers(
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
) -> AcquisitionProviderListResponse:
    """Return configured/planned source discovery providers without secrets."""

    started_at = time.perf_counter()
    config = runtime_provider.resolve_config()
    registry = list_acquisition_providers(config=config)
    _log_provider_route("success", started_at, provider_count=len(registry.providers))
    return AcquisitionProviderListResponse(
        providers=[
            AcquisitionProviderPayload(**provider.as_dict())
            for provider in registry.providers
        ],
        policy_notes=list(registry.policy_notes),
        paths=dict(registry.paths),
    )


@router.get(
    "/discover",
    response_model=AcquisitionDiscoveryResponse,
    status_code=status.HTTP_200_OK,
)
def discover(
    media_kind: str = Query(..., pattern="^(book|video)$"),
    q: str = Query(default=""),
    provider: str | None = Query(default=None),
    language: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionDiscoveryResponse:
    """Return normalized source candidates for Web and Apple Create."""

    _ensure_discovery_user(request_user)
    started_at = time.perf_counter()
    try:
        result = discover_acquisition_candidates(
            media_kind=media_kind,
            query=q,
            provider=provider,
            language=language,
            limit=limit,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="discover")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AcquisitionProviderDiscoveryError as exc:
        _log_provider_route(exc.reason or "provider_error", started_at, operation="discover")
        LOGGER.info(
            "Acquisition discovery provider failed provider=%s reason=%s",
            exc.provider,
            exc.reason,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="discover")
        LOGGER.warning("Acquisition discovery failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query acquisition provider.",
        ) from exc

    _log_provider_route(
        "success",
        started_at,
        operation="discover",
        provider_count=len(result.providers_queried),
    )
    return AcquisitionDiscoveryResponse(
        candidates=[_candidate_payload(candidate) for candidate in result.candidates],
        policy_notes=list(result.policy_notes),
        providers_queried=list(result.providers_queried),
    )


@router.post(
    "/acquire",
    response_model=AcquisitionArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def acquire(
    payload: AcquisitionAcquireRequest,
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionArtifactResponse:
    """Acquire a reviewed source candidate into an existing Create source root."""

    _ensure_discovery_user(request_user)
    started_at = time.perf_counter()
    try:
        artifact = acquire_acquisition_candidate(
            candidate_token=payload.candidate_token,
            confirmed=payload.confirmed,
            filename=payload.filename,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="acquire")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="acquire")
        LOGGER.warning("Acquisition acquire failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to acquire candidate.",
        ) from exc

    _log_provider_route("success", started_at, operation="acquire", provider_count=1)
    return _artifact_payload(artifact)


@router.post(
    "/artifacts/{artifact_id}/prepare",
    response_model=AcquisitionPreparedArtifactResponse,
    status_code=status.HTTP_200_OK,
)
def prepare_artifact(
    artifact_id: str,
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionPreparedArtifactResponse:
    """Resolve a local/acquired artifact into fields existing Create forms use."""

    _ensure_discovery_user(request_user)
    started_at = time.perf_counter()
    try:
        artifact = prepare_acquisition_artifact(
            artifact_id=artifact_id,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="artifact_prepare")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="artifact_prepare")
        LOGGER.warning("Acquisition artifact prepare failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to prepare acquisition artifact.",
        ) from exc

    _log_provider_route("success", started_at, operation="artifact_prepare", provider_count=1)
    return _prepared_artifact_payload(artifact)


@router.post(
    "/jobs",
    response_model=AcquisitionJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(
    payload: AcquisitionJobCreateRequest,
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionJobStatusResponse:
    """Submit a reviewed async downloader handoff job."""

    _ensure_discovery_user(request_user)
    started_at = time.perf_counter()
    if payload.provider != "download_station":
        _log_provider_route("bad_request", started_at, operation="job_create")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"provider {payload.provider} does not support async acquisition jobs",
        )
    try:
        job = enqueue_download_station_task(
            source_uri=payload.source_uri,
            confirmed=payload.confirmed,
            destination=payload.destination,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="job_create")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DownloadStationError as exc:
        _log_provider_route(exc.reason or "provider_error", started_at, operation="job_create")
        LOGGER.info("Download Station handoff failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_create")
        LOGGER.warning("Acquisition job create failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to submit acquisition job.",
        ) from exc

    _log_provider_route("success", started_at, operation="job_create", provider_count=1)
    return _job_payload(job)


@router.get(
    "/jobs/{task_id}",
    response_model=AcquisitionJobStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_job(
    task_id: str,
    provider: str = "download_station",
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionJobStatusResponse:
    """Poll an async acquisition/downloader job."""

    _ensure_discovery_user(request_user)
    started_at = time.perf_counter()
    if provider != "download_station":
        _log_provider_route("bad_request", started_at, operation="job_poll")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"provider {provider} does not support async acquisition jobs",
        )
    try:
        job = poll_download_station_task(
            task_id=task_id,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="job_poll")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DownloadStationError as exc:
        _log_provider_route(exc.reason or "provider_error", started_at, operation="job_poll")
        LOGGER.info("Download Station poll failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_poll")
        LOGGER.warning("Acquisition job poll failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to poll acquisition job.",
        ) from exc

    _log_provider_route("success", started_at, operation="job_poll", provider_count=1)
    return _job_payload(job)
