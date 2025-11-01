"""Routes for system-level pipeline information."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ... import config_manager as cfg
from ..dependencies import RuntimeContextProvider, get_runtime_context_provider
from ..schemas import PipelineDefaultsResponse

router = APIRouter()

@router.get("/defaults", response_model=PipelineDefaultsResponse)
async def get_pipeline_defaults(
    context_provider: RuntimeContextProvider = Depends(get_runtime_context_provider),
):
    """Return the resolved baseline configuration for client defaults."""

    resolved = context_provider.resolve_config()
    stripped = cfg.strip_derived_config(resolved)
    return PipelineDefaultsResponse(config=stripped)


__all__ = ["router"]
