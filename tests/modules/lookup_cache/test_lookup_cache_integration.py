"""Integration tests for lookup cache persistence."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from modules.lookup_cache import (
    LookupCache,
    LookupCacheEntry,
    LookupCacheManager,
    load_lookup_cache,
    normalize_word,
)


# Sample Arabic sentences (30 sentences from typical book content)
SAMPLE_ARABIC_SENTENCES = [
    "مرحباً بك في عالم القراءة الممتع.",
    "الكتاب خير جليس في الزمان.",
    "العلم نور والجهل ظلام.",
    "القراءة تفتح آفاقاً جديدة.",
    "المعرفة قوة لا تُقهر.",
    "الحكمة ضالة المؤمن.",
    "من جدّ وجد ومن زرع حصد.",
    "الصبر مفتاح الفرج.",
    "العقل السليم في الجسم السليم.",
    "التعلم في الصغر كالنقش على الحجر.",
    "الوقت كالسيف إن لم تقطعه قطعك.",
    "أطلبوا العلم من المهد إلى اللحد.",
    "خير الكلام ما قل ودل.",
    "الصديق وقت الضيق.",
    "رُبّ أخٍ لك لم تلده أمك.",
    "من صبر ظفر.",
    "العلم في الصدر كالثمر على الشجر.",
    "لكل مقام مقال.",
    "الاتحاد قوة والتفرق ضعف.",
    "إذا هبت رياحك فاغتنمها.",
    "المثابرة طريق النجاح.",
    "الأمانة خلق الأنبياء.",
    "الصدق منجاة والكذب مهلكة.",
    "الإنسان بأعماله لا بأقواله.",
    "القناعة كنز لا يفنى.",
    "احترم نفسك يحترمك الناس.",
    "التواضع من شيم الكرام.",
    "الحياة مدرسة والناس معلمون.",
    "السعادة في راحة البال.",
    "الأمل يصنع المعجزات.",
]


def create_mock_llm_response(words: List[str]) -> Dict[str, Any]:
    """Create a mock LLM response for word lookups."""
    items = []
    for idx, word in enumerate(words):
        items.append({
            "id": idx,
            "word": word,
            "type": "word",
            "definition": f"Definition for {word}",
            "part_of_speech": "noun",
            "pronunciation": None,
            "etymology": None,
            "example": f"Example sentence with {word}.",
            "example_translation": None,
            "example_transliteration": None,
            "related_languages": None,
        })
    return {"items": items}


class TestLookupCacheManager:
    """Test the LookupCacheManager class."""

    def test_manager_initialization(self, tmp_path: Path) -> None:
        """Test manager initializes correctly."""
        manager = LookupCacheManager(
            job_id="test-job",
            job_dir=tmp_path,
            input_language="Arabic",
            definition_language="English",
        )

        assert manager.job_id == "test-job"
        assert manager.job_dir == tmp_path
        assert manager._input_language == "Arabic"
        assert manager._definition_language == "English"

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Test that save() creates the lookup_cache.json file."""
        manager = LookupCacheManager(
            job_id="test-job",
            job_dir=tmp_path,
            input_language="Arabic",
            definition_language="English",
        )

        # Add a test entry
        entry = LookupCacheEntry(
            word="كتاب",
            word_normalized="كتاب",
            input_language="Arabic",
            definition_language="English",
            lookup_result={"type": "word", "definition": "book"},
            audio_references=[],
        )
        manager.add_entry(entry)

        # Save
        manager.save()

        # Verify file exists
        cache_path = tmp_path / "metadata" / "lookup_cache.json"
        assert cache_path.exists(), f"Cache file not created at {cache_path}"

        # Verify content
        with open(cache_path) as f:
            data = json.load(f)
        assert "entries" in data
        assert len(data["entries"]) == 1

    def test_load_existing_cache(self, tmp_path: Path) -> None:
        """Test loading an existing cache."""
        # Create metadata dir and cache file
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir(parents=True)

        cache_data = {
            "job_id": "test-job",
            "input_language": "Arabic",
            "definition_language": "English",
            "entries": {
                "كتاب": {
                    "word": "كتاب",
                    "word_normalized": "كتاب",
                    "input_language": "Arabic",
                    "definition_language": "English",
                    "lookup_result": {"type": "word", "definition": "book"},
                    "audio_references": [],
                    "created_at": 1234567890.0,
                }
            },
            "stats": {
                "total_words": 1,
                "total_audio_refs": 0,
                "llm_calls": 1,
                "skipped_stopwords": 0,
                "build_time_seconds": 0.5,
            },
            "version": "1.0",
        }

        cache_path = metadata_dir / "lookup_cache.json"
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        # Load via manager
        manager = LookupCacheManager(
            job_id="test-job",
            job_dir=tmp_path,
        )

        # Access cache to trigger load
        entry = manager.get("كتاب")
        assert entry is not None
        assert entry.word == "كتاب"
        assert entry.lookup_result["definition"] == "book"


class TestLookupCacheIntegration:
    """Integration tests for the full lookup cache workflow."""

    def test_build_from_sentences_and_persist(self, tmp_path: Path) -> None:
        """Test building cache from sentences and persisting to disk."""
        # Create a mock LLM client
        mock_client = MagicMock()
        mock_client.model = "test-model"

        def mock_request(*args, **kwargs):
            # Extract words from the request
            items = kwargs.get("items", [])
            words = [item.get("text", "") for item in items]
            response = MagicMock()
            response.payload = create_mock_llm_response(words)
            response.raw_text = json.dumps(response.payload)
            response.error = None
            response.elapsed = 0.1
            return response

        with patch("modules.llm_batch.request_json_batch", side_effect=mock_request):
            manager = LookupCacheManager(
                job_id="test-job",
                job_dir=tmp_path,
                input_language="Arabic",
                definition_language="English",
            )

            # Build from sample sentences
            new_count = manager.build_from_sentences(
                sentences=SAMPLE_ARABIC_SENTENCES[:10],  # Use first 10 sentences
                llm_client=mock_client,
                batch_size=5,
                skip_stopwords=True,
            )

            # Save to disk
            manager.save()

            # Verify file was created
            cache_path = tmp_path / "metadata" / "lookup_cache.json"
            assert cache_path.exists(), f"Cache file not created at {cache_path}"

            # Load and verify
            loaded_cache = load_lookup_cache(tmp_path)
            assert loaded_cache is not None
            assert loaded_cache.stats.total_words > 0

    def test_normalize_word_strips_arabic_diacritics(self) -> None:
        """Test that Arabic diacritics are stripped during normalization."""
        # Word with full tashkeel
        with_diacritics = "كِتَابٌ"
        # Same word without diacritics
        without_diacritics = "كتاب"

        normalized_with = normalize_word(with_diacritics)
        normalized_without = normalize_word(without_diacritics)

        assert normalized_with == normalized_without, (
            f"Diacritic normalization failed: '{normalized_with}' != '{normalized_without}'"
        )

    def test_cache_lookup_with_diacritics(self, tmp_path: Path) -> None:
        """Test that cache lookup works with Arabic diacritics."""
        manager = LookupCacheManager(
            job_id="test-job",
            job_dir=tmp_path,
            input_language="Arabic",
            definition_language="English",
        )

        # Add entry without diacritics
        entry = LookupCacheEntry(
            word="كتاب",
            word_normalized=normalize_word("كتاب"),
            input_language="Arabic",
            definition_language="English",
            lookup_result={"type": "word", "definition": "book"},
            audio_references=[],
        )
        manager.add_entry(entry)

        # Lookup with diacritics should still find it
        found = manager.get("كِتَابٌ")
        assert found is not None, "Cache lookup with diacritics failed"
        assert found.lookup_result["definition"] == "book"


class TestLookupCachePhase:
    """Test the lookup cache pipeline phase."""

    def test_extract_sentences_from_chunk_files(self, tmp_path: Path) -> None:
        """Test that sentences are extracted from chunk metadata files."""
        from modules.services.pipeline_phases.lookup_cache_phase import _load_chunk_metadata

        # Create chunk metadata file
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir(parents=True)

        chunk_data = {
            "chunk_id": "test-chunk",
            "sentences": [
                {"translation": "مرحباً بك في عالم القراءة."},
                {"translation": "الكتاب خير جليس."},
                {"text": "العلم نور."},  # Fallback to 'text' key
            ],
        }

        chunk_path = metadata_dir / "chunk_0000.json"
        with open(chunk_path, "w") as f:
            json.dump(chunk_data, f)

        # Load chunk metadata
        loaded = _load_chunk_metadata(tmp_path, "metadata/chunk_0000.json")
        assert loaded is not None
        assert "sentences" in loaded
        assert len(loaded["sentences"]) == 3

    def test_phase_creates_cache_file(self, tmp_path: Path) -> None:
        """Test that the phase creates the lookup_cache.json file."""
        from unittest.mock import MagicMock

        # Create job structure
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir(parents=True)

        # Create chunk metadata
        chunk_data = {
            "chunk_id": "test-chunk",
            "sentences": [
                {"translation": sent}
                for sent in SAMPLE_ARABIC_SENTENCES[:5]
            ],
        }
        with open(metadata_dir / "chunk_0000.json", "w") as f:
            json.dump(chunk_data, f)

        # Create mock objects
        mock_request = MagicMock()
        mock_request.inputs = MagicMock()
        mock_request.inputs.input_language = "Arabic"
        mock_request.inputs.target_languages = ["English"]
        mock_request.inputs.enable_lookup_cache = True
        mock_request.inputs.lookup_cache_batch_size = 10
        mock_request.job_id = "test-job"
        mock_request.stop_event = None

        mock_config_result = MagicMock()
        mock_config_result.pipeline_config = MagicMock()
        mock_config_result.pipeline_config.translation_client = None

        mock_render_result = MagicMock()
        mock_render_result.base_dir = str(tmp_path / "media" / "output")

        mock_tracker = MagicMock()
        mock_tracker.get_generated_files.return_value = {
            "chunks": [
                {"metadata_path": "metadata/chunk_0000.json"}
            ]
        }

        # Create media/output directory structure
        (tmp_path / "media" / "output").mkdir(parents=True)

        # Mock LLM client
        mock_llm_client = MagicMock()
        mock_llm_client.model = "test-model"

        def mock_request_json(*args, **kwargs):
            items = kwargs.get("items", [])
            words = [item.get("text", "") for item in items]
            response = MagicMock()
            response.payload = create_mock_llm_response(words)
            response.raw_text = json.dumps(response.payload)
            response.error = None
            response.elapsed = 0.1
            return response

        with patch("modules.llm_batch.request_json_batch", side_effect=mock_request_json):
            with patch("modules.llm_client_manager.client_scope") as mock_scope:
                mock_scope.return_value.__enter__ = MagicMock(return_value=mock_llm_client)
                mock_scope.return_value.__exit__ = MagicMock(return_value=False)

                from modules.services.pipeline_phases.lookup_cache_phase import build_lookup_cache_phase

                result = build_lookup_cache_phase(
                    mock_request,
                    mock_config_result,
                    mock_render_result,
                    mock_tracker,
                )

        # Verify cache file was created
        cache_path = tmp_path / "metadata" / "lookup_cache.json"
        assert cache_path.exists(), f"Cache file not created at {cache_path}"

        # Verify content
        with open(cache_path) as f:
            data = json.load(f)
        assert "entries" in data
        assert data["stats"]["total_words"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
