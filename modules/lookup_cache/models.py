"""Data models for word lookup cache.

This module defines the core data structures for caching dictionary lookups
during batch translation, including audio timing references for pronunciation.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class AudioRef:
    """Reference to a word's occurrence in an audio track.

    Enables seeking to the exact position where a word is pronounced
    in the existing narration audio, providing instant playback without TTS.
    """

    chunk_id: str
    """Chunk identifier (e.g., 'chunk_0001')."""

    sentence_idx: int
    """Zero-based sentence index within the chunk."""

    token_idx: int
    """Zero-based token index within the sentence."""

    track: str
    """Audio track name: 'original' or 'translation'."""

    t0: float
    """Start time in seconds within the audio track."""

    t1: float
    """End time in seconds within the audio track."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "sentence_idx": self.sentence_idx,
            "token_idx": self.token_idx,
            "track": self.track,
            "t0": round(self.t0, 3),
            "t1": round(self.t1, 3),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioRef":
        """Create from dictionary."""
        return cls(
            chunk_id=str(data.get("chunk_id", "")),
            sentence_idx=int(data.get("sentence_idx", 0)),
            token_idx=int(data.get("token_idx", 0)),
            track=str(data.get("track", "translation")),
            t0=float(data.get("t0", 0.0)),
            t1=float(data.get("t1", 0.0)),
        )


@dataclass(slots=True)
class LookupCacheEntry:
    """A cached dictionary lookup result for a single word.

    Contains the full LinguistLookupResult JSON structure plus
    references to where the word appears in the audio tracks.
    """

    word: str
    """Original word form as seen in the text."""

    word_normalized: str
    """Normalized form used as the cache key (lowercase, stripped)."""

    input_language: str
    """Source language of the word (e.g., 'Arabic')."""

    definition_language: str
    """Language of the definition (e.g., 'English')."""

    lookup_result: Dict[str, Any]
    """Full LinguistLookupResult JSON structure with type, definition, etc."""

    audio_references: List[AudioRef] = field(default_factory=list)
    """List of audio positions where this word is pronounced."""

    created_at: float = field(default_factory=time.time)
    """Unix timestamp when this entry was created."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "word": self.word,
            "word_normalized": self.word_normalized,
            "input_language": self.input_language,
            "definition_language": self.definition_language,
            "lookup_result": self.lookup_result,
            "audio_references": [ref.to_dict() for ref in self.audio_references],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LookupCacheEntry":
        """Create from dictionary."""
        audio_refs = [
            AudioRef.from_dict(ref)
            for ref in data.get("audio_references", [])
            if isinstance(ref, dict)
        ]
        return cls(
            word=str(data.get("word", "")),
            word_normalized=str(data.get("word_normalized", "")),
            input_language=str(data.get("input_language", "")),
            definition_language=str(data.get("definition_language", "")),
            lookup_result=data.get("lookup_result") or {},
            audio_references=audio_refs,
            created_at=float(data.get("created_at", 0.0)),
        )

    def add_audio_reference(self, ref: AudioRef) -> None:
        """Add an audio reference, avoiding duplicates."""
        # Check for duplicate (same chunk, sentence, token, track)
        for existing in self.audio_references:
            if (
                existing.chunk_id == ref.chunk_id
                and existing.sentence_idx == ref.sentence_idx
                and existing.token_idx == ref.token_idx
                and existing.track == ref.track
            ):
                return
        self.audio_references.append(ref)


@dataclass
class LookupCacheStats:
    """Statistics about the lookup cache."""

    total_words: int = 0
    """Total number of unique words in the cache."""

    total_audio_refs: int = 0
    """Total number of audio references across all words."""

    llm_calls: int = 0
    """Number of LLM batch calls made to build the cache."""

    build_time_seconds: float = 0.0
    """Total time spent building the cache."""

    skipped_stopwords: int = 0
    """Number of stopwords that were skipped."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "total_words": self.total_words,
            "total_audio_refs": self.total_audio_refs,
            "llm_calls": self.llm_calls,
            "build_time_seconds": round(self.build_time_seconds, 2),
            "skipped_stopwords": self.skipped_stopwords,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LookupCacheStats":
        """Create from dictionary."""
        return cls(
            total_words=int(data.get("total_words", 0)),
            total_audio_refs=int(data.get("total_audio_refs", 0)),
            llm_calls=int(data.get("llm_calls", 0)),
            build_time_seconds=float(data.get("build_time_seconds", 0.0)),
            skipped_stopwords=int(data.get("skipped_stopwords", 0)),
        )


@dataclass
class LookupCache:
    """Job-level container for cached word lookups.

    Stores all lookup cache entries for a single job, keyed by
    normalized word form for O(1) lookup performance.
    """

    job_id: str
    """Job identifier this cache belongs to."""

    input_language: str
    """Source language of the cached words."""

    definition_language: str
    """Language of the definitions (typically the target translation language)."""

    entries: Dict[str, LookupCacheEntry] = field(default_factory=dict)
    """Cache entries keyed by normalized word form."""

    stats: LookupCacheStats = field(default_factory=LookupCacheStats)
    """Build statistics."""

    version: str = "1.0"
    """Cache format version for future compatibility."""

    def get(self, word: str) -> Optional[LookupCacheEntry]:
        """Look up a word in the cache.

        Args:
            word: Word to look up (will be normalized).

        Returns:
            Cache entry if found, None otherwise.
        """
        from .tokenizer import normalize_word
        normalized = normalize_word(word)
        return self.entries.get(normalized)

    def add(self, entry: LookupCacheEntry) -> None:
        """Add or update a cache entry.

        Args:
            entry: Entry to add (keyed by word_normalized).
        """
        key = entry.word_normalized.lower().strip()
        if key:
            self.entries[key] = entry

    def update_stats(self) -> None:
        """Recalculate statistics from current entries."""
        self.stats.total_words = len(self.entries)
        self.stats.total_audio_refs = sum(
            len(entry.audio_references) for entry in self.entries.values()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        self.update_stats()
        return {
            "job_id": self.job_id,
            "input_language": self.input_language,
            "definition_language": self.definition_language,
            "entries": {
                key: entry.to_dict() for key, entry in sorted(self.entries.items())
            },
            "stats": self.stats.to_dict(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LookupCache":
        """Create from dictionary."""
        entries_data = data.get("entries") or {}
        entries = {
            key: LookupCacheEntry.from_dict(entry_data)
            for key, entry_data in entries_data.items()
            if isinstance(entry_data, dict)
        }
        stats_data = data.get("stats") or {}
        return cls(
            job_id=str(data.get("job_id", "")),
            input_language=str(data.get("input_language", "")),
            definition_language=str(data.get("definition_language", "")),
            entries=entries,
            stats=LookupCacheStats.from_dict(stats_data),
            version=str(data.get("version", "1.0")),
        )

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "LookupCache":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        """Save cache to a JSON file.

        Args:
            path: Path to the output file.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "LookupCache":
        """Load cache from a JSON file.

        Args:
            path: Path to the cache file.

        Returns:
            Loaded cache, or empty cache if file doesn't exist.
        """
        if not path.exists():
            return cls(job_id="", input_language="", definition_language="")
        content = path.read_text(encoding="utf-8")
        return cls.from_json(content)


__all__ = [
    "AudioRef",
    "LookupCache",
    "LookupCacheEntry",
    "LookupCacheStats",
]
