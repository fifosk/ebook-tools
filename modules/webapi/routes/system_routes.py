"""Routes for system-level pipeline information."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from ... import config_manager as cfg
from ...images.drawthings import normalize_drawthings_base_urls, probe_drawthings_base_urls
from ...services.llm_models import list_available_llm_models
from ..dependencies import (
    RequestUserContext,
    RuntimeContextProvider,
    get_request_user,
    get_runtime_context_provider,
)
from ..schemas import (
    ImageNodeAvailabilityEntry,
    ImageNodeAvailabilityRequest,
    ImageNodeAvailabilityResponse,
    LLMModelListResponse,
    PipelineDefaultsResponse,
)
from modules.permissions import normalize_role

router = APIRouter()
_ALLOWED_ROLES = {"admin", "editor"}
_ALLOWED_LLM_MODEL_ROLES = {"admin", "editor", "viewer"}


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

    _ensure_editor(request_user)
    resolved = context_provider.resolve_config()
    stripped = cfg.strip_derived_config(resolved)
    return PipelineDefaultsResponse(config=stripped)


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
