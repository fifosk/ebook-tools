"""Lookup cache building phase for the pipeline."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

print("[LOOKUP_CACHE_MODULE] Module loaded!", flush=True)  # This prints at import time

from ... import logging_manager as log_mgr
from ...lookup_cache import LookupCacheManager

if TYPE_CHECKING:
    from ..pipeline_service import PipelineRequest
    from ..pipeline_types import ConfigPhaseResult, RenderResult
    from ...progress_tracker import ProgressTracker

logger = log_mgr.logger


def _load_chunk_metadata(job_dir: Path, metadata_path: str) -> Optional[Dict[str, Any]]:
    """Load chunk metadata from file.

    Args:
        job_dir: Job directory path.
        metadata_path: Relative path to chunk metadata file.

    Returns:
        Chunk metadata dict or None if file doesn't exist.
    """
    chunk_file = job_dir / metadata_path
    if not chunk_file.exists():
        return None
    try:
        with open(chunk_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to load chunk metadata %s: %s", chunk_file, exc)
        return None


def build_lookup_cache_phase(
    request: "PipelineRequest",
    config_result: "ConfigPhaseResult",
    render_result: "RenderResult",
    tracker: Optional["ProgressTracker"],
) -> Optional[Path]:
    """Build the lookup cache for the completed job.

    Extracts unique words from translated sentences and looks up their
    definitions in batch, storing results as job metadata.

    Args:
        request: Pipeline request with inputs and settings.
        config_result: Configuration phase result.
        render_result: Rendering phase result with output directory.
        tracker: Progress tracker with generated chunks.

    Returns:
        Path to the lookup cache file if built, None otherwise.
    """
    # Check if lookup cache is enabled
    enable_cache = getattr(request.inputs, "enable_lookup_cache", True)
    # FORCE VISIBLE LOG - use print AND logger.error (error level to ensure it's logged)
    print(f"[LOOKUP_CACHE] Phase called: job_id={request.job_id}, enable_cache={enable_cache}", flush=True)
    logger.error(f"[LOOKUP_CACHE] Phase called: job_id={request.job_id}, enable_cache={enable_cache}")
    logger.info(
        "Lookup cache phase starting",
        extra={
            "event": "lookup_cache.phase.start",
            "attributes": {"enable_cache": enable_cache, "job_id": request.job_id},
        },
    )
    if not enable_cache:
        logger.debug("Lookup cache disabled; skipping build")
        return None

    # Get the base directory from render result
    base_dir = render_result.base_dir
    logger.debug("Lookup cache: base_dir=%s", base_dir)
    if not base_dir:
        logger.debug("No base directory; skipping lookup cache build")
        return None

    # Determine job directory (parent of media directory)
    base_path = Path(base_dir)
    job_dir: Optional[Path] = None
    for parent in [base_path] + list(base_path.parents):
        if parent.name.lower() == "media" and parent.parent != parent:
            job_dir = parent.parent
            break
    if job_dir is None:
        # Fallback: assume base_dir is inside job_dir/media/...
        job_dir = base_path.parent.parent if base_path.parent.name else base_path.parent
    logger.debug("Lookup cache: job_dir=%s, exists=%s", job_dir, job_dir.exists() if job_dir else False)
    if not job_dir.exists():
        logger.debug("Job directory not found; skipping lookup cache build")
        return None

    # Collect translated sentences from progress tracker
    if tracker is None:
        logger.debug("No progress tracker; skipping lookup cache build")
        return None

    generated_files = tracker.get_generated_files()
    chunks = generated_files.get("chunks", [])
    if not isinstance(chunks, list):
        logger.debug("No chunks in generated files; skipping lookup cache build")
        return None

    # Extract sentences from chunk metadata files
    all_sentences: List[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue

        # Try to get sentences directly from chunk (in-memory during pipeline)
        sentences = chunk.get("sentences", [])
        if isinstance(sentences, list) and sentences:
            for sentence_entry in sentences:
                if not isinstance(sentence_entry, dict):
                    continue
                # Get the TRANSLATION text (this is what we want to cache lookups for)
                # Handle both string and dict formats: {"text": "...", "tokens": [...]}
                translation = sentence_entry.get("translation") or sentence_entry.get("text") or ""
                if isinstance(translation, dict):
                    translation = translation.get("text", "")
                if translation and isinstance(translation, str):
                    all_sentences.append(translation.strip())
            continue

        # Fallback: load sentences from chunk metadata file on disk
        metadata_path = chunk.get("metadata_path")
        if not metadata_path:
            continue

        chunk_metadata = _load_chunk_metadata(job_dir, metadata_path)
        if chunk_metadata is None:
            continue

        sentences = chunk_metadata.get("sentences", [])
        if not isinstance(sentences, list):
            continue

        for sentence_entry in sentences:
            if not isinstance(sentence_entry, dict):
                continue
            # Get the TRANSLATION text (this is what we want to cache lookups for)
            # Handle both string and dict formats: {"text": "...", "tokens": [...]}
            translation = sentence_entry.get("translation") or sentence_entry.get("text") or ""
            if isinstance(translation, dict):
                translation = translation.get("text", "")
            if translation and isinstance(translation, str):
                all_sentences.append(translation.strip())

    print(f"[LOOKUP_CACHE] Extracted {len(all_sentences)} sentences from {len(chunks)} chunks")
    logger.debug("Lookup cache: extracted %d sentences from %d chunks", len(all_sentences), len(chunks))
    if not all_sentences:
        print("[LOOKUP_CACHE] No sentences found!")
        logger.debug("No sentences found for lookup cache")
        return None

    # Get configuration
    # For lookup cache: we look up words in the TRANSLATION language (target)
    # and ALWAYS provide definitions in English to help user understand
    target_languages = request.inputs.target_languages
    lookup_language = target_languages[0] if target_languages else "Arabic"  # Language of words being looked up
    definition_language = "English"  # Always provide definitions in English
    batch_size = getattr(request.inputs, "lookup_cache_batch_size", 10)
    job_id = request.job_id or "unknown"

    logger.info(
        "Building lookup cache",
        extra={
            "event": "lookup_cache.build.start",
            "attributes": {
                "job_id": job_id,
                "sentence_count": len(all_sentences),
                "lookup_language": lookup_language,
                "definition_language": definition_language,
            },
            "console_suppress": True,
        },
    )

    if tracker is not None:
        tracker.publish_progress(
            {
                "stage": "lookup_cache",
                "message": f"Building lookup cache for {len(all_sentences)} sentences...",
            }
        )

    start_time = time.perf_counter()

    try:
        # Initialize cache manager with job_dir for persistence
        cache_manager = LookupCacheManager(
            job_id=job_id,
            job_dir=job_dir,
            input_language=lookup_language,
            definition_language=definition_language,
        )

        # Build cache from sentences
        # Use the translation client from config
        from ...llm_client_manager import client_scope

        translation_client = getattr(config_result.pipeline_config, "translation_client", None)
        with client_scope(translation_client) as resolved_client:
            cache_manager.build_from_sentences(
                sentences=all_sentences,
                llm_client=resolved_client,
                batch_size=batch_size,
                skip_stopwords=True,
                progress_tracker=tracker,
            )

        # Save the cache
        print(f"[LOOKUP_CACHE] Saving cache to {cache_manager.cache_path}")
        cache_manager.save()
        cache_path = cache_manager.cache_path
        print(f"[LOOKUP_CACHE] Cache saved! Exists: {cache_path.exists()}")

        elapsed = time.perf_counter() - start_time

        logger.info(
            "Lookup cache built successfully",
            extra={
                "event": "lookup_cache.build.complete",
                "attributes": {
                    "job_id": job_id,
                    "cache_path": str(cache_path),
                    "word_count": cache_manager.cache.stats.total_words,
                    "llm_calls": cache_manager.cache.stats.llm_calls,
                    "elapsed_seconds": round(elapsed, 2),
                },
                "console_suppress": True,
            },
        )

        if tracker is not None:
            tracker.publish_progress(
                {
                    "stage": "lookup_cache",
                    "message": f"Lookup cache built: {cache_manager.cache.stats.total_words} words",
                }
            )
            # Update generated files metadata with cache info
            tracker.update_generated_files_metadata(
                {
                    "lookup_cache": {
                        "available": True,
                        "word_count": cache_manager.cache.stats.total_words,
                        "llm_calls": cache_manager.cache.stats.llm_calls,
                        "skipped_stopwords": cache_manager.cache.stats.skipped_stopwords,
                        "build_time_seconds": round(elapsed, 2),
                        "input_language": input_language,
                        "definition_language": definition_language,
                    }
                }
            )

        return cache_path

    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        logger.error(
            "Failed to build lookup cache",
            extra={
                "event": "lookup_cache.build.error",
                "attributes": {
                    "job_id": job_id,
                    "error": str(exc),
                    "elapsed_seconds": round(elapsed, 2),
                },
            },
        )
        if tracker is not None:
            tracker.publish_progress(
                {
                    "stage": "lookup_cache",
                    "message": f"Lookup cache build failed: {exc}",
                    "error": True,
                }
            )
        # Don't fail the pipeline for lookup cache errors
        return None
