"""Routes that expose library-aware pipeline helpers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, List, Mapping, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules import logging_manager
from modules.library import LibraryError, LibrarySync
from modules.permissions import can_access, resolve_access_policy

from ...services.file_locator import FileLocator
from ...services.pipeline_service import PipelineService
from ..dependencies import (
    RequestUserContext,
    get_file_locator,
    get_library_sync,
    get_pipeline_service,
    get_request_user,
)
from modules.services.job_manager import PipelineJob
from ..schemas import MediaSearchHit, MediaSearchResponse, PipelineMediaFile
from ...search import search_generated_media

router = APIRouter()
LOGGER = logging_manager.get_logger().getChild("webapi.search")


def _record_search_route_duration(operation: str, result: str, started_at: float) -> None:
    """Record token-safe search route timing if metrics are available."""

    try:
        from ..metrics import SEARCH_ROUTE_DURATION
    except Exception:
        return
    SEARCH_ROUTE_DURATION.labels(operation=operation, result=result).observe(
        time.perf_counter() - started_at
    )


def _extract_match_snippet(text: Any, query: str) -> Optional[str]:
    if not isinstance(text, str):
        return None
    stripped_query = query.strip()
    if not stripped_query:
        return None

    tokens = [token for token in stripped_query.split() if token]
    if not tokens:
        return None

    lower_text = text.lower()
    for token in tokens:
        lower_token = token.lower()
        index = lower_text.find(lower_token)
        if index == -1:
            continue
        window = 60
        start = max(0, index - window)
        end = min(len(text), index + len(lower_token) + window)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = f"…{snippet}"
        if end < len(text):
            snippet = f"{snippet}…"
        return snippet
    return None


def _build_library_search_snippet(item: Mapping[str, Any], query: str) -> str:
    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        media_metadata = metadata.get("media_metadata") or metadata.get("book_metadata")
        if isinstance(media_metadata, Mapping):
            preferred_keys = [
                "book_summary",
                "summary",
                "description",
                "synopsis",
            ]
            for key in preferred_keys:
                snippet = _extract_match_snippet(media_metadata.get(key), query)
                if snippet:
                    return snippet

    fallback_candidates = [
        item.get("book_title"),
        item.get("author"),
        item.get("genre"),
    ]
    for candidate in fallback_candidates:
        snippet = _extract_match_snippet(candidate, query)
        if snippet:
            return snippet

    title = item.get("book_title") or "Library entry"
    author = item.get("author") or ""
    language = item.get("language") or ""
    genre = item.get("genre") or ""

    parts = [title]
    if author:
        parts.append(f"by {author}")
    summary_parts: List[str] = []
    if language:
        summary_parts.append(language)
    if genre:
        summary_parts.append(genre)
    if summary_parts:
        parts.append(f"({' • '.join(summary_parts)})")

    return " ".join(parts).strip()


class _LibrarySearchJobAdapter:
    """Minimal adapter that exposes library metadata to the media search helpers."""

    __slots__ = ("job_id", "generated_files", "request", "resume_context", "request_payload", "job_root")

    def __init__(
        self,
        job_id: str,
        generated_files: Mapping[str, Any],
        *,
        label: Optional[str] = None,
        job_root: Optional[Path] = None,
    ) -> None:
        self.job_id = job_id
        self.generated_files = generated_files
        self.request: Any = None
        self.resume_context: Optional[Mapping[str, Any]] = None
        if label:
            self.request_payload: Optional[Mapping[str, Any]] = {
                "inputs": {"media_metadata": {"title": label}}
            }
        else:
            self.request_payload = None
        self.job_root = job_root


@router.get("/search", response_model=MediaSearchResponse)
async def search_pipeline_media(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    job_id: str = Query(..., alias="job_id"),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    file_locator: FileLocator = Depends(get_file_locator),
    library_sync: LibrarySync = Depends(get_library_sync),
    request_user: RequestUserContext = Depends(get_request_user),
):
    """Search across generated ebook media for the provided query."""

    started_at = time.perf_counter()
    normalized_query = query.strip()
    if not normalized_query:
        duration_ms = (time.perf_counter() - started_at) * 1000.0
        _record_search_route_duration("pipeline_media", "blank", started_at)
        LOGGER.debug(
            "Pipeline media search skipped blank query job_id_present=%s limit=%s duration_ms=%.1f",
            bool(job_id),
            limit,
            duration_ms,
        )
        return MediaSearchResponse(query=query, limit=limit, count=0, results=[])

    try:
        job = pipeline_service.get_job(
            job_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
        )
    except KeyError:
        job = None
    except PermissionError as exc:
        duration_ms = (time.perf_counter() - started_at) * 1000.0
        _record_search_route_duration("pipeline_media", "forbidden", started_at)
        LOGGER.info(
            "Pipeline media search forbidden job_id_present=%s limit=%s query_present=%s duration_ms=%.1f",
            bool(job_id),
            limit,
            True,
            duration_ms,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    library_item = None
    if job is None and library_sync is not None:
        library_item = library_sync.get_item(job_id)

    if job is None and library_item is None:  # pragma: no cover - defensive guard
        duration_ms = (time.perf_counter() - started_at) * 1000.0
        _record_search_route_duration("pipeline_media", "not_found", started_at)
        LOGGER.info(
            "Pipeline media search missing target job_id_present=%s limit=%s query_present=%s duration_ms=%.1f",
            bool(job_id),
            limit,
            True,
            duration_ms,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job is None and library_item is not None:
        metadata_payload = library_item.metadata.data if hasattr(library_item.metadata, "data") else {}
        owner_id = library_item.owner_id or metadata_payload.get("user_id") or metadata_payload.get("owner_id")
        if isinstance(owner_id, str):
            owner_id = owner_id.strip() or None
        policy = resolve_access_policy(metadata_payload.get("access"), default_visibility="public")
        if not can_access(
            policy,
            owner_id=owner_id,
            user_id=request_user.user_id,
            user_role=request_user.user_role,
            permission="view",
        ):
            duration_ms = (time.perf_counter() - started_at) * 1000.0
            _record_search_route_duration("pipeline_media", "forbidden", started_at)
            LOGGER.info(
                "Pipeline media search forbidden library target job_id_present=%s limit=%s query_present=%s duration_ms=%.1f",
                bool(job_id),
                limit,
                True,
                duration_ms,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access library item")

    jobs_to_search: List[PipelineJob | _LibrarySearchJobAdapter] = []
    library_job_ids: set[str] = set()
    if job is not None:
        jobs_to_search.append(job)
    elif library_item is not None:
        serialized_item = library_sync.serialize_item(library_item)
        metadata_payload = serialized_item.get("metadata")
        generated_files = (
            metadata_payload.get("generated_files") if isinstance(metadata_payload, Mapping) else None
        )
        if isinstance(generated_files, Mapping):
            label = serialized_item.get("book_title") or metadata_payload.get("book_title")
            library_path_value = serialized_item.get("library_path")
            job_root_path: Optional[Path]
            if isinstance(library_path_value, str) and library_path_value.strip():
                job_root_path = Path(library_path_value).expanduser()
            else:
                job_root_path = None
            jobs_to_search.append(
                _LibrarySearchJobAdapter(
                    job_id=job_id,
                    generated_files=generated_files,
                    label=label if isinstance(label, str) and label.strip() else None,
                    job_root=job_root_path,
                )
            )
            library_job_ids.add(job_id)

    hits = search_generated_media(
        query=normalized_query,
        jobs=tuple(jobs_to_search),
        locator=file_locator,
        limit=limit,
    ) if jobs_to_search else []

    serialized_hits: list[MediaSearchHit] = []
    for hit in hits:
        media_payload: dict[str, list[PipelineMediaFile]] = {}
        for category, entries in hit.media.items():
            if not entries:
                continue
            files: list[PipelineMediaFile] = []
            for entry in entries:
                size_value = entry.get("size")
                if isinstance(size_value, (int, float)):
                    file_size = int(size_value)
                else:
                    file_size = None
                media_file = PipelineMediaFile(
                    name=str(entry.get("name") or "media"),
                    url=entry.get("url"),
                    size=file_size,
                    updated_at=entry.get("updated_at"),
                    source=str(entry.get("source") or "completed"),
                    relative_path=entry.get("relative_path"),
                    path=entry.get("path"),
                )
                files.append(media_file)
            if files:
                media_payload[category] = files
        hit_source = "library" if hit.job_id in library_job_ids else "pipeline"
        serialized_hits.append(
            MediaSearchHit(
                job_id=hit.job_id,
                job_label=hit.job_label,
                base_id=hit.base_id,
                chunk_id=hit.chunk_id,
                chunk_index=hit.chunk_index,
                chunk_total=hit.chunk_total,
                range_fragment=hit.range_fragment,
                start_sentence=hit.start_sentence,
                end_sentence=hit.end_sentence,
                snippet=hit.snippet,
                occurrence_count=hit.occurrence_count,
                match_start=hit.match_start,
                match_end=hit.match_end,
                text_length=hit.text_length,
                offset_ratio=hit.offset_ratio,
                approximate_time_seconds=hit.approximate_time_seconds,
                cue_start_seconds=hit.cue_start_seconds,
                cue_end_seconds=hit.cue_end_seconds,
                media=media_payload,
                source=hit_source,
            )
        )

    available_slots = max(limit - len(serialized_hits), 0)
    library_hits: list[MediaSearchHit] = []
    library_fallback_error = False
    if library_sync is not None and available_slots > 0:
        try:
            library_search = library_sync.search(
                query=normalized_query,
                page=1,
                limit=min(available_slots, limit),
                user_id=request_user.user_id,
                user_role=request_user.user_role,
            )
        except LibraryError:
            library_fallback_error = True
            library_search = None

        if library_search is not None:
            seen_ids = {hit.job_id for hit in serialized_hits}
            for entry in library_search.items:
                serialized_item = library_sync.serialize_item(entry)
                job_identifier = serialized_item.get("job_id") or entry.id
                if job_identifier in seen_ids:
                    continue
                snippet = _build_library_search_snippet(serialized_item, normalized_query)
                library_hits.append(
                    MediaSearchHit(
                        job_id=job_identifier,
                        job_label=serialized_item.get("book_title") or job_identifier,
                        base_id=None,
                        chunk_id=None,
                        range_fragment=None,
                        start_sentence=None,
                        end_sentence=None,
                        snippet=snippet,
                        occurrence_count=1,
                        match_start=None,
                        match_end=None,
                        text_length=None,
                        offset_ratio=None,
                        approximate_time_seconds=None,
                        media={},
                        source="library",
                        library_author=serialized_item.get("author"),
                        library_genre=serialized_item.get("genre"),
                        library_language=serialized_item.get("language"),
                        cover_path=serialized_item.get("cover_path"),
                        library_path=serialized_item.get("library_path"),
                    )
                )
                seen_ids.add(job_identifier)
                if len(library_hits) >= available_slots:
                    break

    combined_results = serialized_hits + library_hits
    duration_ms = (time.perf_counter() - started_at) * 1000.0
    _record_search_route_duration("pipeline_media", "success", started_at)
    log_method = LOGGER.info if duration_ms >= 250 else LOGGER.debug
    log_method(
        "Pipeline media search completed job_id_present=%s pipeline_target=%s library_target=%s limit=%s pipeline_hits=%s library_hits=%s total=%s library_fallback_error=%s duration_ms=%.1f",
        bool(job_id),
        job is not None,
        library_item is not None,
        limit,
        len(serialized_hits),
        len(library_hits),
        len(combined_results),
        library_fallback_error,
        duration_ms,
    )

    return MediaSearchResponse(
        query=normalized_query,
        limit=limit,
        count=len(combined_results),
        results=combined_results,
    )


__all__ = ["router"]
