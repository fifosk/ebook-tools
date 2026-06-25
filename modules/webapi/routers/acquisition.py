"""Discovery/acquisition provider routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, status

from modules import logging_manager as log_mgr
from modules.services.acquisition import list_acquisition_providers

from ..dependencies import RuntimeContextProvider, get_runtime_context_provider
from ..route_telemetry import record_started_route_duration
from ..schemas.acquisition import AcquisitionProviderListResponse, AcquisitionProviderPayload


router = APIRouter(prefix="/api/acquisition", tags=["acquisition"])
LOGGER = log_mgr.get_logger().getChild("webapi.acquisition")


def _log_provider_route(result: str, started_at: float, *, provider_count: int = 0) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1000
    record_started_route_duration(
        "ACQUISITION_ROUTE_DURATION",
        "providers",
        result,
        started_at,
    )
    log_method = LOGGER.info if result != "success" or duration_ms >= 250 else LOGGER.debug
    log_method(
        "Acquisition provider route result=%s providers=%d duration_ms=%.1f",
        result,
        provider_count,
        duration_ms,
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
