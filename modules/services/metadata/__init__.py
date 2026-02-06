"""Unified metadata lookup pipeline for books, movies, TV series, and YouTube videos."""

from __future__ import annotations

from .types import (
    ConfidenceLevel,
    LookupOptions,
    LookupQuery,
    MediaType,
    MetadataSource,
    SeriesInfo,
    SourceIds,
    UnifiedMetadataResult,
)
from .cache import MetadataCache
from .registry import MetadataSourceRegistry, create_registry_from_config
from .pipeline import MetadataLookupPipeline, create_pipeline
from .normalization import merge_results, deduplicate_genres
from .enrichment import (
    EnrichmentResult,
    detect_media_type,
    enrich_media_metadata,
    enrich_metadata,
    enrich_movie_metadata,
    enrich_tv_metadata,
)
from .structured_schema import StructuredMediaMetadata
from .structured_conversion import (
    detect_metadata_version,
    flatten_to_dict,
    normalize_media_metadata,
    structure_from_flat,
)

__all__ = [
    # Types
    "ConfidenceLevel",
    "LookupOptions",
    "LookupQuery",
    "MediaType",
    "MetadataSource",
    "SeriesInfo",
    "SourceIds",
    "UnifiedMetadataResult",
    # Cache
    "MetadataCache",
    # Registry
    "MetadataSourceRegistry",
    "create_registry_from_config",
    # Pipeline
    "MetadataLookupPipeline",
    "create_pipeline",
    # Normalization
    "merge_results",
    "deduplicate_genres",
    # Enrichment
    "EnrichmentResult",
    "detect_media_type",
    "enrich_media_metadata",
    "enrich_metadata",
    "enrich_movie_metadata",
    "enrich_tv_metadata",
    # Structured metadata
    "StructuredMediaMetadata",
    "detect_metadata_version",
    "flatten_to_dict",
    "normalize_media_metadata",
    "structure_from_flat",
]
