"""Normalized source discovery for acquisition-backed Create flows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import requests

from .provider_catalog import discovery_media_kinds_for
from .provider_registry import default_discovery_provider_ids
from .discovery_planning import (
    order_default_discovery_candidates,
    provider_query_limit,
)
from .discovery_normalization import (
    normalize_limit as _normalize_limit,
    normalize_media_kind as _normalize_media_kind,
    normalize_provider as _normalize_provider,
    normalize_query as _normalize_query,
)
from .file_sources import (
    append_bounded_newest_candidate as _append_bounded_newest_candidate,
    discover_local_epubs as _discover_local_epubs,
    discover_manual_downloads as _discover_manual_downloads,
    discover_nas_videos as _discover_nas_videos,
)
from .indexer_discovery import (
    discover_newznab_torznab as _discover_newznab_torznab,
)
from .gutenberg_discovery import (
    discover_gutenberg as _discover_gutenberg,
)
from .internet_archive_discovery import (
    discover_internet_archive as _discover_internet_archive,
    normalize_internet_archive_source_ids as _normalize_source_ids,
)
from .openlibrary_discovery import (
    discover_openlibrary as _discover_openlibrary,
)
from .models import (
    AcquisitionCandidate,
    AcquisitionDiscoveryResult,
    AcquisitionProviderDiscoveryError,
)
from .youtube_discovery import (
    discover_youtube_search as _discover_youtube_search,
    discover_youtube_url as _discover_youtube_url,
)


@dataclass(frozen=True)
class _ProviderDiscoveryContext:
    config: Mapping[str, Any]
    media_kind: str
    raw_query: str
    query: str
    language: str | None
    source_ids: Sequence[str]
    session: requests.Session | None


def discover_acquisition_candidates(
    *,
    media_kind: str,
    query: str,
    provider: str | None = None,
    language: str | None = None,
    limit: int = 20,
    source_ids: Sequence[str] | None = None,
    config: Mapping[str, Any] | None = None,
    session: requests.Session | None = None,
) -> AcquisitionDiscoveryResult:
    """Search configured lawful source providers and normalize candidates."""

    config = config or {}
    normalized_kind = _normalize_media_kind(media_kind)
    raw_query = (query or "").strip()
    normalized_query = _normalize_query(query)
    normalized_provider = _normalize_provider(provider)
    effective_limit = _normalize_limit(limit)
    policy_notes = [
        "Discovery results are candidates only; downloader handoff requires a reviewed acquisition step.",
        "Do not use acquisition providers for works you are not authorized to download or process.",
    ]
    if effective_limit <= 0:
        if normalized_provider is not None:
            _providers_for(normalized_kind, normalized_provider, config)
        return AcquisitionDiscoveryResult(
            candidates=(),
            policy_notes=tuple(policy_notes),
            providers_queried=(),
        )

    providers = _providers_for(normalized_kind, normalized_provider, config)
    is_default_provider_fanout = normalized_provider is None
    normalized_source_ids = (
        _normalize_source_ids(source_ids) if "internet_archive" in providers else ()
    )
    discovery_context = _ProviderDiscoveryContext(
        config=config,
        media_kind=normalized_kind,
        raw_query=raw_query,
        query=normalized_query,
        language=language,
        source_ids=normalized_source_ids,
        session=session,
    )

    candidates: list[AcquisitionCandidate] = []
    queried: list[str] = []
    for provider_id in providers:
        try:
            if not is_default_provider_fanout and len(candidates) >= effective_limit:
                break
            remaining = provider_query_limit(
                provider_id,
                candidates=candidates,
                effective_limit=effective_limit,
                is_default_provider_fanout=is_default_provider_fanout,
            )
            if remaining <= 0:
                continue
            provider_candidates = _discover_provider_candidates(
                provider_id,
                discovery_context,
                remaining,
            )
            queried.append(provider_id)
            candidates.extend(provider_candidates)
        except AcquisitionProviderDiscoveryError as exc:
            if not is_default_provider_fanout:
                raise
            if provider_id not in queried:
                queried.append(provider_id)
            policy_notes.append(_default_provider_failure_note(exc))
            continue

    ordered_candidates = (
        order_default_discovery_candidates(candidates, providers)
        if is_default_provider_fanout
        else candidates
    )
    return AcquisitionDiscoveryResult(
        candidates=tuple(ordered_candidates[:effective_limit]),
        policy_notes=tuple(policy_notes),
        providers_queried=tuple(queried),
    )


def _default_provider_failure_note(error: AcquisitionProviderDiscoveryError) -> str:
    return f"{error.provider} unavailable during Default sources: {error.public_message}"


def _providers_for(
    media_kind: str,
    provider: str | None,
    config: Mapping[str, Any],
) -> tuple[str, ...]:
    if provider:
        media_kinds = discovery_media_kinds_for(provider)
        if not media_kinds:
            raise ValueError(f"provider {provider} does not support discovery")
        if media_kind not in media_kinds:
            raise ValueError(
                f"provider {provider} does not support {media_kind} discovery"
            )
        return (provider,)
    return default_discovery_provider_ids(media_kind, config)


def _discover_provider_candidates(
    provider_id: str,
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    handler = _PROVIDER_DISCOVERY_HANDLERS.get(provider_id)
    if handler is None:
        return []
    return handler(context, limit)


def _discover_local_epub_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_local_epubs(context.config, context.query, limit)


def _discover_manual_download_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_manual_downloads(
        context.config,
        context.media_kind,
        context.query,
        limit,
    )


def _discover_gutenberg_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_gutenberg(
        context.query,
        limit,
        language=context.language,
        session=context.session,
    )


def _discover_internet_archive_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_internet_archive(
        context.query,
        limit,
        language=context.language,
        source_ids=context.source_ids,
        session=context.session,
    )


def _discover_openlibrary_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_openlibrary(
        context.query,
        limit,
        language=context.language,
        session=context.session,
    )


def _discover_nas_video_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_nas_videos(context.config, context.query, limit)


def _discover_newznab_torznab_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_newznab_torznab(
        context.config,
        context.query,
        limit,
        session=context.session,
    )


def _discover_youtube_url_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_youtube_url(context.raw_query, limit)


def _discover_youtube_search_candidates(
    context: _ProviderDiscoveryContext,
    limit: int,
) -> list[AcquisitionCandidate]:
    return _discover_youtube_search(
        context.config,
        context.query,
        limit,
        language=context.language,
        session=context.session,
    )


_PROVIDER_DISCOVERY_HANDLERS = {
    "local_epub": _discover_local_epub_candidates,
    "manual_downloads": _discover_manual_download_candidates,
    "gutenberg": _discover_gutenberg_candidates,
    "internet_archive": _discover_internet_archive_candidates,
    "openlibrary": _discover_openlibrary_candidates,
    "nas_video": _discover_nas_video_candidates,
    "newznab_torznab": _discover_newznab_torznab_candidates,
    "youtube_url": _discover_youtube_url_candidates,
    "youtube_search": _discover_youtube_search_candidates,
}
