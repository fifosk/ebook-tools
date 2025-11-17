"""Routes for system-level pipeline information."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ... import config_manager as cfg
from ...services.llm_models import list_available_llm_models
from ..dependencies import RuntimeContextProvider, get_runtime_context_provider
from ..schemas import LLMModelListResponse, PipelineDefaultsResponse

router = APIRouter()

@router.get("/defaults", response_model=PipelineDefaultsResponse)
async def get_pipeline_defaults(
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Return the resolved baseline configuration for client defaults."""

    resolved = context_provider.resolve_config()
    stripped = cfg.strip_derived_config(resolved)
    return PipelineDefaultsResponse(config=stripped)


@router.get("/llm-models", response_model=LLMModelListResponse, status_code=status.HTTP_200_OK)
async def get_llm_models() -> LLMModelListResponse:
    """Return the available LLM models from the Ollama server."""

    try:
        models = list_available_llm_models()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to query Ollama model list.",
        ) from exc
    return LLMModelListResponse(models=models)


__all__ = ["router"]
