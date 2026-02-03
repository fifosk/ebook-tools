"""Aggregated media routes composed from modular handlers."""

from __future__ import annotations

from fastapi import APIRouter

from .media.images import router as images_router
from .media.lookup_cache import router as lookup_cache_router
from .media.media_list import router as media_router
from .media.storage import _stream_local_file, storage_router
from .media.timing import jobs_timing_router

router = APIRouter()
router.include_router(images_router)
router.include_router(lookup_cache_router)
router.include_router(media_router)


def register_exception_handlers(app) -> None:
    """Compatibility shim; legacy media routes register their own handlers."""
    return None


__all__ = [
    "router",
    "storage_router",
    "jobs_timing_router",
    "lookup_cache_router",
    "register_exception_handlers",
    "_stream_local_file",
]
