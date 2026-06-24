"""Routes for system-level pipeline information."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from ... import config_manager as cfg
from ...images.drawthings import normalize_drawthings_base_urls, probe_drawthings_base_urls
from ...services.llm_models import list_available_llm_models
from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_pipeline_job_manager,
    get_request_user,
    get_runtime_context_provider,
)
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


def _record_pipeline_intake_route_duration(operation: str, result: str, started_at: float) -> None:
    """Record token-safe intake route timing if metrics are available."""

    try:
        from ..metrics import PIPELINE_INTAKE_ROUTE_DURATION
    except Exception:
        return
    PIPELINE_INTAKE_ROUTE_DURATION.labels(operation=operation, result=result).observe(
        time.perf_counter() - started_at
    )


def _record_pipeline_defaults_route_duration(
    operation: str,
    result: str,
    started_at: float,
) -> None:
    """Record token-safe defaults route timing if metrics are available."""

    try:
        from ..metrics import PIPELINE_DEFAULTS_ROUTE_DURATION
    except Exception:
        return
    PIPELINE_DEFAULTS_ROUTE_DURATION.labels(operation=operation, result=result).observe(
        time.perf_counter() - started_at
    )


def _log_pipeline_defaults_result(
    *,
    result: str,
    started_at: float,
    config_keys: int | None = None,
    has_input_file: bool | None = None,
) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1000
    details = f"Pipeline defaults result={result} duration_ms={duration_ms:.1f}"
    if config_keys is not None:
        details += f" config_keys={config_keys}"
    if has_input_file is not None:
        details += f" has_input_file={has_input_file}"
    log_method = logger.info if result != "success" or duration_ms >= 250 else logger.debug
    log_method(details)


def _log_pipeline_intake_status(
    *,
    result: str,
    started_at: float,
    queue_depth: int | None = None,
    active_count: int | None = None,
    accepting_jobs: bool | None = None,
    under_pressure: bool | None = None,
) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1000
    details = (
        f"Pipeline intake status result={result} duration_ms={duration_ms:.1f}"
    )
    if queue_depth is not None:
        details += f" queue_depth={queue_depth}"
    if active_count is not None:
        details += f" active={active_count}"
    if accepting_jobs is not None:
        details += f" accepting={accepting_jobs}"
    if under_pressure is not None:
        details += f" under_pressure={under_pressure}"
    log_method = logger.info if result != "success" or duration_ms >= 250 else logger.debug
    log_method(details)


def _ensure_editor(request_user: RequestUserContext) -> None:
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _ensure_llm_model_access(request_user: RequestUserContext) -> None:
    role = normalize_role(request_user.user_role) or ""
    if role not in _ALLOWED_LLM_MODEL_ROLES:
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
        _record_pipeline_defaults_route_duration("defaults", "forbidden", started_at)
        _log_pipeline_defaults_result(result="forbidden", started_at=started_at)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        resolved = context_provider.resolve_config()
        stripped = cfg.strip_derived_config(resolved)
        input_file = stripped.get("input_file")
        books_dir = resolved.get("books_dir")
        if isinstance(input_file, str) and input_file.strip():
            candidate = cfg.resolve_file_path(input_file.strip(), books_dir)
            if candidate and not candidate.exists():
                stripped.pop("input_file", None)
    except Exception:
        _record_pipeline_defaults_route_duration("defaults", "error", started_at)
        _log_pipeline_defaults_result(result="error", started_at=started_at)
        raise

    _record_pipeline_defaults_route_duration("defaults", "success", started_at)
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
        _record_pipeline_intake_route_duration("status", "forbidden", started_at)
        _log_pipeline_intake_status(result="forbidden", started_at=started_at)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        pressure = queue_pressure_status(job_manager)
    except Exception:
        _record_pipeline_intake_route_duration("status", "error", started_at)
        _log_pipeline_intake_status(result="error", started_at=started_at)
        raise

    _record_pipeline_intake_route_duration("status", "success", started_at)
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

    _ensure_llm_model_access(request_user)
    try:
        models = list_available_llm_models()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query LLM model list.",
        ) from exc
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

    _ensure_editor(request_user)
    base_urls = normalize_drawthings_base_urls(base_urls=payload.base_urls)
    if not base_urls:
        return ImageNodeAvailabilityResponse()

    available, unavailable = await run_in_threadpool(
        probe_drawthings_base_urls, base_urls
    )
    available_set = set(available)
    nodes = [
        ImageNodeAvailabilityEntry(base_url=url, available=url in available_set)
        for url in base_urls
    ]
    return ImageNodeAvailabilityResponse(
        nodes=nodes, available=available, unavailable=unavailable
    )


__all__ = ["router"]
