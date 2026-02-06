"""Convert between flat media_metadata dicts and StructuredMediaMetadata.

Two entry points:

* ``structure_from_flat(flat)`` — upgrade a legacy flat dict to structured form.
* ``flatten_to_dict(structured)`` — downgrade back to flat for backward compat.
* ``normalize_media_metadata(payload)`` — auto-detect version and normalise.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from .enrichment import detect_media_type
from .structured_schema import (
    ContentStructure,
    CoverAssets,
    EnrichmentProvenance,
    LanguageConfig,
    SeriesInfoSchema,
    SourceIdsSchema,
    SourceMetadata,
    StructuredMediaMetadata,
    YouTubeInfoSchema,
)

# ---------------------------------------------------------------------------
# Field mapping tables: flat key → (section, structured_key)
# ---------------------------------------------------------------------------

# Source identity
_SOURCE_FIELD_MAP: Dict[str, str] = {
    "book_title": "title",
    "book_author": "author",
    "book_year": "year",
    "book_summary": "summary",
    "book_genre": "_genre_single",  # special: maps to genres[0]
    "book_genres": "genres",
    "isbn": "isbn",
    "isbn_13": "isbn_13",
    "book_language": "language",
    "runtime_minutes": "runtime_minutes",
    "rating": "rating",
    "votes": "votes",
}

# Language / translation config
_LANGUAGE_FIELD_MAP: Dict[str, str] = {
    "input_language": "input_language",
    "original_language": "original_language",
    "target_language": "target_language",
    "target_languages": "target_languages",
    "translation_language": "_alias_target_language",  # synonym for target_language
    "translation_provider": "translation_provider",
    "translation_model": "translation_model",
    "translation_model_requested": "translation_model_requested",
    "transliteration_mode": "transliteration_mode",
    "transliteration_model": "transliteration_model",
    "transliteration_module": "transliteration_module",
}

# Content structure
_CONTENT_FIELD_MAP: Dict[str, str] = {
    "total_sentences": "total_sentences",
    "book_sentence_count": "_alias_total_sentences",  # synonym
    "content_index_path": "content_index_path",
    "content_index_url": "content_index_url",
    "content_index_summary": "content_index_summary",
}

# Cover assets
_COVER_FIELD_MAP: Dict[str, str] = {
    "book_cover_file": "cover_file",
    "cover_url": "cover_url",
    "book_cover_url": "book_cover_url",
    "job_cover_asset": "job_cover_asset",
    "job_cover_asset_url": "job_cover_asset_url",
}

# Enrichment provenance
_ENRICHMENT_FIELD_MAP: Dict[str, str] = {
    "_enrichment_source": "source",
    "_enrichment_confidence": "confidence",
    "metadata_queried_at": "queried_at",
    "media_metadata_lookup": "lookup_result",
    "book_metadata_lookup": "_alias_lookup_result",  # legacy alias
}

# Source IDs (stored flat in enrichment or sometimes at top level)
_SOURCE_ID_FLAT_KEYS: Dict[str, str] = {
    "openlibrary_work_key": "openlibrary",
    "openlibrary_work_url": "_skip",  # URL, not ID — don't map
    "openlibrary_book_key": "openlibrary_book",
    "openlibrary_book_url": "_skip",
    "google_books_id": "google_books",
    "tmdb_id": "tmdb",
    "imdb_id": "imdb",
    "tvmaze_show_id": "tvmaze_show",
    "tvmaze_episode_id": "tvmaze_episode",
    "wikidata_qid": "wikidata",
    "youtube_video_id": "youtube_video",
    "youtube_channel_id": "youtube_channel",
}

# TV series fields (flat → SeriesInfoSchema)
_SERIES_FLAT_KEYS: Dict[str, str] = {
    "series_name": "series_title",
    "series_title": "series_title",
    "season": "season",
    "episode": "episode",
    "episode_title": "episode_title",
    "series_id": "series_id",
    "episode_id": "episode_id",
}

# YouTube fields (flat → YouTubeInfoSchema)
_YOUTUBE_FLAT_KEYS: Dict[str, str] = {
    "youtube_video_id": "video_id",
    "youtube_channel_id": "channel_id",
    "youtube_channel_name": "channel_name",
    "channel_name": "channel_name",
    "youtube_upload_date": "upload_date",
    "upload_date": "upload_date",
}

# Top-level keys that don't belong to any section
_TOP_LEVEL_KEYS: Dict[str, str] = {
    "job_label": "job_label",
}

# Collect all known flat keys for extras detection
_ALL_KNOWN_FLAT_KEYS: set[str] = set()
for _m in (
    _SOURCE_FIELD_MAP,
    _LANGUAGE_FIELD_MAP,
    _CONTENT_FIELD_MAP,
    _COVER_FIELD_MAP,
    _ENRICHMENT_FIELD_MAP,
    _SOURCE_ID_FLAT_KEYS,
    _SERIES_FLAT_KEYS,
    _YOUTUBE_FLAT_KEYS,
    _TOP_LEVEL_KEYS,
):
    _ALL_KNOWN_FLAT_KEYS.update(_m.keys())
# Also skip the content_index inline object (written to separate file)
_ALL_KNOWN_FLAT_KEYS.add("content_index")
# Skip keys that are processing config (belong in JobParameterSnapshot)
_PROCESSING_CONFIG_KEYS = {
    "add_images",
    "audio_mode",
    "selected_voice",
    "tempo",
    "sentences_per_output_file",
    "enable_lookup_cache",
    "lookup_cache_batch_size",
    "audio_bitrate_kbps",
    "stitch_full",
    "show",
    "enable_transliteration",
    "translation_batch_size",
    "input_file",
    "base_output_file",
}
_ALL_KNOWN_FLAT_KEYS.update(_PROCESSING_CONFIG_KEYS)


# ---------------------------------------------------------------------------
# Flat → Structured
# ---------------------------------------------------------------------------


def _safe_int(value: Any) -> Optional[int]:
    """Coerce a value to int or return None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> Optional[float]:
    """Coerce a value to float or return None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_series_info(flat: Mapping[str, Any]) -> Optional[SeriesInfoSchema]:
    """Extract TV series info from flat metadata."""
    data: Dict[str, Any] = {}
    for flat_key, schema_key in _SERIES_FLAT_KEYS.items():
        val = flat.get(flat_key)
        if val is not None:
            data[schema_key] = val
    if not data:
        return None
    return SeriesInfoSchema(**data)


def _extract_youtube_info(flat: Mapping[str, Any]) -> Optional[YouTubeInfoSchema]:
    """Extract YouTube info from flat metadata."""
    data: Dict[str, Any] = {}
    for flat_key, schema_key in _YOUTUBE_FLAT_KEYS.items():
        val = flat.get(flat_key)
        if val is not None:
            data[schema_key] = val
    if not data:
        return None
    return YouTubeInfoSchema(**data)


def _extract_source_ids(flat: Mapping[str, Any]) -> Optional[SourceIdsSchema]:
    """Extract external source IDs from flat metadata."""
    data: Dict[str, Any] = {}
    for flat_key, schema_key in _SOURCE_ID_FLAT_KEYS.items():
        if schema_key == "_skip":
            continue
        val = flat.get(flat_key)
        if val is not None:
            data[schema_key] = val
    if not data:
        return None
    return SourceIdsSchema(**data)


def structure_from_flat(flat: Mapping[str, Any]) -> StructuredMediaMetadata:
    """Convert a legacy flat media_metadata dict to structured form.

    Unknown keys are preserved in the ``extras`` field so no data is lost
    during round-trip conversion.
    """
    # --- Media type detection (reuse enrichment.detect_media_type) ---
    media_type = detect_media_type(flat).value

    # --- Source ---
    source_data: Dict[str, Any] = {}
    for flat_key, schema_key in _SOURCE_FIELD_MAP.items():
        val = flat.get(flat_key)
        if val is None:
            continue
        if schema_key == "_genre_single":
            # book_genre → genres[0] (only if genres not already set)
            if "genres" not in source_data:
                source_data["genres"] = [val] if isinstance(val, str) else list(val)
        else:
            source_data[schema_key] = val

    # Coerce year to int
    if "year" in source_data:
        source_data["year"] = _safe_int(source_data["year"])
    if "runtime_minutes" in source_data:
        source_data["runtime_minutes"] = _safe_int(source_data["runtime_minutes"])
    if "rating" in source_data:
        source_data["rating"] = _safe_float(source_data["rating"])
    if "votes" in source_data:
        source_data["votes"] = _safe_int(source_data["votes"])

    # TV series / YouTube nested objects
    series_info = _extract_series_info(flat)
    if series_info is not None:
        source_data["series"] = series_info
    youtube_info = _extract_youtube_info(flat)
    if youtube_info is not None:
        source_data["youtube"] = youtube_info

    source = SourceMetadata(**source_data)

    # --- Language config ---
    lang_data: Dict[str, Any] = {}
    for flat_key, schema_key in _LANGUAGE_FIELD_MAP.items():
        val = flat.get(flat_key)
        if val is None:
            continue
        if schema_key == "_alias_target_language":
            lang_data.setdefault("target_language", val)
        else:
            lang_data[schema_key] = val
    language_config = LanguageConfig(**lang_data)

    # --- Content structure ---
    content_data: Dict[str, Any] = {}
    for flat_key, schema_key in _CONTENT_FIELD_MAP.items():
        val = flat.get(flat_key)
        if val is None:
            continue
        if schema_key == "_alias_total_sentences":
            content_data.setdefault("total_sentences", _safe_int(val))
        else:
            if schema_key == "total_sentences":
                content_data[schema_key] = _safe_int(val)
            else:
                content_data[schema_key] = val
    content_structure = ContentStructure(**content_data)

    # --- Cover assets ---
    cover_data: Dict[str, Any] = {}
    for flat_key, schema_key in _COVER_FIELD_MAP.items():
        val = flat.get(flat_key)
        if val is not None:
            cover_data[schema_key] = val
    cover_assets = CoverAssets(**cover_data)

    # --- Enrichment provenance ---
    enrichment_data: Dict[str, Any] = {}
    for flat_key, schema_key in _ENRICHMENT_FIELD_MAP.items():
        val = flat.get(flat_key)
        if val is None:
            continue
        if schema_key == "_alias_lookup_result":
            enrichment_data.setdefault("lookup_result", val)
        else:
            enrichment_data[schema_key] = val
    source_ids = _extract_source_ids(flat)
    if source_ids is not None:
        enrichment_data["source_ids"] = source_ids
    enrichment = EnrichmentProvenance(**enrichment_data)

    # --- Top-level ---
    job_label = flat.get("job_label")

    # --- Extras (unmapped keys) ---
    extras: Dict[str, Any] = {}
    for key, val in flat.items():
        if key not in _ALL_KNOWN_FLAT_KEYS:
            extras[key] = val

    return StructuredMediaMetadata(
        metadata_version=2,
        media_type=media_type,
        source=source,
        language_config=language_config,
        content_structure=content_structure,
        cover_assets=cover_assets,
        enrichment=enrichment,
        job_label=job_label,
        extras=extras,
    )


# ---------------------------------------------------------------------------
# Structured → Flat
# ---------------------------------------------------------------------------

# Reverse maps: structured_field → flat_key (canonical, not aliases)
_SOURCE_REVERSE: Dict[str, str] = {
    "title": "book_title",
    "author": "book_author",
    "year": "book_year",
    "summary": "book_summary",
    "genres": "book_genres",
    "language": "book_language",
    "isbn": "isbn",
    "isbn_13": "isbn_13",
    "runtime_minutes": "runtime_minutes",
    "rating": "rating",
    "votes": "votes",
}

_LANGUAGE_REVERSE: Dict[str, str] = {
    "input_language": "input_language",
    "original_language": "original_language",
    "target_language": "target_language",
    "target_languages": "target_languages",
    "translation_provider": "translation_provider",
    "translation_model": "translation_model",
    "translation_model_requested": "translation_model_requested",
    "transliteration_mode": "transliteration_mode",
    "transliteration_model": "transliteration_model",
    "transliteration_module": "transliteration_module",
}

_CONTENT_REVERSE: Dict[str, str] = {
    "total_sentences": "total_sentences",
    "content_index_path": "content_index_path",
    "content_index_url": "content_index_url",
    "content_index_summary": "content_index_summary",
}

_COVER_REVERSE: Dict[str, str] = {
    "cover_file": "book_cover_file",
    "cover_url": "cover_url",
    "book_cover_url": "book_cover_url",
    "job_cover_asset": "job_cover_asset",
    "job_cover_asset_url": "job_cover_asset_url",
}

_ENRICHMENT_REVERSE: Dict[str, str] = {
    "source": "_enrichment_source",
    "confidence": "_enrichment_confidence",
    "queried_at": "metadata_queried_at",
    "lookup_result": "media_metadata_lookup",
}

_SOURCE_ID_REVERSE: Dict[str, str] = {
    "isbn": "isbn",  # also in source — skip to avoid duplication
    "isbn_13": "isbn_13",
    "openlibrary": "openlibrary_work_key",
    "openlibrary_book": "openlibrary_book_key",
    "google_books": "google_books_id",
    "tmdb": "tmdb_id",
    "imdb": "imdb_id",
    "tvmaze_show": "tvmaze_show_id",
    "tvmaze_episode": "tvmaze_episode_id",
    "wikidata": "wikidata_qid",
    "youtube_video": "youtube_video_id",
    "youtube_channel": "youtube_channel_id",
}

_SERIES_REVERSE: Dict[str, str] = {
    "series_title": "series_name",
    "season": "season",
    "episode": "episode",
    "episode_title": "episode_title",
    "series_id": "series_id",
    "episode_id": "episode_id",
}

_YOUTUBE_REVERSE: Dict[str, str] = {
    "video_id": "youtube_video_id",
    "channel_id": "youtube_channel_id",
    "channel_name": "channel_name",
    "upload_date": "upload_date",
}


def _dump_section(model: Any, reverse_map: Dict[str, str], out: Dict[str, Any]) -> None:
    """Dump a pydantic model's fields to flat dict using a reverse map."""
    if model is None:
        return
    data = model.model_dump(exclude_none=True) if hasattr(model, "model_dump") else {}
    for field_name, flat_key in reverse_map.items():
        val = data.get(field_name)
        if val is not None:
            out[flat_key] = val


def flatten_to_dict(structured: StructuredMediaMetadata) -> Dict[str, Any]:
    """Convert structured metadata back to a flat dict.

    This is the inverse of :func:`structure_from_flat` and is used
    for backward compatibility with code that reads the flat format.
    """
    flat: Dict[str, Any] = {}

    # Source
    _dump_section(structured.source, _SOURCE_REVERSE, flat)
    # Handle book_genre (singular) from genres list
    source_dump = structured.source.model_dump(exclude_none=True)
    genres = source_dump.get("genres")
    if isinstance(genres, list) and genres:
        flat["book_genre"] = genres[0]
        flat["book_genres"] = genres

    # Convert year back to string (legacy format)
    if "book_year" in flat and flat["book_year"] is not None:
        flat["book_year"] = str(flat["book_year"])

    # Series info
    if structured.source.series is not None:
        _dump_section(structured.source.series, _SERIES_REVERSE, flat)

    # YouTube info
    if structured.source.youtube is not None:
        _dump_section(structured.source.youtube, _YOUTUBE_REVERSE, flat)

    # Language config
    _dump_section(structured.language_config, _LANGUAGE_REVERSE, flat)

    # Content structure
    _dump_section(structured.content_structure, _CONTENT_REVERSE, flat)
    # Also write book_sentence_count as alias
    if "total_sentences" in flat:
        flat["book_sentence_count"] = flat["total_sentences"]

    # Cover assets
    _dump_section(structured.cover_assets, _COVER_REVERSE, flat)

    # Enrichment
    _dump_section(structured.enrichment, _ENRICHMENT_REVERSE, flat)

    # Source IDs from enrichment
    if structured.enrichment.source_ids is not None:
        ids_data = structured.enrichment.source_ids.model_dump(exclude_none=True)
        for schema_key, flat_key in _SOURCE_ID_REVERSE.items():
            val = ids_data.get(schema_key)
            if val is not None and flat_key not in flat:
                flat[flat_key] = val

    # Top-level
    if structured.job_label is not None:
        flat["job_label"] = structured.job_label

    # Extras (unknown keys preserved from original flat dict)
    flat.update(structured.extras)

    return flat


# ---------------------------------------------------------------------------
# Public normalisation entry point
# ---------------------------------------------------------------------------


def detect_metadata_version(payload: Mapping[str, Any]) -> int:
    """Detect metadata format version.

    Returns 2 if the payload has ``metadataVersion`` or ``metadata_version``
    key with value >= 2, otherwise 1 (legacy flat).
    """
    version = payload.get("metadataVersion") or payload.get("metadata_version")
    try:
        return int(version) if version is not None else 1
    except (TypeError, ValueError):
        return 1


def normalize_media_metadata(payload: Mapping[str, Any]) -> StructuredMediaMetadata:
    """Auto-detect version and return a :class:`StructuredMediaMetadata`.

    * v2+ payloads are validated directly via Pydantic.
    * v1 (flat) payloads are converted via :func:`structure_from_flat`.
    """
    version = detect_metadata_version(payload)
    if version >= 2:
        return StructuredMediaMetadata.model_validate(payload)
    return structure_from_flat(payload)


__all__ = [
    "detect_metadata_version",
    "flatten_to_dict",
    "normalize_media_metadata",
    "structure_from_flat",
]
