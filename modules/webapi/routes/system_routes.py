"""Routes for system-level pipeline information."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from ... import config_manager as cfg
from ...images.drawthings import normalize_drawthings_base_urls, probe_drawthings_base_urls
from ...services.llm_models import list_available_llm_models
from ...services.source_discovery import safe_stat
from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_pipeline_job_manager,
    get_request_user,
    get_runtime_context_provider,
)
from ..route_telemetry import log_started_route_result
from ..schemas import (
    ImageNodeAvailabilityEntry,
    ImageNodeAvailabilityRequest,
    ImageNodeAvailabilityResponse,
    LLMModelListResponse,
    PipelineDefaultsResponse,
    PipelineIntakeStatusResponse,
)
from ..system_routes import queue_pressure_status
from modules.services.job_manager import PipelineJobManager
from modules.permissions import normalize_role

router = APIRouter()
logger = logging.getLogger(__name__)
_ALLOWED_ROLES = {"admin", "editor"}
_ALLOWED_LLM_MODEL_ROLES = {"admin", "editor", "viewer"}


def _log_pipeline_defaults_result(
    *,
    result: str,
    started_at: float,
    config_keys: int | None = None,
    has_input_file: bool | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="PIPELINE_DEFAULTS_ROUTE_DURATION",
        message="Pipeline defaults",
        operation="defaults",
        result=result,
        started_at=started_at,
        include_operation=False,
        config_keys=config_keys,
        has_input_file=str(has_input_file) if has_input_file is not None else None,
    )


def _log_llm_model_inventory(
    *,
    result: str,
    started_at: float,
    model_count: int | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="LLM_MODEL_ROUTE_DURATION",
        message="LLM model inventory",
        operation="list",
        result=result,
        started_at=started_at,
        include_operation=False,
        models=model_count,
    )


def _log_image_node_availability(
    *,
    result: str,
    started_at: float,
    requested: int | None = None,
    available: int | None = None,
    unavailable: int | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="IMAGE_NODE_ROUTE_DURATION",
        message="Image node availability",
        operation="availability",
        result=result,
        started_at=started_at,
        include_operation=False,
        requested=requested,
        available=available,
        unavailable=unavailable,
    )


def _log_pipeline_intake_status(
    *,
    result: str,
    started_at: float,
    queue_depth: int | None = None,
    active_count: int | None = None,
    accepting_jobs: bool | None = None,
    under_pressure: bool | None = None,
) -> None:
    log_started_route_result(
        logger,
        metric_name="PIPELINE_INTAKE_ROUTE_DURATION",
        message="Pipeline intake status",
        operation="status",
        result=result,
        started_at=started_at,
        include_operation=False,
        queue_depth=queue_depth,
        active=active_count,
        accepting=str(accepting_jobs) if accepting_jobs is not None else None,
        under_pressure=str(under_pressure) if under_pressure is not None else None,
    )


def _ensure_editor(request_user: RequestUserContext) -> None:
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/defaults", response_model=PipelineDefaultsResponse)
async def get_pipeline_defaults(
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Return the resolved baseline configuration for client defaults."""

    started_at = time.perf_counter()
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_ROLES:
        _log_pipeline_defaults_result(result="forbidden", started_at=started_at)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        resolved = context_provider.resolve_config()
        stripped = cfg.strip_derived_config(resolved)
        input_file = stripped.get("input_file")
        books_dir = resolved.get("books_dir")
        if isinstance(input_file, str) and input_file.strip():
            candidate = cfg.resolve_file_path(input_file.strip(), books_dir)
            if candidate and safe_stat(candidate) is None:
                stripped.pop("input_file", None)
    except Exception as exc:
        _log_pipeline_defaults_result(result="error", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to load pipeline defaults.",
        ) from exc

    _log_pipeline_defaults_result(
        result="success",
        started_at=started_at,
        config_keys=len(stripped),
        has_input_file=bool(stripped.get("input_file")),
    )
    return PipelineDefaultsResponse(config=stripped)


@router.get("/intake/status", response_model=PipelineIntakeStatusResponse)
async def get_pipeline_intake_status(
    job_manager: PipelineJobManager = Depends(get_pipeline_job_manager),
    request_user: RequestUserContext = Depends(get_request_user),
) -> PipelineIntakeStatusResponse:
    """Return token-safe job-intake status for creation surfaces."""

    started_at = time.perf_counter()
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_ROLES:
        _log_pipeline_intake_status(result="forbidden", started_at=started_at)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        pressure = await run_in_threadpool(queue_pressure_status, job_manager)
    except Exception as exc:
        _log_pipeline_intake_status(result="error", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to query pipeline intake status.",
        ) from exc

    _log_pipeline_intake_status(
        result="success",
        started_at=started_at,
        queue_depth=pressure.queue_depth,
        active_count=pressure.active_count,
        accepting_jobs=pressure.accepting_jobs,
        under_pressure=pressure.is_under_pressure,
    )
    return PipelineIntakeStatusResponse(
        acceptingJobs=pressure.accepting_jobs,
        isUnderPressure=pressure.is_under_pressure,
        queueDepth=pressure.queue_depth,
        activeCount=pressure.active_count,
        softLimit=pressure.soft_limit,
        hardLimit=pressure.hard_limit,
        delayCount=pressure.delay_count,
    )


@router.get("/llm-models", response_model=LLMModelListResponse, status_code=status.HTTP_200_OK)
async def get_llm_models(
    request_user: RequestUserContext = Depends(get_request_user),
) -> LLMModelListResponse:
    """Return the available LLM models from configured providers."""

    started_at = time.perf_counter()
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_LLM_MODEL_ROLES:
        _log_llm_model_inventory(result="forbidden", started_at=started_at)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        models = await run_in_threadpool(list_available_llm_models)
    except Exception as exc:
        _log_llm_model_inventory(result="error", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query LLM model list.",
        ) from exc

    _log_llm_model_inventory(
        result="success",
        started_at=started_at,
        model_count=len(models),
    )
    return LLMModelListResponse(models=models)


@router.post(
    "/image-nodes/availability",
    response_model=ImageNodeAvailabilityResponse,
    status_code=status.HTTP_200_OK,
)
async def check_image_node_availability(
    payload: ImageNodeAvailabilityRequest,
    request_user: RequestUserContext = Depends(get_request_user),
) -> ImageNodeAvailabilityResponse:
    """Check reachability of supplied Draw Things nodes."""

    started_at = time.perf_counter()
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_ROLES:
        _log_image_node_availability(result="forbidden", started_at=started_at)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        base_urls = normalize_drawthings_base_urls(base_urls=payload.base_urls)
    except Exception as exc:
        _log_image_node_availability(result="error", started_at=started_at)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to check image node availability.",
        ) from exc

    if not base_urls:
        _log_image_node_availability(
            result="empty",
            started_at=started_at,
            requested=0,
            available=0,
            unavailable=0,
        )
        return ImageNodeAvailabilityResponse()

    try:
        available, unavailable = await run_in_threadpool(
            probe_drawthings_base_urls, base_urls
        )
    except Exception as exc:
        _log_image_node_availability(
            result="error",
            started_at=started_at,
            requested=len(base_urls),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to check image node availability.",
        ) from exc

    available_set = set(available)
    nodes = [
        ImageNodeAvailabilityEntry(base_url=url, available=url in available_set)
        for url in base_urls
    ]
    _log_image_node_availability(
        result="success",
        started_at=started_at,
        requested=len(base_urls),
        available=len(available),
        unavailable=len(unavailable),
    )
    return ImageNodeAvailabilityResponse(
        nodes=nodes, available=available, unavailable=unavailable
    )


__all__ = ["router"]
