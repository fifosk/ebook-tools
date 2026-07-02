"""Normalized source discovery for acquisition-backed Create flows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import requests

from .provider_registry import (
    default_discovery_provider_ids,
    discovery_media_kinds_for,
)
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
    providers = _providers_for(normalized_kind, normalized_provider, config)
    is_default_provider_fanout = normalized_provider is None
    normalized_source_ids = (
        _normalize_source_ids(source_ids) if "internet_archive" in providers else ()
    )

    candidates: list[AcquisitionCandidate] = []
    queried: list[str] = []
    policy_notes = [
        "Discovery results are candidates only; downloader handoff requires a reviewed acquisition step.",
        "Do not use acquisition providers for works you are not authorized to download or process.",
    ]
    if effective_limit <= 0:
        return AcquisitionDiscoveryResult(
            candidates=(),
            policy_notes=tuple(policy_notes),
            providers_queried=(),
        )
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
            if provider_id == "local_epub":
                queried.append(provider_id)
                candidates.extend(_discover_local_epubs(config, normalized_query, remaining))
            elif provider_id == "manual_downloads":
                queried.append(provider_id)
                candidates.extend(
                    _discover_manual_downloads(
                        config,
                        normalized_kind,
                        normalized_query,
                        remaining,
                    )
                )
            elif provider_id == "gutenberg":
                queried.append(provider_id)
                candidates.extend(
                    _discover_gutenberg(
                        normalized_query,
                        remaining,
                        language=language,
                        session=session,
                    )
                )
            elif provider_id == "internet_archive":
                queried.append(provider_id)
                candidates.extend(
                    _discover_internet_archive(
                        normalized_query,
                        remaining,
                        language=language,
                        source_ids=normalized_source_ids,
                        session=session,
                    )
                )
            elif provider_id == "openlibrary":
                queried.append(provider_id)
                candidates.extend(
                    _discover_openlibrary(
                        normalized_query,
                        remaining,
                        language=language,
                        session=session,
                    )
                )
            elif provider_id == "nas_video":
                queried.append(provider_id)
                candidates.extend(_discover_nas_videos(config, normalized_query, remaining))
            elif provider_id == "newznab_torznab":
                queried.append(provider_id)
                candidates.extend(
                    _discover_newznab_torznab(
                        config,
                        normalized_query,
                        remaining,
                        session=session,
                    )
                )
            elif provider_id == "youtube_url":
                queried.append(provider_id)
                candidates.extend(_discover_youtube_url(raw_query, remaining))
            elif provider_id == "youtube_search":
                queried.append(provider_id)
                candidates.extend(
                    _discover_youtube_search(
                        config,
                        normalized_query,
                        remaining,
                        language=language,
                        session=session,
                    )
                )
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
