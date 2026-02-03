"""Cache manager for word lookup cache.

This module handles loading, saving, and managing the lookup cache,
including linking audio references from timing tracks.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.progress_tracker import ProgressTracker
    from modules.llm_client import LLMClient

from modules import logging_manager as log_mgr

from .models import AudioRef, LookupCache, LookupCacheEntry
from .tokenizer import count_skipped_stopwords, extract_unique_words, normalize_word
from .batch_lookup import LOOKUP_BATCH_SUBDIR, build_lookup_cache_batch

logger = log_mgr.get_logger().getChild("lookup_cache")

# Default file names
LOOKUP_CACHE_FILENAME = "lookup_cache.json"
LOOKUP_CACHE_STATS_FILENAME = "lookup_cache_stats.json"


class LookupCacheManager:
    """Manager for job-level word lookup cache.

    Handles loading, saving, building, and querying the cache.
    """

    def __init__(
        self,
        job_id: str,
        job_dir: Path,
        *,
        input_language: str = "",
        definition_language: str = "",
    ):
        """Initialize the cache manager.

        Args:
            job_id: Job identifier.
            job_dir: Path to job directory (containing metadata/).
            input_language: Source language for lookups.
            definition_language: Definition language (typically target translation).
        """
        self.job_id = job_id
        self.job_dir = Path(job_dir)
        self.metadata_dir = self.job_dir / "metadata"
        self.cache_path = self.metadata_dir / LOOKUP_CACHE_FILENAME
        self.batch_log_dir = self.metadata_dir / "llm_batches" / LOOKUP_BATCH_SUBDIR

        self._cache: Optional[LookupCache] = None
        self._input_language = input_language
        self._definition_language = definition_language

    @property
    def cache(self) -> LookupCache:
        """Get the cache, loading from disk if needed."""
        if self._cache is None:
            self._cache = self._load_or_create()
        return self._cache

    def _load_or_create(self) -> LookupCache:
        """Load cache from disk or create a new one."""
        if self.cache_path.exists():
            try:
                loaded = LookupCache.load(self.cache_path)
                # Update languages if not set
                if not loaded.input_language and self._input_language:
                    loaded.input_language = self._input_language
                if not loaded.definition_language and self._definition_language:
                    loaded.definition_language = self._definition_language
                return loaded
            except Exception as exc:
                logger.warning("Failed to load lookup cache: %s", exc)

        return LookupCache(
            job_id=self.job_id,
            input_language=self._input_language,
            definition_language=self._definition_language,
        )

    def save(self) -> None:
        """Save the cache to disk."""
        if self._cache is None:
            return

        self._cache.update_stats()
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self._cache.save(self.cache_path)

    def get(self, word: str) -> Optional[LookupCacheEntry]:
        """Look up a word in the cache.

        Args:
            word: Word to look up.

        Returns:
            Cache entry if found, None otherwise.
        """
        return self.cache.get(word)

    def get_bulk(self, words: Sequence[str]) -> Dict[str, Optional[LookupCacheEntry]]:
        """Look up multiple words at once.

        Args:
            words: Words to look up.

        Returns:
            Dict mapping word -> entry (None if not found).
        """
        results = {}
        for word in words:
            normalized = normalize_word(word)
            results[word] = self.cache.get(normalized)
        return results

    def add_entry(self, entry: LookupCacheEntry) -> None:
        """Add or update a cache entry.

        Args:
            entry: Entry to add.
        """
        self.cache.add(entry)

    def add_entries(self, entries: Dict[str, LookupCacheEntry]) -> None:
        """Add multiple cache entries.

        Args:
            entries: Dict of normalized word -> entry.
        """
        for entry in entries.values():
            self.cache.add(entry)

    def build_from_sentences(
        self,
        sentences: Sequence[str],
        *,
        llm_client: "LLMClient",
        batch_size: int = 10,
        skip_stopwords: bool = True,
        min_word_length: int = 2,
        progress_tracker: Optional["ProgressTracker"] = None,
        timeout_seconds: float = 45.0,
    ) -> int:
        """Build cache entries from a batch of sentences.

        Extracts unique words, filters stopwords and cached words,
        then looks up definitions via LLM.

        Args:
            sentences: Sentences to extract words from.
            llm_client: LLM client for lookups.
            batch_size: Words per LLM batch call.
            skip_stopwords: Whether to skip stopwords.
            min_word_length: Minimum word length to include.
            progress_tracker: Optional progress tracker.
            timeout_seconds: Timeout per LLM call.

        Returns:
            Number of new entries added.
        """
        start_time = time.perf_counter()

        # Extract unique words not in cache
        unique_words = extract_unique_words(
            list(sentences),
            existing_cache=self.cache,
            language=self._input_language,
            skip_stopwords=skip_stopwords,
            min_word_length=min_word_length,
        )

        if not unique_words:
            return 0

        # Count skipped stopwords for stats
        if skip_stopwords:
            skipped_count = count_skipped_stopwords(
                list(sentences),
                existing_cache=self.cache,
                language=self._input_language,
            )
            self.cache.stats.skipped_stopwords += skipped_count

        # Build cache entries via LLM
        self.batch_log_dir.mkdir(parents=True, exist_ok=True)

        # Callback to add entries and save cache incrementally after each batch
        def _on_batch_complete(batch_entries: Dict[str, LookupCacheEntry]) -> None:
            self.add_entries(batch_entries)
            # Save cache incrementally so dictionary becomes available during build
            try:
                self.save()
            except Exception as exc:
                logger.warning("Failed to save cache incrementally: %s", exc)

        entries, llm_calls, _elapsed = build_lookup_cache_batch(
            unique_words,
            self._input_language,
            self._definition_language,
            llm_client=llm_client,
            batch_size=batch_size,
            progress_tracker=progress_tracker,
            timeout_seconds=timeout_seconds,
            batch_log_dir=self.batch_log_dir,
            existing_cache=self.cache,
            on_batch_complete=_on_batch_complete,
        )

        # Entries already added via callback, but ensure any stragglers are added
        self.add_entries(entries)

        # Update stats
        self.cache.stats.llm_calls += llm_calls
        self.cache.stats.build_time_seconds += time.perf_counter() - start_time

        return len(entries)

    def link_audio_references(
        self,
        timing_tracks: Mapping[str, Sequence[Mapping[str, Any]]],
        chunk_id: str,
    ) -> int:
        """Link audio references from timing tracks to cached words.

        Args:
            timing_tracks: Dict of track name -> list of timing tokens.
                Each token has: token/text, t0, t1, sentenceIdx/sentence_idx, wordIdx/word_idx
            chunk_id: Chunk identifier.

        Returns:
            Number of audio references added.
        """
        refs_added = 0

        for track_name, tokens in timing_tracks.items():
            for token in tokens:
                # Get word text
                word_text = token.get("token") or token.get("text") or ""
                if not word_text:
                    continue

                normalized = normalize_word(str(word_text))
                if not normalized:
                    continue

                # Check if word is in cache
                entry = self.cache.get(normalized)
                if entry is None:
                    continue

                # Get timing info
                t0 = token.get("t0") or token.get("start") or 0.0
                t1 = token.get("t1") or token.get("end") or 0.0

                if t1 <= t0:
                    continue

                # Get sentence and token indices
                sentence_idx = (
                    token.get("sentenceIdx")
                    or token.get("sentence_idx")
                    or token.get("sentenceId")
                    or 0
                )
                token_idx = (
                    token.get("wordIdx")
                    or token.get("word_idx")
                    or token.get("tokenIdx")
                    or 0
                )

                # Create audio reference
                audio_ref = AudioRef(
                    chunk_id=chunk_id,
                    sentence_idx=int(sentence_idx),
                    token_idx=int(token_idx),
                    track=track_name,
                    t0=float(t0),
                    t1=float(t1),
                )

                # Add to entry (deduplication handled by add_audio_reference)
                entry.add_audio_reference(audio_ref)
                refs_added += 1

        return refs_added

    def to_summary_dict(self) -> Dict[str, Any]:
        """Get a summary dict suitable for API responses.

        Returns:
            Summary dictionary with cache availability and stats.
        """
        self.cache.update_stats()
        return {
            "available": len(self.cache.entries) > 0,
            "word_count": self.cache.stats.total_words,
            "audio_ref_count": self.cache.stats.total_audio_refs,
            "input_language": self.cache.input_language,
            "definition_language": self.cache.definition_language,
            "version": self.cache.version,
        }


def resolve_lookup_cache_path(job_dir: Path) -> Path:
    """Get the path to the lookup cache file for a job.

    Args:
        job_dir: Job directory path.

    Returns:
        Path to lookup_cache.json.
    """
    return job_dir / "metadata" / LOOKUP_CACHE_FILENAME


def load_lookup_cache(job_dir: Path) -> Optional[LookupCache]:
    """Load lookup cache from a job directory.

    Args:
        job_dir: Job directory path.

    Returns:
        LookupCache if file exists and is valid, None otherwise.
    """
    cache_path = resolve_lookup_cache_path(job_dir)
    if not cache_path.exists():
        return None

    try:
        return LookupCache.load(cache_path)
    except Exception as exc:
        logger.warning("Failed to load lookup cache from %s: %s", cache_path, exc)
        return None


def lookup_word_from_job(job_dir: Path, word: str) -> Optional[LookupCacheEntry]:
    """Look up a single word from a job's cache.

    Args:
        job_dir: Job directory path.
        word: Word to look up.

    Returns:
        Cache entry if found, None otherwise.
    """
    cache = load_lookup_cache(job_dir)
    if cache is None:
        return None
    return cache.get(word)


__all__ = [
    "LOOKUP_CACHE_FILENAME",
    "LookupCacheManager",
    "load_lookup_cache",
    "lookup_word_from_job",
    "resolve_lookup_cache_path",
]
