"""Discovery/acquisition provider routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules.services.acquisition import (
    AcquisitionProviderDiscoveryError,
    DownloadStationError,
    acquire_acquisition_candidate,
    discover_acquisition_candidates,
    enqueue_download_station_task,
    list_acquisition_providers,
    poll_download_station_task,
    prepare_acquisition_artifact,
    resolve_download_station_candidate_source_uri,
)
from modules.services.acquisition.discovery_normalization import (
    normalize_provider as _normalize_optional_provider_id,
    normalize_source_id_filters as _normalize_source_id_filters,
)

from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_request_user,
    get_runtime_context_provider,
)
from ..schemas.acquisition import (
    AcquisitionAcquireRequest,
    AcquisitionArtifactResponse,
    AcquisitionDiscoveryResponse,
    AcquisitionJobCreateRequest,
    AcquisitionJobStatusResponse,
    AcquisitionPreparedArtifactResponse,
    AcquisitionProviderListResponse,
)
from .acquisition_payloads import (
    artifact_payload as _artifact_payload,
    job_payload as _job_payload,
    prepared_artifact_payload as _prepared_artifact_payload,
    public_metadata as _public_metadata,
)
from .acquisition_route_support import (
    ACQUISITION_ACQUIRE_UNAVAILABLE_MESSAGE,
    ACQUISITION_ARTIFACT_PREPARE_UNAVAILABLE_MESSAGE,
    ACQUISITION_DISCOVERY_UNAVAILABLE_MESSAGE,
    ACQUISITION_JOB_CREATE_UNAVAILABLE_MESSAGE,
    ACQUISITION_JOB_POLL_UNAVAILABLE_MESSAGE,
    ACQUISITION_PROVIDERS_UNAVAILABLE_MESSAGE,
    LOGGER,
    ensure_discovery_user as _ensure_discovery_user,
    discovery_response as _discovery_response,
    log_provider_route as _log_provider_route,
    log_unexpected_route_error as _log_unexpected_route_error,
    normalize_async_job_provider_id as _normalize_async_job_provider_id,
    normalize_optional_text as _normalize_optional_text,
    normalize_route_id as _normalize_route_id,
    provider_list_response as _provider_list_response,
    raise_bad_acquisition_route_id as _raise_bad_acquisition_route_id,
)


router = APIRouter(prefix="/api/acquisition", tags=["acquisition"])


@router.get(
    "/providers",
    response_model=AcquisitionProviderListResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
def list_providers(
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
) -> AcquisitionProviderListResponse:
    """Return configured/planned source discovery providers without secrets."""

    started_at = time.perf_counter()
    try:
        config = runtime_provider.resolve_config()
        registry = list_acquisition_providers(config=config)
        response_payload = _provider_list_response(registry)
    except Exception as exc:
        _log_provider_route("error", started_at, logger=LOGGER)
        _log_unexpected_route_error("providers", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ACQUISITION_PROVIDERS_UNAVAILABLE_MESSAGE,
        ) from exc
    _log_provider_route(
        "success",
        started_at,
        provider_count=len(registry.providers),
        logger=LOGGER,
    )
    return response_payload


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
    source_id: list[str] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    runtime_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
) -> AcquisitionDiscoveryResponse:
    """Return normalized source candidates for Web and Apple Create."""

    started_at = time.perf_counter()
    _ensure_discovery_user(
        request_user,
        operation="discover",
        started_at=started_at,
        logger=LOGGER,
    )
    source_ids = _normalize_source_id_filters(source_id)
    provider_id = _normalize_optional_provider_id(provider)
    try:
        result = discover_acquisition_candidates(
            media_kind=media_kind,
            query=q,
            provider=provider_id,
            language=language,
            limit=limit,
            source_ids=source_ids,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="discover", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AcquisitionProviderDiscoveryError as exc:
        _log_provider_route(
            exc.reason or "provider_error",
            started_at,
            operation="discover",
            logger=LOGGER,
        )
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
        _log_provider_route("error", started_at, operation="discover", logger=LOGGER)
        _log_unexpected_route_error("discover", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_DISCOVERY_UNAVAILABLE_MESSAGE,
        ) from exc

    try:
        response_payload = _discovery_response(result)
    except Exception as exc:
        _log_provider_route("error", started_at, operation="discover", logger=LOGGER)
        _log_unexpected_route_error("discover", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_DISCOVERY_UNAVAILABLE_MESSAGE,
        ) from exc
    _log_provider_route(
        "success",
        started_at,
        operation="discover",
        provider_count=len(result.providers_queried),
        logger=LOGGER,
    )
    return response_payload


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

    started_at = time.perf_counter()
    _ensure_discovery_user(
        request_user,
        operation="acquire",
        started_at=started_at,
        logger=LOGGER,
    )
    candidate_token = _normalize_route_id(payload.candidate_token)
    if not candidate_token:
        _raise_bad_acquisition_route_id(
            operation="acquire",
            started_at=started_at,
            detail="Missing acquisition candidate token",
            logger=LOGGER,
        )
    try:
        artifact = acquire_acquisition_candidate(
            candidate_token=candidate_token,
            confirmed=payload.confirmed,
            filename=_normalize_optional_text(payload.filename),
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="acquire", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="acquire", logger=LOGGER)
        _log_unexpected_route_error("acquire", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_ACQUIRE_UNAVAILABLE_MESSAGE,
        ) from exc

    try:
        response_payload = _artifact_payload(artifact)
    except Exception as exc:
        _log_provider_route("error", started_at, operation="acquire", logger=LOGGER)
        _log_unexpected_route_error("acquire", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_ACQUIRE_UNAVAILABLE_MESSAGE,
        ) from exc

    _log_provider_route("success", started_at, operation="acquire", provider_count=1, logger=LOGGER)
    return response_payload


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

    started_at = time.perf_counter()
    _ensure_discovery_user(
        request_user,
        operation="artifact_prepare",
        started_at=started_at,
        logger=LOGGER,
    )
    normalized_artifact_id = _normalize_route_id(artifact_id)
    if not normalized_artifact_id:
        _raise_bad_acquisition_route_id(
            operation="artifact_prepare",
            started_at=started_at,
            detail="Missing acquisition artifact id",
            logger=LOGGER,
        )
    try:
        artifact = prepare_acquisition_artifact(
            artifact_id=normalized_artifact_id,
            config=runtime_provider.resolve_config(),
        )
    except ValueError as exc:
        _log_provider_route(
            "bad_request",
            started_at,
            operation="artifact_prepare",
            logger=LOGGER,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="artifact_prepare", logger=LOGGER)
        _log_unexpected_route_error("artifact_prepare", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_ARTIFACT_PREPARE_UNAVAILABLE_MESSAGE,
        ) from exc

    try:
        response_payload = _prepared_artifact_payload(artifact)
    except Exception as exc:
        _log_provider_route("error", started_at, operation="artifact_prepare", logger=LOGGER)
        _log_unexpected_route_error("artifact_prepare", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_ARTIFACT_PREPARE_UNAVAILABLE_MESSAGE,
        ) from exc

    _log_provider_route(
        "success",
        started_at,
        operation="artifact_prepare",
        provider_count=1,
        logger=LOGGER,
    )
    return response_payload


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

    started_at = time.perf_counter()
    _ensure_discovery_user(
        request_user,
        operation="job_create",
        started_at=started_at,
        logger=LOGGER,
    )
    _normalize_async_job_provider_id(
        payload.provider,
        operation="job_create",
        started_at=started_at,
        logger=LOGGER,
    )
    try:
        config = runtime_provider.resolve_config()
        candidate_token = _normalize_optional_text(payload.candidate_token)
        source_uri = (
            resolve_download_station_candidate_source_uri(
                candidate_token=candidate_token,
                config=config,
            )
            if candidate_token
            else _normalize_optional_text(payload.source_uri)
        )
        job = enqueue_download_station_task(
            source_uri=source_uri or "",
            confirmed=payload.confirmed,
            destination=_normalize_optional_text(payload.destination),
            config=config,
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="job_create", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DownloadStationError as exc:
        _log_provider_route(
            exc.reason or "provider_error",
            started_at,
            operation="job_create",
            logger=LOGGER,
        )
        LOGGER.info("Download Station handoff failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_create", logger=LOGGER)
        _log_unexpected_route_error("job_create", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_JOB_CREATE_UNAVAILABLE_MESSAGE,
        ) from exc

    try:
        response_payload = _job_payload(job, config=config)
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_create", logger=LOGGER)
        _log_unexpected_route_error("job_create", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_JOB_CREATE_UNAVAILABLE_MESSAGE,
        ) from exc

    _log_provider_route(
        "success",
        started_at,
        operation="job_create",
        provider_count=1,
        logger=LOGGER,
    )
    return response_payload


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

    started_at = time.perf_counter()
    _ensure_discovery_user(
        request_user,
        operation="job_poll",
        started_at=started_at,
        logger=LOGGER,
    )
    normalized_task_id = _normalize_route_id(task_id)
    if not normalized_task_id:
        _raise_bad_acquisition_route_id(
            operation="job_poll",
            started_at=started_at,
            detail="Missing acquisition task id",
            logger=LOGGER,
        )
    _normalize_async_job_provider_id(
        provider,
        operation="job_poll",
        started_at=started_at,
        logger=LOGGER,
    )
    try:
        config = runtime_provider.resolve_config()
        job = poll_download_station_task(
            task_id=normalized_task_id,
            config=config,
        )
    except ValueError as exc:
        _log_provider_route("bad_request", started_at, operation="job_poll", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DownloadStationError as exc:
        _log_provider_route(
            exc.reason or "provider_error",
            started_at,
            operation="job_poll",
            logger=LOGGER,
        )
        LOGGER.info("Download Station poll failed reason=%s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.public_message,
        ) from exc
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_poll", logger=LOGGER)
        _log_unexpected_route_error("job_poll", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_JOB_POLL_UNAVAILABLE_MESSAGE,
        ) from exc

    try:
        response_payload = _job_payload(job, config=config)
    except Exception as exc:
        _log_provider_route("error", started_at, operation="job_poll", logger=LOGGER)
        _log_unexpected_route_error("job_poll", logger=LOGGER)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ACQUISITION_JOB_POLL_UNAVAILABLE_MESSAGE,
        ) from exc

    _log_provider_route(
        "success",
        started_at,
        operation="job_poll",
        provider_count=1,
        logger=LOGGER,
    )
    return response_payload
