from modules.services.media_metadata_service import _normalize_openlibrary_language
from modules.services.metadata.clients.openlibrary import OpenLibraryClient
from modules.services.metadata.types import LookupOptions, LookupQuery, MediaType


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
