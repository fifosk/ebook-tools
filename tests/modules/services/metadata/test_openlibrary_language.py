from modules.services.media_metadata_service import _normalize_openlibrary_language
from modules.services.media_metadata_service import BookLookupQuery, MediaMetadataService
from modules.services.metadata.clients.openlibrary import OpenLibraryClient
from modules.services.metadata.types import (
    ConfidenceLevel,
    LookupOptions,
    LookupQuery,
    MediaType,
    MetadataSource,
    SourceIds,
    UnifiedMetadataResult,
)


def test_normalizes_openlibrary_language_payloads() -> None:
    assert _normalize_openlibrary_language([{"key": "/languages/eng"}]) == "eng"
    assert _normalize_openlibrary_language(["fre"]) == "fre"
    assert _normalize_openlibrary_language({"name": "English"}) == "English"
    assert _normalize_openlibrary_language([]) is None


def test_openlibrary_isbn_parser_preserves_language() -> None:
    client = object.__new__(OpenLibraryClient)

    result = client._parse_isbn_response(
        {
            "title": "Example Book",
            "authors": [{"name": "Jane Doe"}],
            "languages": [{"key": "/languages/eng"}],
            "publish_date": "2025",
            "subjects": ["Adventure"],
            "key": "/books/OL1M",
        },
        LookupQuery(media_type=MediaType.BOOK, title=None, author=None, isbn="9780140328721"),
        LookupOptions(download_cover=False),
    )

    assert result.language == "eng"
    assert result.to_dict()["language"] == "eng"


def test_google_books_fallback_preserves_language_and_genre_aliases() -> None:
    class StubGoogleBooks:
        def lookup(self, _query: LookupQuery, _options: LookupOptions) -> UnifiedMetadataResult:
            return UnifiedMetadataResult(
                title="Example Book",
                type=MediaType.BOOK,
                year=2025,
                genres=["Adventure", "Fantasy"],
                summary="A compact test fixture.",
                source_ids=SourceIds(isbn_13="9780140328721", google_books_id="gb-1"),
                confidence=ConfidenceLevel.HIGH,
                primary_source=MetadataSource.GOOGLE_BOOKS,
                contributing_sources=[MetadataSource.GOOGLE_BOOKS],
                author="Jane Doe",
                language="en",
            )

    service = object.__new__(MediaMetadataService)
    service._google_books = StubGoogleBooks()

    payload = service._try_google_books_fallback(
        BookLookupQuery(title="Example Book", author="Jane Doe", isbn=None, source_name="example.epub"),
        job_id=None,
    )

    assert payload is not None
    assert payload["provider"] == "google_books"
    assert payload["book"]["language"] == "en"
    assert payload["book"]["book_language"] == "en"
    assert payload["book"]["book_isbn"] == "9780140328721"
    assert payload["book"]["genre"] == "Adventure, Fantasy"
    assert payload["book"]["book_genre"] == "Adventure, Fantasy"
    assert payload["book"]["book_genres"] == ["Adventure", "Fantasy"]


def test_pipeline_result_payload_exposes_web_aligned_book_aliases() -> None:
    service = object.__new__(MediaMetadataService)

    payload = service._convert_pipeline_result_to_payload(
        UnifiedMetadataResult(
            title="Example Book",
            type=MediaType.BOOK,
            year=2025,
            genres=["Adventure", "Fantasy"],
            source_ids=SourceIds(isbn="0140328726"),
            confidence=ConfidenceLevel.HIGH,
            primary_source=MetadataSource.OPENLIBRARY,
            contributing_sources=[MetadataSource.OPENLIBRARY],
            author="Jane Doe",
            language="en",
        ),
        BookLookupQuery(title="Example Book", author="Jane Doe", isbn=None, source_name="example.epub"),
    )

    book = payload["book"]
    assert book["isbn"] == "0140328726"
    assert book["book_isbn"] == "0140328726"
    assert book["genre"] == "Adventure, Fantasy"
    assert book["book_genre"] == "Adventure, Fantasy"
    assert book["book_genres"] == ["Adventure", "Fantasy"]
