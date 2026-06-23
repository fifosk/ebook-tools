from datetime import datetime, timezone

from modules.services.media_metadata_service import _normalize_openlibrary_language
from modules.services.media_metadata_service import BookLookupQuery, MediaMetadataService
from modules.services.job_manager.job import PipelineJob, PipelineJobStatus
from modules.services.pipeline_service import PipelineInput, PipelineRequest
from modules.services.pipeline_types import PipelineMetadata
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


def test_persisted_lookup_keeps_book_isbn_and_genre_aliases() -> None:
    request = PipelineRequest(
        config={},
        context=None,
        environment_overrides={},
        pipeline_overrides={},
        inputs=PipelineInput(
            input_file="input.epub",
            base_output_file="output",
            input_language="en",
            target_languages=["en"],
            sentences_per_output_file=10,
            start_sentence=0,
            end_sentence=None,
            stitch_full=False,
            generate_audio=True,
            audio_mode="tts",
            written_mode="text",
            selected_voice="voice",
            output_html=False,
            output_pdf=False,
            add_images=False,
            include_transliteration=False,
            tempo=1.0,
            media_metadata=PipelineMetadata(),
        ),
    )

    class StubJobManager:
        def __init__(self) -> None:
            self.job = PipelineJob(
                job_id="job-1",
                status=PipelineJobStatus.COMPLETED,
                created_at=datetime.now(timezone.utc),
                request=request,
                request_payload={"inputs": {"media_metadata": {}}, "config": {}},
                job_type="book",
            )

        def mutate_job(self, _job_id: str, mutator, **_kwargs):
            mutator(self.job)
            return self.job

    manager = StubJobManager()
    service = object.__new__(MediaMetadataService)
    service._job_manager = manager

    service._persist_lookup_result(
        "job-1",
        {
            "kind": "book",
            "provider": "openlibrary",
            "queried_at": "2026-06-23T12:00:00+00:00",
            "job_label": "Example Book - Jane Doe",
            "book": {
                "title": "Example Book",
                "author": "Jane Doe",
                "isbn": "9780140328721",
                "book_isbn": "9780140328721",
                "genre": "Adventure, Fantasy",
                "book_genre": "Adventure, Fantasy",
                "book_genres": ["Adventure", "Fantasy", ""],
            },
        },
        user_id=None,
        user_role=None,
    )

    request_payload = manager.job.request_payload
    media_metadata = request_payload["inputs"]["media_metadata"]
    config = request_payload["config"]

    assert media_metadata["book_isbn"] == "9780140328721"
    assert media_metadata["book_genre"] == "Adventure, Fantasy"
    assert media_metadata["book_genres"] == ["Adventure", "Fantasy"]
    assert config["book_isbn"] == "9780140328721"
    assert config["book_genre"] == "Adventure, Fantasy"
    assert config["book_genres"] == ["Adventure", "Fantasy"]
    assert manager.job.request is not None
    assert manager.job.request.config["book_isbn"] == "9780140328721"
    assert manager.job.request.config["book_genre"] == "Adventure, Fantasy"
    assert manager.job.request.config["book_genres"] == ["Adventure", "Fantasy"]
    assert manager.job.request.inputs.media_metadata.as_dict()["book_genres"] == ["Adventure", "Fantasy"]
