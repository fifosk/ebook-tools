"""Shared acquisition route validation and telemetry helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from modules import logging_manager as log_mgr
from modules.permissions import normalize_role

from ..dependencies import RequestUserContext
from ..route_ids import normalize_route_id
from ..route_telemetry import log_started_route_result
from ..schemas.acquisition import (
    AcquisitionDiscoveryResponse,
    AcquisitionProviderListResponse,
    AcquisitionProviderPayload,
)
from .acquisition_payloads import candidate_payload


LOGGER = log_mgr.get_logger().getChild("webapi.acquisition")
ACQUISITION_PROVIDERS_UNAVAILABLE_MESSAGE = "Unable to load acquisition providers."
ACQUISITION_DISCOVERY_UNAVAILABLE_MESSAGE = "Unable to query acquisition provider."
ACQUISITION_ACQUIRE_UNAVAILABLE_MESSAGE = "Unable to acquire candidate."
ACQUISITION_ARTIFACT_PREPARE_UNAVAILABLE_MESSAGE = (
    "Unable to prepare acquisition artifact."
)
ACQUISITION_JOB_CREATE_UNAVAILABLE_MESSAGE = "Unable to submit acquisition job."
ACQUISITION_JOB_POLL_UNAVAILABLE_MESSAGE = "Unable to poll acquisition job."

_ALLOWED_DISCOVERY_ROLES = {"admin", "editor"}


def log_provider_route(
    result: str,
    started_at: float,
    *,
    operation: str = "providers",
    provider_count: int = 0,
    logger=None,
) -> None:
    log_started_route_result(
        logger or LOGGER,
        metric_name="ACQUISITION_ROUTE_DURATION",
        message=f"Acquisition {operation} route",
        operation=operation,
        result=result,
        started_at=started_at,
        include_operation=False,
        duration_first=False,
        providers=provider_count,
    )


def log_unexpected_route_error(operation: str, *, logger=None) -> None:
    (logger or LOGGER).warning(
        "Acquisition %s route failed unexpectedly; response detail suppressed",
        operation,
    )


def ensure_discovery_user(
    request_user: RequestUserContext,
    *,
    operation: str,
    started_at: float,
    logger=None,
) -> None:
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_DISCOVERY_ROLES:
        log_provider_route("forbidden", started_at, operation=operation, logger=logger)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def provider_list_response(registry) -> AcquisitionProviderListResponse:
    """Shape a token-safe provider registry response for Web and Apple Create."""

    return AcquisitionProviderListResponse(
        providers=[
            AcquisitionProviderPayload(**provider.as_dict())
            for provider in registry.providers
        ],
        policy_notes=list(registry.policy_notes),
        paths=dict(registry.paths),
        default_provider_ids={
            media_kind: list(provider_ids)
            for media_kind, provider_ids in registry.default_provider_ids.items()
        },
    )


def discovery_response(result) -> AcquisitionDiscoveryResponse:
    """Shape normalized discovery candidates into the public route schema."""

    return AcquisitionDiscoveryResponse(
        candidates=[candidate_payload(candidate) for candidate in result.candidates],
        policy_notes=list(result.policy_notes),
        providers_queried=list(result.providers_queried),
    )


def normalize_async_job_provider_id(
    value: str | None,
    *,
    operation: str,
    started_at: float,
    logger=None,
) -> str:
    provider_id = str(value or "").strip().casefold()
    if not provider_id:
        raise_bad_acquisition_route_id(
            operation=operation,
            started_at=started_at,
            detail="Missing acquisition provider",
            logger=logger,
        )
    if provider_id != "download_station":
        log_provider_route("bad_request", started_at, operation=operation, logger=logger)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider does not support async acquisition jobs",
        )
    return provider_id


def raise_bad_acquisition_route_id(
    *,
    operation: str,
    started_at: float,
    detail: str,
    logger=None,
) -> None:
    log_provider_route("bad_request", started_at, operation=operation, logger=logger)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
