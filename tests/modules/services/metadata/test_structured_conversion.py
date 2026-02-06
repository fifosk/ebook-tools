"""Tests for structured metadata conversion (flat ↔ structured)."""

import pytest

from modules.services.metadata.structured_schema import (
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
from modules.services.metadata.structured_conversion import (
    detect_metadata_version,
    flatten_to_dict,
    normalize_media_metadata,
    structure_from_flat,
)


# ---------------------------------------------------------------------------
# Fixtures — representative flat metadata payloads
# ---------------------------------------------------------------------------


@pytest.fixture()
def flat_book_metadata():
    """A typical flat book metadata dict (legacy v1)."""
    return {
        "book_title": "The Great Gatsby",
        "book_author": "F. Scott Fitzgerald",
        "book_year": "1925",
        "book_summary": "A story of wealth and longing in 1920s America.",
        "book_genre": "Fiction",
        "isbn": "9780743273565",
        "isbn_13": "9780743273565",
        "book_language": "en",
        "input_language": "en",
        "original_language": "en",
        "target_language": "ar",
        "target_languages": ["ar"],
        "translation_provider": "googletrans",
        "translation_model": "googletrans",
        "transliteration_mode": "python",
        "transliteration_model": "sa",
        "transliteration_module": "indic_transliteration",
        "total_sentences": 1234,
        "book_sentence_count": 1234,
        "content_index_path": "metadata/content_index.json",
        "content_index_url": "/api/pipelines/job-123/files/content-index",
        "content_index_summary": {"chapter_count": 12, "alignment": "aligned"},
        "book_cover_file": "/storage/covers/gatsby.jpg",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780743273565-L.jpg",
        "job_cover_asset": "metadata/cover.jpg",
        "job_cover_asset_url": "/api/pipelines/job-123/cover",
        "_enrichment_source": "openlibrary",
        "_enrichment_confidence": "high",
        "openlibrary_work_key": "OL23919A",
        "google_books_id": "iWA-DwAAQBAJ",
        "media_metadata_lookup": {"kind": "book", "provider": "openlibrary"},
        "job_label": "Gatsby — Fitzgerald",
    }


@pytest.fixture()
def flat_tv_metadata():
    """A typical flat TV episode metadata dict."""
    return {
        "book_title": "Breaking Bad S05E16 - Felina",
        "book_author": "Vince Gilligan",
        "book_year": "2013",
        "series_name": "Breaking Bad",
        "season": 5,
        "episode": 16,
        "episode_title": "Felina",
        "series_id": "169",
        "runtime_minutes": 55,
        "rating": 9.9,
        "job_type": "tv_episode",
        "input_language": "en",
        "target_language": "es",
        "target_languages": ["es"],
        "translation_provider": "llm",
        "tmdb_id": 62085,
        "imdb_id": "tt0903747",
    }


@pytest.fixture()
def flat_youtube_metadata():
    """A typical flat YouTube video metadata dict."""
    return {
        "book_title": "How to Build a Spaceship",
        "book_author": "Science Channel",
        "book_year": "2024",
        "youtube_video_id": "dQw4w9WgXcQ",
        "youtube_channel_id": "UC123",
        "channel_name": "Science Channel",
        "upload_date": "2024-01-15",
        "input_language": "en",
        "target_language": "hi",
        "target_languages": ["hi"],
        "translation_provider": "googletrans",
    }


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------


class TestDetectMetadataVersion:
    def test_v1_flat_no_version(self, flat_book_metadata):
        assert detect_metadata_version(flat_book_metadata) == 1

    def test_v2_camel_case(self):
        assert detect_metadata_version({"metadataVersion": 2}) == 2

    def test_v2_snake_case(self):
        assert detect_metadata_version({"metadata_version": 2}) == 2

    def test_empty_dict(self):
        assert detect_metadata_version({}) == 1

    def test_invalid_version(self):
        assert detect_metadata_version({"metadataVersion": "abc"}) == 1


# ---------------------------------------------------------------------------
# Flat → Structured (Book)
# ---------------------------------------------------------------------------


class TestStructureFromFlatBook:
    def test_media_type_detected(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        assert result.media_type == "book"
        assert result.metadata_version == 2

    def test_source_fields(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        assert result.source.title == "The Great Gatsby"
        assert result.source.author == "F. Scott Fitzgerald"
        assert result.source.year == 1925
        assert result.source.summary == "A story of wealth and longing in 1920s America."
        assert result.source.isbn == "9780743273565"
        assert result.source.language == "en"

    def test_source_genres(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        assert result.source.genres == ["Fiction"]

    def test_language_config(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        lc = result.language_config
        assert lc.input_language == "en"
        assert lc.original_language == "en"
        assert lc.target_language == "ar"
        assert lc.target_languages == ["ar"]
        assert lc.translation_provider == "googletrans"
        assert lc.translation_model == "googletrans"
        assert lc.transliteration_mode == "python"
        assert lc.transliteration_model == "sa"
        assert lc.transliteration_module == "indic_transliteration"

    def test_content_structure(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        cs = result.content_structure
        assert cs.total_sentences == 1234
        assert cs.content_index_path == "metadata/content_index.json"
        assert cs.content_index_url == "/api/pipelines/job-123/files/content-index"
        assert cs.content_index_summary == {"chapter_count": 12, "alignment": "aligned"}

    def test_cover_assets(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        ca = result.cover_assets
        assert ca.cover_file == "/storage/covers/gatsby.jpg"
        assert ca.cover_url == "https://covers.openlibrary.org/b/isbn/9780743273565-L.jpg"
        assert ca.job_cover_asset == "metadata/cover.jpg"
        assert ca.job_cover_asset_url == "/api/pipelines/job-123/cover"

    def test_enrichment(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        e = result.enrichment
        assert e.source == "openlibrary"
        assert e.confidence == "high"
        assert e.lookup_result == {"kind": "book", "provider": "openlibrary"}
        assert e.source_ids is not None
        assert e.source_ids.openlibrary == "OL23919A"
        assert e.source_ids.google_books == "iWA-DwAAQBAJ"

    def test_job_label(self, flat_book_metadata):
        result = structure_from_flat(flat_book_metadata)
        assert result.job_label == "Gatsby — Fitzgerald"


# ---------------------------------------------------------------------------
# Flat → Structured (TV)
# ---------------------------------------------------------------------------


class TestStructureFromFlatTV:
    def test_media_type_detected(self, flat_tv_metadata):
        result = structure_from_flat(flat_tv_metadata)
        assert result.media_type == "tv_episode"

    def test_series_info(self, flat_tv_metadata):
        result = structure_from_flat(flat_tv_metadata)
        assert result.source.series is not None
        assert result.source.series.series_title == "Breaking Bad"
        assert result.source.series.season == 5
        assert result.source.series.episode == 16
        assert result.source.series.episode_title == "Felina"
        assert result.source.series.series_id == "169"

    def test_movie_tv_extras(self, flat_tv_metadata):
        result = structure_from_flat(flat_tv_metadata)
        assert result.source.runtime_minutes == 55
        assert result.source.rating == 9.9

    def test_enrichment_source_ids(self, flat_tv_metadata):
        result = structure_from_flat(flat_tv_metadata)
        assert result.enrichment.source_ids is not None
        assert result.enrichment.source_ids.tmdb == 62085
        assert result.enrichment.source_ids.imdb == "tt0903747"


# ---------------------------------------------------------------------------
# Flat → Structured (YouTube)
# ---------------------------------------------------------------------------


class TestStructureFromFlatYouTube:
    def test_media_type_detected(self, flat_youtube_metadata):
        result = structure_from_flat(flat_youtube_metadata)
        assert result.media_type == "youtube_video"

    def test_youtube_info(self, flat_youtube_metadata):
        result = structure_from_flat(flat_youtube_metadata)
        assert result.source.youtube is not None
        assert result.source.youtube.video_id == "dQw4w9WgXcQ"
        assert result.source.youtube.channel_id == "UC123"
        assert result.source.youtube.channel_name == "Science Channel"
        assert result.source.youtube.upload_date == "2024-01-15"


# ---------------------------------------------------------------------------
# Structured → Flat (round-trip)
# ---------------------------------------------------------------------------


class TestFlattenToDict:
    def test_round_trip_book_preserves_keys(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        flat = flatten_to_dict(structured)
        # Core identity
        assert flat["book_title"] == "The Great Gatsby"
        assert flat["book_author"] == "F. Scott Fitzgerald"
        assert flat["book_year"] == "1925"  # back to string
        assert flat["isbn"] == "9780743273565"

    def test_round_trip_book_language(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        flat = flatten_to_dict(structured)
        assert flat["input_language"] == "en"
        assert flat["target_language"] == "ar"
        assert flat["target_languages"] == ["ar"]
        assert flat["translation_provider"] == "googletrans"

    def test_round_trip_book_content(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        flat = flatten_to_dict(structured)
        assert flat["total_sentences"] == 1234
        assert flat["book_sentence_count"] == 1234
        assert flat["content_index_path"] == "metadata/content_index.json"

    def test_round_trip_book_cover(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        flat = flatten_to_dict(structured)
        assert flat["book_cover_file"] == "/storage/covers/gatsby.jpg"
        assert flat["job_cover_asset"] == "metadata/cover.jpg"

    def test_round_trip_book_enrichment(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        flat = flatten_to_dict(structured)
        assert flat["_enrichment_source"] == "openlibrary"
        assert flat["_enrichment_confidence"] == "high"
        assert flat["openlibrary_work_key"] == "OL23919A"
        assert flat["google_books_id"] == "iWA-DwAAQBAJ"
        assert flat["media_metadata_lookup"] == {"kind": "book", "provider": "openlibrary"}

    def test_round_trip_book_job_label(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        flat = flatten_to_dict(structured)
        assert flat["job_label"] == "Gatsby — Fitzgerald"

    def test_round_trip_tv_series_fields(self, flat_tv_metadata):
        structured = structure_from_flat(flat_tv_metadata)
        flat = flatten_to_dict(structured)
        assert flat["series_name"] == "Breaking Bad"
        assert flat["season"] == 5
        assert flat["episode"] == 16
        assert flat["episode_title"] == "Felina"

    def test_round_trip_youtube_fields(self, flat_youtube_metadata):
        structured = structure_from_flat(flat_youtube_metadata)
        flat = flatten_to_dict(structured)
        assert flat["youtube_video_id"] == "dQw4w9WgXcQ"
        assert flat["youtube_channel_id"] == "UC123"
        assert flat["channel_name"] == "Science Channel"

    def test_genre_singular_preserved(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        flat = flatten_to_dict(structured)
        assert flat["book_genre"] == "Fiction"
        assert flat["book_genres"] == ["Fiction"]


# ---------------------------------------------------------------------------
# Extras preservation
# ---------------------------------------------------------------------------


class TestExtrasPreservation:
    def test_unknown_keys_in_extras(self):
        flat = {
            "book_title": "Test",
            "custom_field_1": "value1",
            "my_plugin_data": {"nested": True},
        }
        structured = structure_from_flat(flat)
        assert "custom_field_1" in structured.extras
        assert structured.extras["custom_field_1"] == "value1"
        assert structured.extras["my_plugin_data"] == {"nested": True}

    def test_extras_round_trip(self):
        flat = {
            "book_title": "Test",
            "unknown_key": 42,
        }
        structured = structure_from_flat(flat)
        flat2 = flatten_to_dict(structured)
        assert flat2["unknown_key"] == 42

    def test_processing_config_excluded_from_extras(self):
        flat = {
            "book_title": "Test",
            "add_images": True,
            "audio_mode": "translation",
            "selected_voice": "Google US English",
        }
        structured = structure_from_flat(flat)
        # Processing config keys are known/excluded, not in extras
        assert "add_images" not in structured.extras
        assert "audio_mode" not in structured.extras
        assert "selected_voice" not in structured.extras


# ---------------------------------------------------------------------------
# normalize_media_metadata (auto-detect)
# ---------------------------------------------------------------------------


class TestNormalizeMediaMetadata:
    def test_v1_flat_auto_detects(self, flat_book_metadata):
        result = normalize_media_metadata(flat_book_metadata)
        assert result.metadata_version == 2
        assert result.source.title == "The Great Gatsby"

    def test_v2_structured_passthrough(self):
        structured_dict = {
            "metadataVersion": 2,
            "mediaType": "book",
            "source": {"title": "Test Book", "author": "Author"},
            "languageConfig": {"inputLanguage": "en"},
            "contentStructure": {},
            "coverAssets": {},
            "enrichment": {},
        }
        result = normalize_media_metadata(structured_dict)
        assert result.metadata_version == 2
        assert result.source.title == "Test Book"
        assert result.language_config.input_language == "en"

    def test_empty_dict_produces_defaults(self):
        result = normalize_media_metadata({})
        assert result.metadata_version == 2
        assert result.media_type == "book"
        assert result.source.title is None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_camel_dict(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        d = structured.to_camel_dict()
        assert d["metadataVersion"] == 2
        assert d["mediaType"] == "book"
        assert d["source"]["title"] == "The Great Gatsby"
        assert d["languageConfig"]["inputLanguage"] == "en"
        assert d["contentStructure"]["totalSentences"] == 1234
        assert d["coverAssets"]["coverFile"] == "/storage/covers/gatsby.jpg"
        assert d["enrichment"]["source"] == "openlibrary"
        assert d["jobLabel"] == "Gatsby — Fitzgerald"

    def test_v2_dict_round_trip_through_pydantic(self, flat_book_metadata):
        structured = structure_from_flat(flat_book_metadata)
        d = structured.to_camel_dict()
        reloaded = StructuredMediaMetadata.model_validate(d)
        assert reloaded.source.title == structured.source.title
        assert reloaded.language_config.target_languages == structured.language_config.target_languages
        assert reloaded.enrichment.source == structured.enrichment.source


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_year_as_string(self):
        flat = {"book_year": "2024"}
        result = structure_from_flat(flat)
        assert result.source.year == 2024

    def test_year_as_int(self):
        flat = {"book_year": 2024}
        result = structure_from_flat(flat)
        assert result.source.year == 2024

    def test_year_invalid(self):
        flat = {"book_year": "unknown"}
        result = structure_from_flat(flat)
        assert result.source.year is None

    def test_total_sentences_coercion(self):
        flat = {"total_sentences": "500"}
        result = structure_from_flat(flat)
        assert result.content_structure.total_sentences == 500

    def test_translation_language_alias(self):
        flat = {"translation_language": "fr"}
        result = structure_from_flat(flat)
        assert result.language_config.target_language == "fr"

    def test_book_metadata_lookup_alias(self):
        flat = {"book_metadata_lookup": {"kind": "book"}}
        result = structure_from_flat(flat)
        assert result.enrichment.lookup_result == {"kind": "book"}

    def test_both_lookups_prefer_media(self):
        flat = {
            "media_metadata_lookup": {"kind": "media"},
            "book_metadata_lookup": {"kind": "book_fallback"},
        }
        result = structure_from_flat(flat)
        assert result.enrichment.lookup_result == {"kind": "media"}

    def test_genres_list_preferred_over_singular(self):
        flat = {
            "book_genre": "Fiction",
            "book_genres": ["Fiction", "Classic"],
        }
        result = structure_from_flat(flat)
        assert result.source.genres == ["Fiction", "Classic"]

    def test_minimal_metadata(self):
        flat = {"book_title": "Untitled"}
        result = structure_from_flat(flat)
        assert result.source.title == "Untitled"
        assert result.media_type == "book"
        assert result.language_config.input_language is None

    def test_movie_detection(self):
        flat = {"imdb_id": "tt1234567", "book_title": "Some Movie"}
        result = structure_from_flat(flat)
        assert result.media_type == "movie"
