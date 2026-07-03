"""Resolve acquisition provider source readiness without building payloads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from modules import config_manager as cfg

from .discovery_values import ACQUISITION_MEDIA_KINDS
from .provider_catalog import normalized_provider_id as _normalized_catalog_id
from .provider_defaults import (
    default_discovery_provider_ids_from_readiness as _default_discovery_provider_ids_from_readiness,
    is_download_station_configured,
    is_indexer_search_configured,
    is_youtube_search_configured,
)
from .provider_roots import (
    is_readable_dir as _is_readable_dir,
    readable_explicit_manual_download_roots as _readable_explicit_manual_download_roots,
    resolve_books_root,
    resolve_manual_download_roots,
    resolve_video_root,
)


@dataclass(frozen=True)
class ProviderReadiness:
    """Resolved source roots and provider readiness for one registry request."""

    books_root: Path
    video_root: Path
    manual_download_roots: tuple[Path, ...]
    readable_manual_roots: tuple[Path, ...]
    readable_default_manual_roots: tuple[Path, ...]
    books_root_readable: bool
    video_root_readable: bool
    youtube_search_configured: bool
    download_station_configured: bool
    indexer_search_configured: bool
    default_provider_ids: Mapping[str, tuple[str, ...]]


def resolve_provider_readiness(
    *,
    config: Mapping[str, Any],
    context: cfg.RuntimeContext | None = None,
    is_readable_dir: Callable[[Path], bool] | None = None,
) -> ProviderReadiness:
    """Resolve readable roots and configured remote providers once per request."""

    readable = is_readable_dir or _is_readable_dir
    books_root = resolve_books_root(config=config, context=context)
    video_root = resolve_video_root(config)
    manual_download_roots = resolve_manual_download_roots(config)
    readable_manual_roots = tuple(
        root for root in manual_download_roots if readable(root)
    )
    readable_default_manual_roots = _readable_explicit_manual_download_roots(config)
    books_root_readable = readable(books_root)
    video_root_readable = readable(video_root)
    youtube_search_configured = is_youtube_search_configured(config)
    download_station_configured = is_download_station_configured(config)
    indexer_search_configured = is_indexer_search_configured(config)
    default_provider_ids = {
        media_kind: _default_discovery_provider_ids_from_readiness(
            media_kind,
            books_root_readable=books_root_readable,
            video_root_readable=video_root_readable,
            has_readable_manual_roots=bool(readable_default_manual_roots),
            youtube_search_configured=youtube_search_configured,
            indexer_search_configured=indexer_search_configured,
        )
        for media_kind in ACQUISITION_MEDIA_KINDS
    }
    return ProviderReadiness(
        books_root=books_root,
        video_root=video_root,
        manual_download_roots=manual_download_roots,
        readable_manual_roots=readable_manual_roots,
        readable_default_manual_roots=readable_default_manual_roots,
        books_root_readable=books_root_readable,
        video_root_readable=video_root_readable,
        youtube_search_configured=youtube_search_configured,
        download_station_configured=download_station_configured,
        indexer_search_configured=indexer_search_configured,
        default_provider_ids=default_provider_ids,
    )


def default_discovery_provider_ids_from_config(
    media_kind: str,
    config: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return configured default provider fan-out for one media kind."""

    config = config or {}
    normalized_media_kind = _normalized_catalog_id(media_kind)
    if normalized_media_kind not in ACQUISITION_MEDIA_KINDS:
        return ()
    return resolve_provider_readiness(
        config=config,
        context=None,
    ).default_provider_ids.get(normalized_media_kind, ())
