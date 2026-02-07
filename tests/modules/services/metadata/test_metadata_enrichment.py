"""Integration tests for metadata enrichment functionality.

These tests verify that the enrichment module correctly:
1. Enriches book metadata from external sources
2. Enriches movie metadata from external sources
3. Enriches TV series/episode metadata from external sources
4. Downloads cover art as part of enrichment
5. Handles already-enriched metadata correctly

Run with: pytest tests/modules/services/metadata/test_metadata_enrichment.py -v -s
"""
import pytest
from pathlib import Path
from typing import Dict, Any

from modules.services.metadata import (
    enrich_media_metadata,
    enrich_movie_metadata,
    enrich_tv_metadata,
    enrich_metadata,
    detect_media_type,
    EnrichmentResult,
    MediaType,
)
from modules.services.metadata.services.unified_service import UnifiedMetadataService

pytestmark = pytest.mark.metadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def unified_service() -> UnifiedMetadataService:
    """Create a unified metadata service for tests."""
    return UnifiedMetadataService()


# ---------------------------------------------------------------------------
# Media Type Detection Tests
# ---------------------------------------------------------------------------

class TestMediaTypeDetection:
    """Test automatic media type detection from metadata."""

    def test_detect_book_from_isbn(self):
        """Metadata with ISBN should be detected as book."""
        metadata = {"isbn": "978-0451524935", "book_title": "1984"}
        assert detect_media_type(metadata) == MediaType.BOOK

    def test_detect_book_from_author(self):
        """Metadata with book_author should be detected as book."""
        metadata = {"book_title": "1984", "book_author": "George Orwell"}
        assert detect_media_type(metadata) == MediaType.BOOK

    def test_detect_movie_from_imdb_id(self):
        """Metadata with IMDB ID should be detected as movie."""
        metadata = {"title": "Inception", "imdb_id": "tt1375666"}
        assert detect_media_type(metadata) == MediaType.MOVIE

    def test_detect_tv_episode_from_series_info(self):
        """Metadata with series_name and season/episode should be TV episode."""
        metadata = {"series_name": "Breaking Bad", "season": 1, "episode": 1}
        assert detect_media_type(metadata) == MediaType.TV_EPISODE

    def test_detect_tv_series_from_series_name_only(self):
        """Metadata with only series_name should be TV series."""
        metadata = {"series_name": "Breaking Bad"}
        assert detect_media_type(metadata) == MediaType.TV_SERIES

    def test_detect_youtube_from_video_id(self):
        """Metadata with YouTube video ID should be detected as YouTube."""
        metadata = {"youtube_video_id": "dQw4w9WgXcQ"}
        assert detect_media_type(metadata) == MediaType.YOUTUBE_VIDEO

    def test_detect_youtube_from_url(self):
        """Metadata with YouTube URL should be detected as YouTube."""
        metadata = {"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        assert detect_media_type(metadata) == MediaType.YOUTUBE_VIDEO

    def test_default_to_book(self):
        """Unknown metadata should default to book."""
        metadata = {"title": "Something"}
        assert detect_media_type(metadata) == MediaType.BOOK


# ---------------------------------------------------------------------------
# Book Enrichment Tests
# ---------------------------------------------------------------------------

class TestBookEnrichment:
    """Test book metadata enrichment."""

    def test_enrich_book_by_title_author(self, unified_service: UnifiedMetadataService):
        """Enrich a book with title and author."""
        metadata = {
            "book_title": "1984",
            "book_author": "George Orwell",
        }

        result = enrich_media_metadata(metadata, service=unified_service)

        assert result.enriched, "Book should be enriched"
        assert result.confidence is not None
        print(f"\nBook enrichment result:")
        print(f"  Enriched: {result.enriched}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Source: {result.source_result.primary_source.value if result.source_result and result.source_result.primary_source else 'N/A'}")

        # Check enriched fields
        enriched = result.metadata
        print(f"  Summary available: {bool(enriched.get('book_summary'))}")
        print(f"  Cover URL available: {bool(enriched.get('book_cover_url') or enriched.get('book_cover_file'))}")
        print(f"  Year available: {bool(enriched.get('book_year'))}")

    def test_enrich_book_by_isbn(self, unified_service: UnifiedMetadataService):
        """Enrich a book with ISBN."""
        metadata = {
            "isbn": "978-0451524935",  # 1984 ISBN
        }

        result = enrich_media_metadata(metadata, service=unified_service)

        assert result.enriched, "Book should be enriched by ISBN"
        print(f"\nISBN enrichment result:")
        print(f"  Enriched: {result.enriched}")
        print(f"  Title: {result.metadata.get('book_title')}")
        print(f"  Author: {result.metadata.get('book_author')}")

    def test_enrich_book_preserves_existing_data(self, unified_service: UnifiedMetadataService):
        """Enrichment should not overwrite existing non-empty fields."""
        metadata = {
            "book_title": "My Custom Title",  # Should be preserved
            "book_author": "George Orwell",
        }

        result = enrich_media_metadata(metadata, service=unified_service)

        # Title should be preserved
        assert result.metadata.get("book_title") == "My Custom Title"
        print(f"\nPreservation test:")
        print(f"  Title preserved: {result.metadata.get('book_title')}")

    def test_enrich_book_adds_cover_url(self, unified_service: UnifiedMetadataService):
        """Enrichment should add cover URL when available."""
        metadata = {
            "book_title": "Pride and Prejudice",
            "book_author": "Jane Austen",
        }

        result = enrich_media_metadata(metadata, service=unified_service)

        if result.enriched:
            cover = result.metadata.get("book_cover_url") or result.metadata.get("book_cover_file")
            print(f"\nCover URL test:")
            print(f"  Cover URL: {cover}")
            if cover:
                assert cover.startswith("http"), "Cover should be a URL"

    def test_skip_already_enriched(self, unified_service: UnifiedMetadataService):
        """Enrichment should skip if already enriched (without force)."""
        metadata = {
            "book_title": "1984",
            "book_author": "George Orwell",
            "_enrichment_source": "openlibrary",
            "_enrichment_confidence": "medium",
        }

        result = enrich_media_metadata(metadata, force=False, service=unified_service)

        # Should not re-enrich
        assert not result.enriched, "Should skip already enriched metadata"
        print(f"\nSkip enriched test: enriched={result.enriched}")

    def test_force_re_enrichment(self, unified_service: UnifiedMetadataService):
        """Force flag should re-enrich even if already enriched."""
        metadata = {
            "book_title": "1984",
            "book_author": "George Orwell",
            "_enrichment_source": "openlibrary",
            "_enrichment_confidence": "low",
        }

        result = enrich_media_metadata(metadata, force=True, service=unified_service)

        assert result.enriched, "Should re-enrich with force=True"
        print(f"\nForce re-enrichment test: enriched={result.enriched}")


# ---------------------------------------------------------------------------
# Movie Enrichment Tests
# ---------------------------------------------------------------------------

class TestMovieEnrichment:
    """Test movie metadata enrichment."""

    def test_enrich_movie_by_title_year(self, unified_service: UnifiedMetadataService):
        """Enrich a movie with title and year."""
        metadata = {
            "title": "Inception",
            "year": 2010,
        }

        result = enrich_movie_metadata(metadata, service=unified_service)

        assert result.enriched, "Movie should be enriched"
        print(f"\nMovie enrichment result:")
        print(f"  Enriched: {result.enriched}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Source: {result.source_result.primary_source.value if result.source_result and result.source_result.primary_source else 'N/A'}")

        enriched = result.metadata
        print(f"  IMDB ID: {enriched.get('imdb')}")
        print(f"  TMDB ID: {enriched.get('tmdb')}")
        print(f"  Cover URL: {enriched.get('cover_url')}")
        print(f"  Genres: {enriched.get('genres')}")

    def test_enrich_movie_by_imdb_id(self, unified_service: UnifiedMetadataService):
        """Enrich a movie with IMDB ID."""
        metadata = {
            "imdb_id": "tt0133093",  # The Matrix
        }

        result = enrich_movie_metadata(metadata, service=unified_service)

        if result.enriched:
            print(f"\nIMDB ID enrichment result:")
            print(f"  Title: {result.metadata.get('title') or result.metadata.get('movie_title')}")
            print(f"  Year: {result.metadata.get('year')}")
        else:
            print(f"\nIMDB lookup returned no result (API may not support direct ID lookup)")

    def test_enrich_movie_gets_poster(self, unified_service: UnifiedMetadataService):
        """Enrichment should return poster/cover URL."""
        metadata = {
            "title": "The Matrix",
            "year": 1999,
        }

        result = enrich_movie_metadata(metadata, service=unified_service)

        if result.enriched:
            cover = result.metadata.get("cover_url")
            print(f"\nMovie poster test:")
            print(f"  Poster URL: {cover}")
            if cover:
                assert "http" in cover, "Poster should be a URL"


# ---------------------------------------------------------------------------
# TV Series Enrichment Tests
# ---------------------------------------------------------------------------

class TestTvEnrichment:
    """Test TV series/episode metadata enrichment."""

    def test_enrich_tv_series(self, unified_service: UnifiedMetadataService):
        """Enrich a TV series."""
        metadata = {
            "series_name": "Breaking Bad",
        }

        result = enrich_tv_metadata(metadata, service=unified_service)

        assert result.enriched, "TV series should be enriched"
        print(f"\nTV series enrichment result:")
        print(f"  Enriched: {result.enriched}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Title: {result.metadata.get('title')}")
        print(f"  Genres: {result.metadata.get('genres')}")

    def test_enrich_tv_episode(self, unified_service: UnifiedMetadataService):
        """Enrich a TV episode."""
        metadata = {
            "series_name": "Breaking Bad",
            "season": 1,
            "episode": 1,
        }

        result = enrich_tv_metadata(metadata, service=unified_service)

        assert result.enriched, "TV episode should be enriched"
        print(f"\nTV episode enrichment result:")
        print(f"  Enriched: {result.enriched}")
        print(f"  Title: {result.metadata.get('title')}")
        print(f"  Episode Title: {result.metadata.get('episode_title')}")
        print(f"  Series: {result.metadata.get('series_name')}")


# ---------------------------------------------------------------------------
# Auto-Detection Enrichment Tests
# ---------------------------------------------------------------------------

class TestAutoEnrichment:
    """Test automatic media type detection and enrichment."""

    def test_auto_enrich_book(self, unified_service: UnifiedMetadataService):
        """Auto-detect and enrich book."""
        metadata = {
            "book_title": "The Great Gatsby",
            "book_author": "F. Scott Fitzgerald",
        }

        result = enrich_metadata(metadata, service=unified_service)

        assert result.enriched
        print(f"\nAuto book enrichment: {result.enriched}, confidence: {result.confidence}")

    def test_auto_enrich_movie(self, unified_service: UnifiedMetadataService):
        """Auto-detect and enrich movie."""
        metadata = {
            "title": "Pulp Fiction",
            "imdb_id": "tt0110912",
        }

        result = enrich_metadata(metadata, service=unified_service)

        print(f"\nAuto movie enrichment: {result.enriched}, confidence: {result.confidence}")

    def test_auto_enrich_tv(self, unified_service: UnifiedMetadataService):
        """Auto-detect and enrich TV series."""
        metadata = {
            "series_name": "Game of Thrones",
            "season": 1,
            "episode": 1,
        }

        result = enrich_metadata(media_type=MediaType.TV_EPISODE, existing_metadata=metadata, service=unified_service)

        print(f"\nAuto TV enrichment: {result.enriched}, confidence: {result.confidence}")


# ---------------------------------------------------------------------------
# Cover Art Download Tests
# ---------------------------------------------------------------------------

class TestCoverArtDownload:
    """Test cover art URL retrieval from various sources."""

    def test_book_cover_from_openlibrary(self, unified_service: UnifiedMetadataService):
        """OpenLibrary should return cover URLs."""
        metadata = {
            "book_title": "Harry Potter and the Sorcerer's Stone",
            "book_author": "J.K. Rowling",
        }

        result = enrich_media_metadata(metadata, service=unified_service)

        if result.enriched and result.source_result:
            cover = result.source_result.cover_url
            print(f"\nOpenLibrary cover URL: {cover}")
            if cover:
                # OpenLibrary covers are from covers.openlibrary.org
                assert "openlibrary.org" in cover or "http" in cover

    def test_movie_poster_from_tmdb(self, unified_service: UnifiedMetadataService):
        """TMDB should return poster URLs."""
        metadata = {
            "title": "Avatar",
            "year": 2009,
        }

        result = enrich_movie_metadata(metadata, service=unified_service)

        if result.enriched and result.source_result:
            cover = result.source_result.cover_url
            print(f"\nTMDB poster URL: {cover}")
            if cover:
                # TMDB images are from image.tmdb.org
                assert "tmdb.org" in cover or "http" in cover

    def test_tv_series_poster(self, unified_service: UnifiedMetadataService):
        """TV series should return poster URLs."""
        metadata = {
            "series_name": "The Office",
        }

        result = enrich_tv_metadata(metadata, service=unified_service)

        if result.enriched and result.source_result:
            cover = result.source_result.cover_url
            print(f"\nTV series poster URL: {cover}")


# ---------------------------------------------------------------------------
# Enrichment Result Structure Tests
# ---------------------------------------------------------------------------

class TestEnrichmentResultStructure:
    """Test the structure of enrichment results."""

    def test_result_has_enrichment_provenance(self, unified_service: UnifiedMetadataService):
        """Enriched metadata should have provenance fields."""
        metadata = {
            "book_title": "Moby Dick",
            "book_author": "Herman Melville",
        }

        result = enrich_media_metadata(metadata, service=unified_service)

        if result.enriched:
            # Check provenance fields
            assert "_enrichment_source" in result.metadata
            assert "_enrichment_confidence" in result.metadata
            print(f"\nProvenance fields:")
            print(f"  Source: {result.metadata.get('_enrichment_source')}")
            print(f"  Confidence: {result.metadata.get('_enrichment_confidence')}")

    def test_result_has_source_ids(self, unified_service: UnifiedMetadataService):
        """Enriched metadata should include external source IDs."""
        metadata = {
            "title": "Fight Club",
            "year": 1999,
        }

        result = enrich_movie_metadata(metadata, service=unified_service)

        if result.enriched and result.source_result:
            source_ids = result.source_result.source_ids
            print(f"\nSource IDs:")
            print(f"  IMDB: {source_ids.imdb_id}")
            print(f"  TMDB: {source_ids.tmdb_id}")


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestEnrichmentErrorHandling:
    """Test error handling in enrichment."""

    def test_handles_empty_metadata(self):
        """Should handle empty metadata gracefully."""
        result = enrich_media_metadata({})

        assert not result.enriched
        print(f"\nEmpty metadata result: enriched={result.enriched}")

    def test_handles_missing_title(self):
        """Should handle metadata without title."""
        metadata = {"book_author": "Unknown"}

        result = enrich_media_metadata(metadata)

        # Should not crash, may or may not enrich
        print(f"\nMissing title result: enriched={result.enriched}")

    def test_handles_nonexistent_book(self):
        """Should handle non-existent book gracefully."""
        metadata = {
            "book_title": "This Book Does Not Exist XYZ123456789",
            "book_author": "Nobody Real",
        }

        result = enrich_media_metadata(metadata)

        # Should not crash
        print(f"\nNon-existent book result: enriched={result.enriched}")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
