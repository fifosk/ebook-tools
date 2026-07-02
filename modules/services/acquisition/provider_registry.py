"""Token-safe provider registry for discovery/acquisition surfaces."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from modules import config_manager as cfg

from .discovery_values import (
    ACQUISITION_CAPABILITIES,
    ACQUISITION_MEDIA_KINDS,
    ACQUISITION_PROVIDER_STATUSES,
    ACQUISITION_RIGHTS,
    unsupported_contract_values,
)
from .provider_catalog import (
    DISCOVERY_PROVIDER_MEDIA_KINDS,
    discovery_media_kinds_for,
    normalized_provider_id as _normalized_catalog_id,
)
from .provider_defaults import (
    default_discovery_provider_ids_from_readiness as _default_discovery_provider_ids_from_readiness,
    is_download_station_configured,
    is_indexer_search_configured,
    is_youtube_search_configured,
)
from .provider_roots import (
    DEFAULT_YOUTUBE_VIDEO_ROOT,
    is_readable_dir as _is_readable_dir,
    manual_download_source_label as _manual_download_source_label,
    readable_explicit_manual_download_roots as _readable_explicit_manual_download_roots,
    resolve_books_root,
    resolve_manual_download_roots,
    resolve_video_root,
)


def default_discovery_provider_ids(
    media_kind: str,
    config: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return providers searched when clients do not choose a provider."""

    config = config or {}
    media_kind = _normalized_catalog_id(media_kind)
    if media_kind not in ACQUISITION_MEDIA_KINDS:
        return ()
    return _resolve_provider_readiness(
        config=config,
        context=None,
    ).default_provider_ids.get(media_kind, ())


@dataclass(frozen=True)
class AcquisitionProvider:
    """Backend provider metadata safe to expose to clients."""

    id: str
    label: str
    media_kinds: tuple[str, ...]
    capabilities: tuple[str, ...]
    status: str
    configured: bool
    available: bool
    rights: tuple[str, ...]
    discovery_media_kinds: tuple[str, ...] = ()
    default_eligible_media_kinds: tuple[str, ...] = ()
    source_path: str | None = None
    source_label: str | None = None
    policy_notes: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Return a Pydantic-friendly representation."""

        payload: dict[str, object] = {
            "id": self.id,
            "label": self.label,
            "media_kinds": list(self.media_kinds),
            "capabilities": list(self.capabilities),
            "status": self.status,
            "configured": self.configured,
            "available": self.available,
            "rights": list(self.rights),
            "discovery_media_kinds": list(self.discovery_media_kinds),
            "default_eligible_media_kinds": list(self.default_eligible_media_kinds),
            "policy_notes": list(self.policy_notes),
            "next_actions": list(self.next_actions),
        }
        if self.source_path:
            payload["source_path"] = self.source_path
        if self.source_label:
            payload["source_label"] = self.source_label
        return payload


@dataclass(frozen=True)
class AcquisitionProviderRegistry:
    """Collection of acquisition providers and global policy metadata."""

    providers: tuple[AcquisitionProvider, ...]
    policy_notes: tuple[str, ...] = field(default_factory=tuple)
    paths: Mapping[str, str] = field(default_factory=dict)
    default_provider_ids: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return a serializable registry snapshot."""

        return {
            "providers": [provider.as_dict() for provider in self.providers],
            "policy_notes": list(self.policy_notes),
            "paths": dict(self.paths),
            "default_provider_ids": {
                media_kind: list(provider_ids)
                for media_kind, provider_ids in self.default_provider_ids.items()
            },
        }


@dataclass(frozen=True)
class _ProviderReadiness:
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


def list_acquisition_providers(
    *,
    config: Mapping[str, Any] | None = None,
    context: cfg.RuntimeContext | None = None,
) -> AcquisitionProviderRegistry:
    """Return token-safe provider metadata for Web and Apple Create."""

    config = config or {}
    readiness = _resolve_provider_readiness(config=config, context=context)

    providers = (
        AcquisitionProvider(
            id="local_epub",
            label="Local EPUB library",
            media_kinds=("book",),
            capabilities=("import_local", "metadata"),
            status="available" if readiness.books_root_readable else "not_configured",
            configured=True,
            available=readiness.books_root_readable,
            rights=("user_provided",),
            discovery_media_kinds=discovery_media_kinds_for("local_epub"),
            source_path=readiness.books_root.as_posix(),
            source_label="Books root",
            policy_notes=(
                "Uses backend-visible EPUB files under the configured books root.",
            ),
            next_actions=("prepare_epub_source", "create_book_job"),
        ),
        AcquisitionProvider(
            id="nas_video",
            label="NAS video library",
            media_kinds=("video",),
            capabilities=("import_local", "extract_subtitles", "metadata"),
            status="available" if readiness.video_root_readable else "not_configured",
            configured=True,
            available=readiness.video_root_readable,
            rights=("user_provided",),
            discovery_media_kinds=discovery_media_kinds_for("nas_video"),
            source_path=readiness.video_root.as_posix(),
            source_label="NAS video root",
            policy_notes=(
                "Uses downloaded or user-owned videos visible to the backend NAS scanner.",
            ),
            next_actions=("choose_video", "extract_subtitles", "create_dub_job"),
        ),
        AcquisitionProvider(
            id="manual_downloads",
            label="Manual download folders",
            media_kinds=("book", "video"),
            capabilities=("import_local", "extract_subtitles", "metadata"),
            status="available" if readiness.readable_manual_roots else "not_configured",
            configured=bool(readiness.manual_download_roots),
            available=bool(readiness.readable_manual_roots),
            rights=("user_provided",),
            discovery_media_kinds=discovery_media_kinds_for("manual_downloads"),
            source_path=(
                ";".join(root.as_posix() for root in readiness.readable_manual_roots)
                or None
            ),
            source_label=_manual_download_source_label(readiness.manual_download_roots),
            policy_notes=(
                "Scans configured backend-visible folders for user-authorized files already downloaded through Safari, Download Station, or another manual workflow.",
            ),
            next_actions=("review_rights", "import_local", "create_job"),
        ),
        AcquisitionProvider(
            id="youtube_url",
            label="YouTube URL",
            media_kinds=("video",),
            capabilities=("metadata", "acquire", "extract_subtitles"),
            status="available",
            configured=True,
            available=True,
            rights=("unknown", "restricted"),
            discovery_media_kinds=discovery_media_kinds_for("youtube_url"),
            policy_notes=(
                "Direct URL inspection reuses the existing yt-dlp workflow and must "
                "respect the user's rights and backend policy.",
            ),
            next_actions=("inspect_url", "choose_subtitle", "download_video"),
        ),
        AcquisitionProvider(
            id="youtube_search",
            label="YouTube search",
            media_kinds=("video",),
            capabilities=("search", "metadata"),
            status="available" if readiness.youtube_search_configured else "not_configured",
            configured=readiness.youtube_search_configured,
            available=readiness.youtube_search_configured,
            rights=("unknown", "restricted"),
            discovery_media_kinds=discovery_media_kinds_for("youtube_search"),
            policy_notes=(
                "Search uses the YouTube Data API when configured; acquisition remains "
                "a separate reviewed step.",
            ),
            next_actions=("search", "inspect_url"),
        ),
        AcquisitionProvider(
            id="download_station",
            label="Synology Download Station",
            media_kinds=("video",),
            capabilities=("acquire", "poll"),
            status="available" if readiness.download_station_configured else "not_configured",
            configured=readiness.download_station_configured,
            available=readiness.download_station_configured,
            rights=("unknown", "restricted"),
            policy_notes=(
                "Queue handoff is for lawful reviewed torrents, magnets, NZBs, or URLs only.",
                "Requires backend Download Station endpoint, account, and password configuration.",
            ),
            next_actions=("confirm_acquisition", "poll_download", "import_local"),
        ),
        AcquisitionProvider(
            id="newznab_torznab",
            label="Newznab/Torznab indexers",
            media_kinds=("video",),
            capabilities=("search", "metadata"),
            status="available" if readiness.indexer_search_configured else "not_configured",
            configured=readiness.indexer_search_configured,
            available=readiness.indexer_search_configured,
            rights=("unknown", "restricted"),
            discovery_media_kinds=discovery_media_kinds_for("newznab_torznab"),
            policy_notes=(
                "Indexer results are review-only until the user confirms a lawful acquisition.",
            ),
            next_actions=("search", "confirm_acquisition"),
        ),
        AcquisitionProvider(
            id="openlibrary",
            label="Open Library metadata",
            media_kinds=("book",),
            capabilities=("search", "metadata"),
            status="available",
            configured=True,
            available=True,
            rights=("unknown",),
            discovery_media_kinds=discovery_media_kinds_for("openlibrary"),
            policy_notes=(
                "Metadata-first book lookup; do not assume a downloadable EPUB is available.",
            ),
            next_actions=("search_metadata", "enrich_book"),
        ),
        AcquisitionProvider(
            id="zlibrary_attended",
            label="Z-Library attended import",
            media_kinds=("book",),
            capabilities=("import_local",),
            status="planned",
            configured=False,
            available=False,
            rights=("unknown", "restricted"),
            policy_notes=(
                "Direct Z-Library automation is intentionally disabled.",
                "Use an attended browser/download workflow only for books you are "
                "authorized to process, then import the EPUB through Manual downloads "
                "or the backend books folder.",
            ),
            next_actions=(
                "download_attended",
                "place_in_manual_downloads",
                "refresh_manual_downloads",
            ),
        ),
        AcquisitionProvider(
            id="gutenberg",
            label="Project Gutenberg/Gutendex",
            media_kinds=("book",),
            capabilities=("search", "metadata", "acquire"),
            status="available",
            configured=True,
            available=True,
            rights=("public_domain", "open_license"),
            discovery_media_kinds=discovery_media_kinds_for("gutenberg"),
            policy_notes=(
                "Searches the public Gutendex catalog for Project Gutenberg ebook metadata and EPUB links.",
            ),
            next_actions=("search", "review_rights", "download_epub", "create_book_job"),
        ),
        AcquisitionProvider(
            id="internet_archive",
            label="Internet Archive",
            media_kinds=("book",),
            capabilities=("search", "metadata", "acquire"),
            status="available",
            configured=True,
            available=True,
            rights=("public_domain", "open_license", "unknown"),
            discovery_media_kinds=discovery_media_kinds_for("internet_archive"),
            policy_notes=(
                "Searches public Internet Archive text items and only offers ordinary downloadable EPUB files with suitable access metadata.",
            ),
            next_actions=("search", "review_files", "download_epub", "create_book_job"),
        ),
    )
    providers = tuple(
        replace(
            provider,
            default_eligible_media_kinds=_default_eligible_media_kinds(
                provider.id,
                readiness.default_provider_ids,
            ),
        )
        for provider in providers
    )

    registry = AcquisitionProviderRegistry(
        providers=providers,
        policy_notes=(
            "Do not automate Z-Library or other shadow-library download workflows.",
            "Downloader and indexer providers require explicit user review and lawful authorization.",
            "Credentials and raw provider tokens stay server-side and are never returned by this endpoint.",
        ),
        paths={
            "books_root": readiness.books_root.as_posix(),
            "video_root": readiness.video_root.as_posix(),
            "manual_download_roots": os.pathsep.join(
                root.as_posix() for root in readiness.manual_download_roots
            ),
        },
        default_provider_ids=readiness.default_provider_ids,
    )
    _validate_provider_registry_contract(registry)
    return registry


def _resolve_provider_readiness(
    *,
    config: Mapping[str, Any],
    context: cfg.RuntimeContext | None = None,
) -> _ProviderReadiness:
    books_root = resolve_books_root(config=config, context=context)
    video_root = resolve_video_root(config)
    manual_download_roots = resolve_manual_download_roots(config)
    readable_manual_roots = tuple(
        root for root in manual_download_roots if _is_readable_dir(root)
    )
    readable_default_manual_roots = _readable_explicit_manual_download_roots(config)
    books_root_readable = _is_readable_dir(books_root)
    video_root_readable = _is_readable_dir(video_root)
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
    return _ProviderReadiness(
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


def _default_eligible_media_kinds(
    provider_id: str,
    default_provider_ids: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Return media kinds where provider may participate in default fan-out."""

    return tuple(
        media_kind
        for media_kind in ACQUISITION_MEDIA_KINDS
        if provider_id in default_provider_ids.get(media_kind, ())
    )


def _validate_provider_registry_contract(registry: AcquisitionProviderRegistry) -> None:
    """Fail fast when backend provider metadata drifts from public API enums."""

    provider_ids = {provider.id for provider in registry.providers}
    for provider in registry.providers:
        _ensure_provider_values(
            provider,
            field="media_kinds",
            values=provider.media_kinds,
            allowed_values=ACQUISITION_MEDIA_KINDS,
        )
        _ensure_provider_values(
            provider,
            field="capabilities",
            values=provider.capabilities,
            allowed_values=ACQUISITION_CAPABILITIES,
        )
        _ensure_provider_values(
            provider,
            field="rights",
            values=provider.rights,
            allowed_values=ACQUISITION_RIGHTS,
        )
        _ensure_provider_values(
            provider,
            field="discovery_media_kinds",
            values=provider.discovery_media_kinds,
            allowed_values=ACQUISITION_MEDIA_KINDS,
        )
        _ensure_provider_values(
            provider,
            field="default_eligible_media_kinds",
            values=provider.default_eligible_media_kinds,
            allowed_values=ACQUISITION_MEDIA_KINDS,
        )
        if provider.status not in ACQUISITION_PROVIDER_STATUSES:
            raise ValueError(
                "Unsupported acquisition provider status "
                f"{provider.status!r} for provider {provider.id!r}."
            )

    for media_kind, default_provider_ids in registry.default_provider_ids.items():
        if media_kind not in ACQUISITION_MEDIA_KINDS:
            raise ValueError(
                f"Unsupported acquisition default-provider media kind {media_kind!r}."
            )
        unknown_provider_ids = tuple(
            provider_id
            for provider_id in default_provider_ids
            if provider_id not in provider_ids
        )
        if unknown_provider_ids:
            raise ValueError(
                "Unknown acquisition default provider ids for "
                f"{media_kind!r}: {', '.join(unknown_provider_ids)}."
            )


def _ensure_provider_values(
    provider: AcquisitionProvider,
    *,
    field: str,
    values: tuple[str, ...],
    allowed_values: tuple[str, ...],
) -> None:
    unsupported = unsupported_contract_values(values, allowed_values=allowed_values)
    if unsupported:
        raise ValueError(
            f"Unsupported acquisition provider {field} values for "
            f"{provider.id!r}: {', '.join(unsupported)}."
        )
