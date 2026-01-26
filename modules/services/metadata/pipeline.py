"""Metadata lookup pipeline orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from modules import config_manager as cfg
from modules import logging_manager as log_mgr

from .types import (
    ConfidenceLevel,
    LookupOptions,
    LookupQuery,
    UnifiedMetadataResult,
)
from .registry import MetadataSourceRegistry, create_registry_from_config
from .cache import MetadataCache
from .normalization import merge_results, deduplicate_genres

logger = log_mgr.get_logger().getChild("services.metadata.pipeline")


class MetadataLookupPipeline:
    """Orchestrates multi-source metadata lookups with fallback.

    The pipeline:
    1. Checks cache if enabled
    2. Tries sources in order from the fallback chain
    3. Stops early on high confidence results or when all required fields are present
    4. Merges results from multiple sources
    5. Caches and returns the result
    """

    def __init__(
        self,
        registry: Optional[MetadataSourceRegistry] = None,
        cache: Optional[MetadataCache] = None,
        cache_enabled: bool = True,
    ) -> None:
        """Initialize the pipeline.

        Args:
            registry: Source registry to use. If None, creates from config.
            cache: Cache to use. If None, creates from config if enabled.
            cache_enabled: Whether to enable caching.
        """
        self._registry = registry or create_registry_from_config()
        self._cache = cache
        self._cache_enabled = cache_enabled

        # Initialize cache if not provided but enabled
        if self._cache is None and cache_enabled:
            self._cache = self._create_cache_from_config()

    def _create_cache_from_config(self) -> Optional[MetadataCache]:
        """Create cache from configuration."""
        try:
            settings = cfg.get_settings()
            metadata_config = getattr(settings, "metadata_lookup", {}) or {}
            if not metadata_config.get("cache_enabled", True):
                return None

            cache_dir = metadata_config.get("cache_dir", "storage/cache/metadata")
            cache_path = cfg.resolve_directory(None, cache_dir)
            ttl_hours = metadata_config.get("cache_ttl_hours", 168)

            return MetadataCache(cache_dir=cache_path, ttl_hours=ttl_hours)
        except Exception as exc:
            logger.warning("Failed to create metadata cache: %s", exc)
            return None

    def lookup(
        self,
        query: LookupQuery,
        options: Optional[LookupOptions] = None,
    ) -> Optional[UnifiedMetadataResult]:
        """Execute a metadata lookup across configured sources.

        Args:
            query: The lookup query.
            options: Options controlling lookup behavior.

        Returns:
            A UnifiedMetadataResult if found, None otherwise.
        """
        opts = options or LookupOptions()

        # Check cache
        if self._cache and not opts.skip_cache and not opts.force_refresh:
            cached = self._cache.get(query)
            if cached is not None:
                logger.debug("Cache hit for %s", query.title or query.isbn or query.youtube_video_id)
                return cached

        # Get available sources for this media type
        available_sources = self._registry.get_available_sources(query.media_type)
        logger.info("Available sources for %s: %s", query.media_type.value, [s.value for s in available_sources])
        if not available_sources:
            logger.warning("No available sources for media type %s", query.media_type)
            return None

        results: list[UnifiedMetadataResult] = []
        primary_source = None

        for source in available_sources:
            if len(results) >= opts.max_sources:
                logger.debug("Reached max sources (%d), stopping chain", opts.max_sources)
                break

            client = self._registry.get_client(source)
            if client is None:
                continue

            logger.info(
                "Querying %s for %s",
                source.value,
                query.title or query.isbn or query.youtube_video_id or "unknown",
            )

            try:
                result = client.lookup(query, opts)
            except Exception as exc:
                logger.warning("Source %s failed: %s", source.value, exc)
                continue

            if result is None:
                logger.debug("Source %s returned no results", source.value)
                continue

            # Skip error results from this source
            if result.error and not result.title:
                logger.debug("Source %s returned error: %s", source.value, result.error)
                continue

            results.append(result)
            if primary_source is None:
                primary_source = source

            logger.info(
                "Source %s returned: title=%s, genres=%s, has_required=%s",
                source.value,
                result.title,
                result.genres[:3] if result.genres else [],
                result.has_required_fields(),
            )

            # Check if we have all required fields (title, year, genres, summary, cover)
            # This takes precedence over confidence level to ensure we get complete metadata
            if result.has_required_fields():
                logger.debug("All required fields found after %s", source.value)
                break

            # Only stop on high confidence if we also have required fields
            # Otherwise continue to fill missing fields from fallback sources
            if result.confidence == ConfidenceLevel.HIGH:
                logger.info(
                    "High confidence result from %s but missing fields, continuing to fallbacks",
                    source.value,
                )

        if not results:
            logger.info("No results found from any source")
            return None

        # Merge results
        merged = merge_results(results)
        merged.primary_source = primary_source
        merged.contributing_sources = [r.primary_source for r in results if r.primary_source]
        merged.queried_at = datetime.now(timezone.utc)

        # Post-process
        merged.genres = deduplicate_genres(merged.genres)

        logger.info(
            "Merged result: title=%s, genres=%s, sources=%s",
            merged.title,
            merged.genres[:5] if merged.genres else [],
            [s.value for s in merged.contributing_sources],
        )

        # Cache result
        if self._cache and not opts.skip_cache:
            try:
                self._cache.set(query, merged)
            except Exception as exc:
                logger.warning("Failed to cache result: %s", exc)

        return merged

    def lookup_with_fallback(
        self,
        query: LookupQuery,
        options: Optional[LookupOptions] = None,
    ) -> UnifiedMetadataResult:
        """Execute lookup with guaranteed result (fallback to empty).

        Args:
            query: The lookup query.
            options: Options controlling lookup behavior.

        Returns:
            A UnifiedMetadataResult (may have error set if lookup failed).
        """
        result = self.lookup(query, options)
        if result is not None:
            return result

        # Return empty result with error
        return UnifiedMetadataResult(
            title=query.title or query.movie_title or query.series_name or "Unknown",
            type=query.media_type,
            confidence=ConfidenceLevel.LOW,
            queried_at=datetime.now(timezone.utc),
            error="No metadata found from any source",
        )

    def invalidate_cache(self, query: LookupQuery) -> bool:
        """Invalidate cached result for a query.

        Args:
            query: The lookup query.

        Returns:
            True if entry was deleted, False otherwise.
        """
        if self._cache:
            return self._cache.delete(query)
        return False

    def clear_cache(self) -> int:
        """Clear all cached results.

        Returns:
            Number of entries deleted.
        """
        if self._cache:
            return self._cache.clear()
        return 0

    def close(self) -> None:
        """Release resources."""
        self._registry.close()

    def __enter__(self) -> "MetadataLookupPipeline":
        return self

    def __exit__(self, *args) -> None:
        self.close()


def create_pipeline(
    api_keys: Optional[dict] = None,
    cache_enabled: bool = True,
) -> MetadataLookupPipeline:
    """Create a configured metadata lookup pipeline.

    Args:
        api_keys: Optional API keys to use. If None, loads from config.
        cache_enabled: Whether to enable caching.

    Returns:
        Configured MetadataLookupPipeline.
    """
    # Use the registry's config-aware factory which properly reads flat API key settings
    if api_keys is None:
        registry = create_registry_from_config()
    else:
        registry = MetadataSourceRegistry(api_keys=api_keys)

    # Create cache if enabled
    cache = None
    if cache_enabled:
        try:
            settings = cfg.get_settings()
            metadata_config = getattr(settings, "metadata_lookup", {}) or {}
            cache_dir = metadata_config.get("cache_dir", "storage/cache/metadata")
            cache_path = cfg.resolve_directory(None, cache_dir)
            ttl_hours = metadata_config.get("cache_ttl_hours", 168)
            cache = MetadataCache(cache_dir=cache_path, ttl_hours=ttl_hours)
        except Exception:
            pass

    return MetadataLookupPipeline(registry=registry, cache=cache, cache_enabled=cache_enabled)


__all__ = [
    "MetadataLookupPipeline",
    "create_pipeline",
]
