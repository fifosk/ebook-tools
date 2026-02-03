"""Word lookup cache module for pre-computed dictionary definitions.

This module provides functionality for building and querying a cache
of dictionary lookups during batch translation, enabling instant
word definitions in the interactive reader without additional LLM calls.

Key Components:
    - LookupCache: Job-level container for cached entries
    - LookupCacheEntry: Individual cached word definition
    - LookupCacheManager: High-level cache management
    - AudioRef: Reference to word occurrence in audio track

Usage Example:
    from modules.lookup_cache import LookupCacheManager

    manager = LookupCacheManager(
        job_id="job-123",
        job_dir=Path("storage/jobs/job-123"),
        input_language="Arabic",
        definition_language="English",
    )

    # Build cache from sentences during translation
    new_count = manager.build_from_sentences(
        sentences=["مرحبا بالعالم", "هذا كتاب جميل"],
        llm_client=client,
        batch_size=10,
        skip_stopwords=True,
    )

    # Link audio references after timing generation
    manager.link_audio_references(timing_tracks, chunk_id="chunk_0001")

    # Save cache
    manager.save()

    # Query cache
    entry = manager.get("كتاب")
    if entry:
        print(entry.lookup_result["definition"])
"""

from .models import (
    AudioRef,
    LookupCache,
    LookupCacheEntry,
    LookupCacheStats,
)

from .tokenizer import (
    count_skipped_stopwords,
    extract_unique_words,
    extract_words,
    is_stopword,
    normalize_word,
)

from .batch_lookup import (
    LOOKUP_BATCH_SUBDIR,
    build_lookup_cache_batch,
    build_lookup_system_prompt,
    lookup_words_batch,
)

from .cache_manager import (
    LOOKUP_CACHE_FILENAME,
    LookupCacheManager,
    load_lookup_cache,
    lookup_word_from_job,
    resolve_lookup_cache_path,
)

__all__ = [
    # Models
    "AudioRef",
    "LookupCache",
    "LookupCacheEntry",
    "LookupCacheStats",
    # Tokenizer
    "count_skipped_stopwords",
    "extract_unique_words",
    "extract_words",
    "is_stopword",
    "normalize_word",
    # Batch lookup
    "LOOKUP_BATCH_SUBDIR",
    "build_lookup_cache_batch",
    "build_lookup_system_prompt",
    "lookup_words_batch",
    # Cache manager
    "LOOKUP_CACHE_FILENAME",
    "LookupCacheManager",
    "load_lookup_cache",
    "lookup_word_from_job",
    "resolve_lookup_cache_path",
]
