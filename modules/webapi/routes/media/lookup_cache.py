"""Lookup cache routes for cached word definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

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
from .common import _resolve_job_root

router = APIRouter()


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
    except HTTPException:
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
    cache = _load_cache_for_job(
        job_id,
        locator,
        library_repository,
        request_user,
        pipeline_service._job_manager,
    )

    if cache is None:
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
    cache = _load_cache_for_job(
        job_id,
        locator,
        library_repository,
        request_user,
        pipeline_service._job_manager,
    )

    if cache is None:
        return LookupCacheSummaryResponse(available=False)

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
    cache = _load_cache_for_job(
        job_id,
        locator,
        library_repository,
        request_user,
        pipeline_service._job_manager,
    )

    normalized = normalize_word(word)
    if cache is None:
        return LookupCacheEntryResponse(
            word=word,
            word_normalized=normalized,
            cached=False,
        )

    entry = cache.get(word)
    if entry is None:
        return LookupCacheEntryResponse(
            word=word,
            word_normalized=normalized,
            cached=False,
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
    cache = _load_cache_for_job(
        job_id,
        locator,
        library_repository,
        request_user,
        pipeline_service._job_manager,
    )

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

    return LookupCacheBulkResponse(
        results=results,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
    )
