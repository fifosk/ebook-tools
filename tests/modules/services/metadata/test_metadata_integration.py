"""Integration tests for the unified metadata lookup pipeline.

These tests require valid API keys to be configured:
- TMDB API key for movie/TV lookups
- OMDb API key for movie/TV lookups
- Google Books API key for book lookups

Run with: pytest tests/modules/services/metadata/test_metadata_integration.py -v -s
"""
import pytest
from typing import Optional

from modules.services.metadata.types import (
    MediaType,
    MetadataSource,
    ConfidenceLevel,
    LookupQuery,
    LookupOptions,
)
from modules.services.metadata.registry import (
    MetadataSourceRegistry,
    create_registry_from_config,
)
from modules.services.metadata.pipeline import (
    MetadataLookupPipeline,
    create_pipeline,
)

pytestmark = pytest.mark.metadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def registry() -> MetadataSourceRegistry:
    """Create a registry from config with all available API keys."""
    return create_registry_from_config()


@pytest.fixture(scope="module")
def pipeline() -> MetadataLookupPipeline:
    """Create a pipeline from config."""
    return create_pipeline(cache_enabled=False)


@pytest.fixture(scope="module")
def default_options() -> LookupOptions:
    """Default options for direct client lookups."""
    return LookupOptions(max_sources=1, timeout_seconds=30.0)


def get_api_key(registry: MetadataSourceRegistry, source: MetadataSource) -> Optional[str]:
    """Get API key for a source if available."""
    return registry._api_keys.get(source.value)


# ---------------------------------------------------------------------------
# API Key Availability Tests
# ---------------------------------------------------------------------------

class TestApiKeyAvailability:
    """Test that API keys are properly loaded from configuration."""

    def test_tmdb_key_available(self, registry: MetadataSourceRegistry):
        """TMDB API key should be loaded."""
        key = get_api_key(registry, MetadataSource.TMDB)
        assert key is not None, "TMDB API key not configured"
        assert len(key) > 0, "TMDB API key is empty"
        print(f"\nTMDB key loaded: {key[:8]}...")

    def test_omdb_key_available(self, registry: MetadataSourceRegistry):
        """OMDb API key should be loaded."""
        key = get_api_key(registry, MetadataSource.OMDB)
        assert key is not None, "OMDb API key not configured"
        assert len(key) > 0, "OMDb API key is empty"
        print(f"\nOMDb key loaded: {key[:8]}...")

    def test_google_books_key_available(self, registry: MetadataSourceRegistry):
        """Google Books API key should be loaded."""
        key = get_api_key(registry, MetadataSource.GOOGLE_BOOKS)
        assert key is not None, "Google Books API key not configured"
        assert len(key) > 0, "Google Books API key is empty"
        print(f"\nGoogle Books key loaded: {key[:8]}...")


# ---------------------------------------------------------------------------
# Client Availability Tests
# ---------------------------------------------------------------------------

class TestClientAvailability:
    """Test that clients can be instantiated with API keys."""

    def test_tmdb_client_available(self, registry: MetadataSourceRegistry):
        """TMDB client should be available when key is configured."""
        client = registry.get_client(MetadataSource.TMDB)
        if get_api_key(registry, MetadataSource.TMDB):
            assert client is not None, "TMDB client not available despite key being set"
            assert client.is_available, "TMDB client reports not available"
            print(f"\nTMDB client: {client}")

    def test_omdb_client_available(self, registry: MetadataSourceRegistry):
        """OMDb client should be available when key is configured."""
        client = registry.get_client(MetadataSource.OMDB)
        if get_api_key(registry, MetadataSource.OMDB):
            assert client is not None, "OMDb client not available despite key being set"
            assert client.is_available, "OMDb client reports not available"
            print(f"\nOMDb client: {client}")

    def test_google_books_client_available(self, registry: MetadataSourceRegistry):
        """Google Books client should be available when key is configured."""
        client = registry.get_client(MetadataSource.GOOGLE_BOOKS)
        if get_api_key(registry, MetadataSource.GOOGLE_BOOKS):
            assert client is not None, "Google Books client not available despite key being set"
            assert client.is_available, "Google Books client reports not available"
            print(f"\nGoogle Books client: {client}")

    def test_openlibrary_client_available(self, registry: MetadataSourceRegistry):
        """OpenLibrary client should always be available (no key required)."""
        client = registry.get_client(MetadataSource.OPENLIBRARY)
        assert client is not None, "OpenLibrary client not available"
        assert client.is_available, "OpenLibrary client reports not available"
        print(f"\nOpenLibrary client: {client}")

    def test_tvmaze_client_available(self, registry: MetadataSourceRegistry):
        """TVMaze client should always be available (no key required)."""
        client = registry.get_client(MetadataSource.TVMAZE)
        assert client is not None, "TVMaze client not available"
        assert client.is_available, "TVMaze client reports not available"
        print(f"\nTVMaze client: {client}")

    def test_wikipedia_client_available(self, registry: MetadataSourceRegistry):
        """Wikipedia client should always be available (no key required)."""
        client = registry.get_client(MetadataSource.WIKIPEDIA)
        assert client is not None, "Wikipedia client not available"
        assert client.is_available, "Wikipedia client reports not available"
        print(f"\nWikipedia client: {client}")


# ---------------------------------------------------------------------------
# Book Lookup Tests
# ---------------------------------------------------------------------------

class TestBookLookups:
    """Test book metadata lookups."""

    def test_book_lookup_by_title_author(self, pipeline: MetadataLookupPipeline):
        """Look up a well-known book by title and author."""
        query = LookupQuery(
            media_type=MediaType.BOOK,
            title="1984",
            author="George Orwell",
        )
        options = LookupOptions(max_sources=3)

        result = pipeline.lookup(query, options)

        assert result is not None, "No result returned"
        assert result.title is not None, "No title in result"
        print(f"\nBook lookup result:")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        print(f"  Genres: {result.genres}")
        print(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")
        print(f"  Cover: {result.cover_url}")
        print(f"  Confidence: {result.confidence.value}")
        print(f"  Primary Source: {result.primary_source.value if result.primary_source else 'N/A'}")
        print(f"  Contributing Sources: {[s.value for s in result.contributing_sources]}")

    def test_book_lookup_by_isbn(self, pipeline: MetadataLookupPipeline):
        """Look up a book by ISBN."""
        query = LookupQuery(
            media_type=MediaType.BOOK,
            title="",  # Empty title, rely on ISBN
            isbn="978-0451524935",  # 1984 ISBN
        )
        options = LookupOptions(max_sources=2)

        result = pipeline.lookup(query, options)

        assert result is not None, "No result returned"
        print(f"\nISBN lookup result:")
        print(f"  Title: {result.title}")
        print(f"  ISBN: {result.source_ids.isbn or result.source_ids.isbn_13 or 'N/A'}")
        print(f"  Primary Source: {result.primary_source.value if result.primary_source else 'N/A'}")

    def test_book_lookup_openlibrary_only(self, registry: MetadataSourceRegistry, default_options: LookupOptions):
        """Test OpenLibrary client directly (no API key required)."""
        client = registry.get_client(MetadataSource.OPENLIBRARY)
        assert client is not None

        query = LookupQuery(
            media_type=MediaType.BOOK,
            title="The Hitchhiker's Guide to the Galaxy",
            author="Douglas Adams",
        )

        result = client.lookup(query, default_options)

        assert result is not None, "OpenLibrary returned no result"
        print(f"\nOpenLibrary direct lookup:")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        print(f"  Confidence: {result.confidence.value}")

    def test_book_lookup_google_books(self, registry: MetadataSourceRegistry, default_options: LookupOptions):
        """Test Google Books client directly."""
        client = registry.get_client(MetadataSource.GOOGLE_BOOKS)
        if client is None:
            pytest.skip("Google Books client not available (no API key)")

        query = LookupQuery(
            media_type=MediaType.BOOK,
            title="Pride and Prejudice",
            author="Jane Austen",
        )

        result = client.lookup(query, default_options)

        assert result is not None, "Google Books returned no result"
        print(f"\nGoogle Books direct lookup:")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        print(f"  Genres: {result.genres}")
        print(f"  Cover: {result.cover_url}")
        print(f"  Confidence: {result.confidence.value}")


# ---------------------------------------------------------------------------
# Movie Lookup Tests
# ---------------------------------------------------------------------------

class TestMovieLookups:
    """Test movie metadata lookups."""

    def test_movie_lookup_by_title_year(self, pipeline: MetadataLookupPipeline):
        """Look up a well-known movie by title and year."""
        query = LookupQuery(
            media_type=MediaType.MOVIE,
            title="Inception",
            year=2010,
        )
        options = LookupOptions(max_sources=3)

        result = pipeline.lookup(query, options)

        assert result is not None, "No result returned"
        assert result.title is not None, "No title in result"
        print(f"\nMovie lookup result:")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        print(f"  Genres: {result.genres}")
        print(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")
        print(f"  Cover: {result.cover_url}")
        print(f"  Confidence: {result.confidence.value}")
        print(f"  Primary Source: {result.primary_source.value if result.primary_source else 'N/A'}")
        print(f"  Contributing Sources: {[s.value for s in result.contributing_sources]}")
        print(f"  IMDB ID: {result.source_ids.imdb_id or 'N/A'}")
        print(f"  TMDB ID: {result.source_ids.tmdb_id or 'N/A'}")

    def test_movie_lookup_tmdb_direct(self, registry: MetadataSourceRegistry, default_options: LookupOptions):
        """Test TMDB client directly."""
        client = registry.get_client(MetadataSource.TMDB)
        if client is None:
            pytest.skip("TMDB client not available (no API key)")

        query = LookupQuery(
            media_type=MediaType.MOVIE,
            title="The Matrix",
            year=1999,
        )

        result = client.lookup(query, default_options)

        assert result is not None, "TMDB returned no result"
        print(f"\nTMDB direct lookup:")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        print(f"  Genres: {result.genres}")
        print(f"  TMDB ID: {result.source_ids.tmdb_id or 'N/A'}")
        print(f"  Confidence: {result.confidence.value}")

    def test_movie_lookup_omdb_direct(self, registry: MetadataSourceRegistry, default_options: LookupOptions):
        """Test OMDb client directly."""
        client = registry.get_client(MetadataSource.OMDB)
        if client is None:
            pytest.skip("OMDb client not available (no API key)")

        query = LookupQuery(
            media_type=MediaType.MOVIE,
            title="Pulp Fiction",
            year=1994,
        )

        result = client.lookup(query, default_options)

        # OMDb may return None if API key is invalid or rate limited
        if result is None:
            pytest.skip("OMDb returned no result (API key may be invalid or rate limited)")

        print(f"\nOMDb direct lookup:")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        print(f"  Genres: {result.genres}")
        print(f"  IMDB ID: {result.source_ids.imdb_id or 'N/A'}")
        print(f"  Confidence: {result.confidence.value}")


# ---------------------------------------------------------------------------
# TV Series Lookup Tests
# ---------------------------------------------------------------------------

class TestTvSeriesLookups:
    """Test TV series metadata lookups."""

    def test_tv_series_lookup(self, pipeline: MetadataLookupPipeline):
        """Look up a well-known TV series."""
        query = LookupQuery(
            media_type=MediaType.TV_SERIES,
            title="Breaking Bad",
        )
        options = LookupOptions(max_sources=3)

        result = pipeline.lookup(query, options)

        assert result is not None, "No result returned"
        assert result.title is not None, "No title in result"
        print(f"\nTV Series lookup result:")
        print(f"  Title: {result.title}")
        print(f"  Year: {result.year}")
        print(f"  Genres: {result.genres}")
        print(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")
        print(f"  Confidence: {result.confidence.value}")
        print(f"  Primary Source: {result.primary_source.value if result.primary_source else 'N/A'}")
        print(f"  Contributing Sources: {[s.value for s in result.contributing_sources]}")

    def test_tv_episode_lookup(self, pipeline: MetadataLookupPipeline):
        """Look up a specific TV episode."""
        query = LookupQuery(
            media_type=MediaType.TV_EPISODE,
            title="Breaking Bad",
            season=1,
            episode=1,
        )
        options = LookupOptions(max_sources=3)

        result = pipeline.lookup(query, options)

        assert result is not None, "No result returned"
        print(f"\nTV Episode lookup result:")
        print(f"  Title: {result.title}")
        print(f"  Series: {result.series}")
        print(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")
        print(f"  Confidence: {result.confidence.value}")
        print(f"  Primary Source: {result.primary_source.value if result.primary_source else 'N/A'}")
        print(f"  Contributing Sources: {[s.value for s in result.contributing_sources]}")

    def test_tvmaze_direct(self, registry: MetadataSourceRegistry, default_options: LookupOptions):
        """Test TVMaze client directly (no API key required)."""
        client = registry.get_client(MetadataSource.TVMAZE)
        assert client is not None

        query = LookupQuery(
            media_type=MediaType.TV_EPISODE,
            title="Game of Thrones",
            season=1,
            episode=1,
        )

        result = client.lookup(query, default_options)

        assert result is not None, "TVMaze returned no result"
        print(f"\nTVMaze direct lookup:")
        print(f"  Title: {result.title}")
        print(f"  Series: {result.series}")
        print(f"  Confidence: {result.confidence.value}")


# ---------------------------------------------------------------------------
# Fallback Chain Tests
# ---------------------------------------------------------------------------

class TestFallbackChains:
    """Test that fallback chains work correctly."""

    def test_book_chain_defined(self, registry: MetadataSourceRegistry):
        """Book fallback chain should be defined."""
        chain = registry.get_chain(MediaType.BOOK)
        assert len(chain) > 0, "Book chain is empty"
        print(f"\nBook fallback chain: {[s.value for s in chain]}")

    def test_movie_chain_defined(self, registry: MetadataSourceRegistry):
        """Movie fallback chain should be defined."""
        chain = registry.get_chain(MediaType.MOVIE)
        assert len(chain) > 0, "Movie chain is empty"
        print(f"\nMovie fallback chain: {[s.value for s in chain]}")

    def test_tv_series_chain_defined(self, registry: MetadataSourceRegistry):
        """TV series fallback chain should be defined."""
        chain = registry.get_chain(MediaType.TV_SERIES)
        assert len(chain) > 0, "TV series chain is empty"
        print(f"\nTV series fallback chain: {[s.value for s in chain]}")

    def test_tv_episode_chain_defined(self, registry: MetadataSourceRegistry):
        """TV episode fallback chain should be defined."""
        chain = registry.get_chain(MediaType.TV_EPISODE)
        assert len(chain) > 0, "TV episode chain is empty"
        print(f"\nTV episode fallback chain: {[s.value for s in chain]}")

    def test_available_sources_for_book(self, registry: MetadataSourceRegistry):
        """Get available sources for book lookups."""
        available = registry.get_available_sources(MediaType.BOOK)
        print(f"\nAvailable sources for books: {[s.value for s in available]}")
        # At minimum, OpenLibrary should be available (no key required)
        assert MetadataSource.OPENLIBRARY in available or len(available) > 0

    def test_available_sources_for_movie(self, registry: MetadataSourceRegistry):
        """Get available sources for movie lookups."""
        available = registry.get_available_sources(MediaType.MOVIE)
        print(f"\nAvailable sources for movies: {[s.value for s in available]}")


# ---------------------------------------------------------------------------
# Wikipedia Fallback Tests
# ---------------------------------------------------------------------------

class TestWikipediaFallback:
    """Test Wikipedia as a fallback source."""

    def test_wikipedia_book_lookup(self, registry: MetadataSourceRegistry, default_options: LookupOptions):
        """Test Wikipedia lookup for a book."""
        client = registry.get_client(MetadataSource.WIKIPEDIA)
        assert client is not None

        query = LookupQuery(
            media_type=MediaType.BOOK,
            title="To Kill a Mockingbird",
            author="Harper Lee",
        )

        result = client.lookup(query, default_options)

        if result:
            print(f"\nWikipedia book lookup:")
            print(f"  Title: {result.title}")
            print(f"  Year: {result.year}")
            print(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")
            print(f"  Wikidata ID: {result.source_ids.wikidata_qid or 'N/A'}")
        else:
            print("\nWikipedia returned no result (may need title refinement)")

    def test_wikipedia_movie_lookup(self, registry: MetadataSourceRegistry, default_options: LookupOptions):
        """Test Wikipedia lookup for a movie."""
        client = registry.get_client(MetadataSource.WIKIPEDIA)
        assert client is not None

        query = LookupQuery(
            media_type=MediaType.MOVIE,
            title="The Shawshank Redemption",
            year=1994,
        )

        result = client.lookup(query, default_options)

        if result:
            print(f"\nWikipedia movie lookup:")
            print(f"  Title: {result.title}")
            print(f"  Year: {result.year}")
            print(f"  Summary: {result.summary[:100] if result.summary else 'N/A'}...")
        else:
            print("\nWikipedia returned no result")


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Test error handling in the pipeline."""

    def test_nonexistent_title_handling(self, pipeline: MetadataLookupPipeline):
        """Pipeline should handle non-existent titles gracefully."""
        query = LookupQuery(
            media_type=MediaType.MOVIE,
            title="This Movie Does Not Exist XYZ123456789",
            year=2099,
        )
        options = LookupOptions(max_sources=2)

        # Should not raise an exception
        result = pipeline.lookup(query, options)

        print(f"\nNon-existent movie lookup result: {result}")
        # Result may be None or low confidence

    def test_empty_query_handling(self, pipeline: MetadataLookupPipeline):
        """Pipeline should handle empty queries gracefully."""
        query = LookupQuery(
            media_type=MediaType.BOOK,
            title="",
        )
        options = LookupOptions(max_sources=1)

        # Should not raise an exception
        result = pipeline.lookup(query, options)

        print(f"\nEmpty query result: {result}")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
