"""Aggregated pipeline routers composed from modular route groups."""

from __future__ import annotations

from fastapi import APIRouter, status

from ..schemas import PipelineSubmissionResponse
from .books_routes import router as books_router
from .jobs_routes import router as jobs_router, submit_pipeline
from .library_routes import router as library_router
from .media_routes import router as media_router, storage_router
from .system_routes import router as system_router
from .user_routes import router as user_router

router = APIRouter()

router.include_router(books_router)
router.include_router(jobs_router)
router.include_router(library_router)
router.include_router(media_router)
router.include_router(system_router)
router.include_router(user_router)

# Provide backwards compatibility for POST /pipelines without the trailing slash.
router.add_api_route(
    "",
    submit_pipeline,
    methods=["POST"],
    response_model=PipelineSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
    name="submit_pipeline_legacy",
)

__all__ = ["router", "storage_router"]
