"""Discovery/acquisition provider routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules import logging_manager as log_mgr
from modules.permissions import normalize_role
from modules.services.acquisition import (
    AcquisitionArtifact,
    AcquisitionCandidate,
    AcquisitionProviderDiscoveryError,
    acquire_acquisition_candidate,
    discover_acquisition_candidates,
    list_acquisition_providers,
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
        artifact_path=artifact.artifact_path,
        local_path=artifact.local_path,
        filename=artifact.filename,
        size_bytes=artifact.size_bytes,
        modified_at=artifact.modified_at,
        next_actions=list(artifact.next_actions),
        metadata=dict(artifact.metadata),
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
