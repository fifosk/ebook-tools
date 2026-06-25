"""Lookup cache routes for cached word definitions."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from modules import logging_manager as log_mgr

from ....lookup_cache import LookupCache, load_lookup_cache, normalize_word
from ....library import LibraryRepository
from ....services.file_locator import FileLocator
from ....services.pipeline_service import PipelineService
from ...dependencies import (
    RequestUserContext,
    get_file_locator,
    get_library_repository,
    get_pipeline_service,
    get_request_user,
)
from ...route_telemetry import record_started_route_duration
from .common import _resolve_job_root

router = APIRouter()
logger = log_mgr.get_logger().getChild("webapi.routes.lookup_cache")


class LookupCacheEntryResponse(BaseModel):
    """Response for a single cached word lookup."""

    word: str
    word_normalized: str
    cached: bool
    lookup_result: Optional[Dict[str, Any]] = None
    audio_references: List[Dict[str, Any]] = Field(default_factory=list)


class LookupCacheBulkRequest(BaseModel):
    """Request for bulk word lookup from cache."""

    words: List[str] = Field(min_length=1, max_length=100)


class LookupCacheBulkResponse(BaseModel):
    """Response for bulk word lookup from cache."""

    results: Dict[str, Optional[LookupCacheEntryResponse]]
    cache_hits: int
    cache_misses: int


class LookupCacheSummaryResponse(BaseModel):
    """Summary information about the lookup cache."""

    available: bool
    word_count: int = 0
    input_language: str = ""
    definition_language: str = ""
    llm_calls: int = 0
    skipped_stopwords: int = 0
    build_time_seconds: float = 0.0


class LookupCacheFullResponse(BaseModel):
    """Full lookup cache for offline download."""

    version: str = "1"
    input_language: str
    definition_language: str
    entries: Dict[str, LookupCacheEntryResponse]


def _record_lookup_cache_route_duration(operation: str, result: str, started_at: float) -> None:
    """Record token-safe lookup-cache route timing if metrics are available."""

    record_started_route_duration(
        "LOOKUP_CACHE_ROUTE_DURATION",
        operation,
        result,
        started_at,
    )


def _log_lookup_cache_route_result(
    *,
    operation: str,
    result: str,
    started_at: float,
    available: bool | None = None,
    entries: int | None = None,
    words: int | None = None,
    hits: int | None = None,
    misses: int | None = None,
) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1000.0
    details = (
        f"Lookup cache route operation={operation} "
        f"result={result} duration_ms={duration_ms:.1f}"
    )
    if available is not None:
        details += f" available={str(available).lower()}"
    if entries is not None:
        details += f" entries={entries}"
    if words is not None:
        details += f" words={words}"
    if hits is not None:
        details += f" hits={hits}"
    if misses is not None:
        details += f" misses={misses}"
    log_method = logger.info if result not in {"success", "cache_hit", "cache_miss", "unavailable"} or duration_ms >= 250 else logger.debug
    log_method(details)


def _record_lookup_cache_http_exception(
    *,
    operation: str,
    started_at: float,
    exc: HTTPException,
) -> None:
    result = "forbidden" if exc.status_code == status.HTTP_403_FORBIDDEN else "error"
    _record_lookup_cache_route_duration(operation, result, started_at)
    _log_lookup_cache_route_result(
        operation=operation,
        result=result,
        started_at=started_at,
    )


def _load_cache_for_job(
    job_id: str,
    locator: FileLocator,
    library_repository: LibraryRepository,
    request_user: RequestUserContext,
    job_manager: Any,
) -> Optional[LookupCache]:
    """Load the lookup cache for a job if it exists."""
    try:
        job_root = _resolve_job_root(
            job_id=job_id,
            locator=locator,
            library_repository=library_repository,
            request_user=request_user,
            job_manager=job_manager,
            permission="view",
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise
        return None

    return load_lookup_cache(job_root)


@router.get(
    "/api/pipelines/jobs/{job_id}/lookup-cache",
    response_model=LookupCacheFullResponse,
    summary="Get full lookup cache",
    description="Get the complete lookup cache for offline download.",
)
async def get_lookup_cache_full(
    job_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
) -> LookupCacheFullResponse:
    """Get the full lookup cache for offline download."""
    started_at = time.perf_counter()
    try:
        cache = _load_cache_for_job(
            job_id,
            locator,
            library_repository,
            request_user,
            pipeline_service._job_manager,
        )
    except HTTPException as exc:
        _record_lookup_cache_http_exception(
            operation="full",
            started_at=started_at,
            exc=exc,
        )
        raise

    if cache is None:
        _record_lookup_cache_route_duration("full", "not_found", started_at)
        _log_lookup_cache_route_result(
            operation="full",
            result="not_found",
            started_at=started_at,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lookup cache not found for this job",
        )

    # Build entries dictionary indexed by normalized word
    entries: Dict[str, LookupCacheEntryResponse] = {}
    for normalized_word, entry in cache.entries.items():
        entries[normalized_word] = LookupCacheEntryResponse(
            word=entry.word,
            word_normalized=entry.word_normalized,
            cached=True,
            lookup_result=entry.lookup_result,
            audio_references=[ref.to_dict() for ref in entry.audio_references],
        )

    _record_lookup_cache_route_duration("full", "success", started_at)
    _log_lookup_cache_route_result(
        operation="full",
        result="success",
        started_at=started_at,
        entries=len(entries),
    )
    return LookupCacheFullResponse(
        version="1",
        input_language=cache.input_language,
        definition_language=cache.definition_language,
        entries=entries,
    )


@router.get(
    "/api/pipelines/jobs/{job_id}/lookup-cache/summary",
    response_model=LookupCacheSummaryResponse,
    summary="Get lookup cache summary",
    description="Get summary information about the lookup cache for a job.",
)
async def get_lookup_cache_summary(
    job_id: str,
    request_user: RequestUserContext = Depends(get_request_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
) -> LookupCacheSummaryResponse:
    """Get summary information about the lookup cache."""
    started_at = time.perf_counter()
    try:
        cache = _load_cache_for_job(
            job_id,
            locator,
            library_repository,
            request_user,
            pipeline_service._job_manager,
        )
    except HTTPException as exc:
        _record_lookup_cache_http_exception(
            operation="summary",
            started_at=started_at,
            exc=exc,
        )
        raise

    if cache is None:
        _record_lookup_cache_route_duration("summary", "unavailable", started_at)
        _log_lookup_cache_route_result(
            operation="summary",
            result="unavailable",
            started_at=started_at,
            available=False,
        )
        return LookupCacheSummaryResponse(available=False)

    _record_lookup_cache_route_duration("summary", "success", started_at)
    _log_lookup_cache_route_result(
        operation="summary",
        result="success",
        started_at=started_at,
        available=True,
        entries=cache.stats.total_words,
    )
    return LookupCacheSummaryResponse(
        available=True,
        word_count=cache.stats.total_words,
        input_language=cache.input_language,
        definition_language=cache.definition_language,
        llm_calls=cache.stats.llm_calls,
        skipped_stopwords=cache.stats.skipped_stopwords,
        build_time_seconds=cache.stats.build_time_seconds,
    )


@router.get(
    "/api/pipelines/jobs/{job_id}/lookup-cache/{word}",
    response_model=LookupCacheEntryResponse,
    summary="Get cached word lookup",
    description="Look up a word from the job's lookup cache.",
)
async def get_cached_lookup(
    job_id: str,
    word: str,
    request_user: RequestUserContext = Depends(get_request_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
) -> LookupCacheEntryResponse:
    """Look up a word from the job's lookup cache."""
    started_at = time.perf_counter()
    try:
        cache = _load_cache_for_job(
            job_id,
            locator,
            library_repository,
            request_user,
            pipeline_service._job_manager,
        )
    except HTTPException as exc:
        _record_lookup_cache_http_exception(
            operation="word",
            started_at=started_at,
            exc=exc,
        )
        raise

    normalized = normalize_word(word)
    if cache is None:
        _record_lookup_cache_route_duration("word", "cache_miss", started_at)
        _log_lookup_cache_route_result(
            operation="word",
            result="cache_miss",
            started_at=started_at,
            available=False,
            words=1,
            hits=0,
            misses=1,
        )
        return LookupCacheEntryResponse(
            word=word,
            word_normalized=normalized,
            cached=False,
        )

    entry = cache.get(word)
    if entry is None:
        _record_lookup_cache_route_duration("word", "cache_miss", started_at)
        _log_lookup_cache_route_result(
            operation="word",
            result="cache_miss",
            started_at=started_at,
            available=True,
            words=1,
            hits=0,
            misses=1,
        )
        return LookupCacheEntryResponse(
            word=word,
            word_normalized=normalized,
            cached=False,
        )

    _record_lookup_cache_route_duration("word", "cache_hit", started_at)
    _log_lookup_cache_route_result(
        operation="word",
        result="cache_hit",
        started_at=started_at,
        available=True,
        words=1,
        hits=1,
        misses=0,
    )
    return LookupCacheEntryResponse(
        word=entry.word,
        word_normalized=entry.word_normalized,
        cached=True,
        lookup_result=entry.lookup_result,
        audio_references=[ref.to_dict() for ref in entry.audio_references],
    )


@router.post(
    "/api/pipelines/jobs/{job_id}/lookup-cache/bulk",
    response_model=LookupCacheBulkResponse,
    summary="Bulk word lookup from cache",
    description="Look up multiple words from the job's lookup cache.",
)
async def get_cached_lookups_bulk(
    job_id: str,
    request: LookupCacheBulkRequest,
    request_user: RequestUserContext = Depends(get_request_user),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    locator: FileLocator = Depends(get_file_locator),
    library_repository: LibraryRepository = Depends(get_library_repository),
) -> LookupCacheBulkResponse:
    """Look up multiple words from the job's lookup cache."""
    started_at = time.perf_counter()
    try:
        cache = _load_cache_for_job(
            job_id,
            locator,
            library_repository,
            request_user,
            pipeline_service._job_manager,
        )
    except HTTPException as exc:
        _record_lookup_cache_http_exception(
            operation="bulk",
            started_at=started_at,
            exc=exc,
        )
        raise

    results: Dict[str, Optional[LookupCacheEntryResponse]] = {}
    cache_hits = 0
    cache_misses = 0

    for word in request.words:
        if cache is None:
            results[word] = None
            cache_misses += 1
            continue

        entry = cache.get(word)
        if entry is None:
            results[word] = None
            cache_misses += 1
        else:
            results[word] = LookupCacheEntryResponse(
                word=entry.word,
                word_normalized=entry.word_normalized,
                cached=True,
                lookup_result=entry.lookup_result,
                audio_references=[ref.to_dict() for ref in entry.audio_references],
            )
            cache_hits += 1

    result = "success" if cache is not None else "unavailable"
    _record_lookup_cache_route_duration("bulk", result, started_at)
    _log_lookup_cache_route_result(
        operation="bulk",
        result=result,
        started_at=started_at,
        available=cache is not None,
        words=len(request.words),
        hits=cache_hits,
        misses=cache_misses,
    )
    return LookupCacheBulkResponse(
        results=results,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
    )
