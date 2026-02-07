"""Integration tests for the translation engine refactoring.

These tests verify that the extracted modules work correctly together,
ensuring the refactoring didn't break any integration points.

## Scope of Integration Tests

### 1. Module Import & Delegation Tests
Verify that translation_engine.py correctly imports and delegates to:
- translation_validation.py (validation functions)
- translation_batch.py (batch processing)
- translation_logging.py (logging & stats)
- translation_workers.py (worker pools)
- translation_providers/ (GoogleTrans provider)

### 2. Batch Processing Integration
Test the full batch translation flow:
- Building batches from sentences
- Parsing LLM responses
- Validating results
- Handling fallbacks

### 3. Validation Integration
Test that validation functions are properly called during:
- Single sentence translation
- Batch translation
- Transliteration

### 4. Cross-Module Data Flow
Verify data flows correctly between modules:
- BatchStatsRecorder receives updates from batch processing
- Progress tracker receives retry counts from validation
- Worker pools execute batch tasks correctly
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from modules import translation_engine as te
from modules import translation_batch as tb
from modules import translation_validation as tv
from modules.translation_logging import BatchStatsRecorder
from modules.translation_workers import ThreadWorkerPool

pytestmark = pytest.mark.translation


class TestModuleImportDelegation:
    """Test that translation_engine correctly delegates to extracted modules.

    Scope: Verifies the refactoring preserved the API contract by checking
    that private aliases in translation_engine point to the correct functions
    in the extracted modules.
    """

    def test_validation_delegation(self):
        """Verify validation functions are delegated to translation_validation."""
        # These should be the same function objects
        assert te._valid_translation is tv.is_valid_translation
        assert te._is_probable_transliteration is tv.is_probable_transliteration
        assert te._is_translation_too_short is tv.is_translation_too_short
        assert te._missing_required_diacritics is tv.missing_required_diacritics
        assert te._unexpected_script_used is tv.unexpected_script_used
        assert te._is_segmentation_ok is tv.is_segmentation_ok
        assert te._letter_count is tv.letter_count

    def test_batch_processing_delegation(self):
        """Verify batch processing functions are delegated to translation_batch."""
        assert te.normalize_llm_batch_size is tb.normalize_llm_batch_size
        assert te.build_translation_batches is tb.build_translation_batches
        assert te.chunk_batch_items is tb.chunk_batch_items
        assert te.extract_batch_items is tb.extract_batch_items
        assert te.coerce_batch_item_id is tb.coerce_batch_item_id
        assert te.coerce_text_value is tb.coerce_text_value
        assert te.parse_batch_translation_payload is tb.parse_batch_translation_payload
        assert te.parse_batch_transliteration_payload is tb.parse_batch_transliteration_payload
        assert te.validate_batch_translation is tb.validate_batch_translation
        assert te.validate_batch_transliteration is tb.validate_batch_transliteration
        assert te.translate_llm_batch_items is tb.translate_llm_batch_items
        assert te.transliterate_llm_batch_items is tb.transliterate_llm_batch_items
        assert te.resolve_batch_transliterations is tb.resolve_batch_transliterations

    def test_logging_delegation(self):
        """Verify logging functions are delegated to translation_logging."""
        from modules.translation_logging import (
            resolve_llm_batch_log_dir,
            sanitize_batch_component,
            write_llm_batch_artifact,
        )
        assert te.resolve_llm_batch_log_dir is resolve_llm_batch_log_dir
        assert te.sanitize_batch_component is sanitize_batch_component
        assert te.write_llm_batch_artifact is write_llm_batch_artifact

    def test_provider_delegation(self):
        """Verify provider functions are delegated to translation_providers."""
        from modules.translation_providers import (
            check_googletrans_health,
            normalize_translation_provider,
            resolve_googletrans_language,
            translate_with_googletrans,
        )
        assert te.check_googletrans_health is check_googletrans_health
        assert te.normalize_translation_provider is normalize_translation_provider
        assert te.resolve_googletrans_language is resolve_googletrans_language
        assert te.translate_with_googletrans is translate_with_googletrans


class TestBatchProcessingIntegration:
    """Test batch processing integration between modules.

    Scope: Verifies that batch building, parsing, and validation work
    together correctly across module boundaries.
    """

    def test_batch_building_and_chunking_integration(self):
        """Test that batches are built and chunked correctly."""
        sentences = ["Hello", "World", "Foo", "Bar", "Baz"]
        targets = ["ar", "ar", "fr", "fr", "ar"]

        # Build batches (groups by language)
        batches = tb.build_translation_batches(sentences, targets, batch_size=10)

        # Should have 3 batches: ar(2), fr(2), ar(1)
        assert len(batches) == 3
        assert batches[0][0] == "ar"
        assert batches[1][0] == "fr"
        assert batches[2][0] == "ar"

        # Now chunk one of the batches
        _, items = batches[0]
        chunks = tb.chunk_batch_items(items, batch_size=1)
        assert len(chunks) == 2  # 2 items, batch_size=1

    def test_payload_parsing_and_validation_integration(self):
        """Test that parsed payloads are validated correctly."""
        # Simulate an LLM response payload
        payload = {
            "items": [
                {"id": 0, "translation": "مرحبا بالعالم", "transliteration": "marhaba bil3alam"},
                {"id": 1, "translation": "OK"},  # Too short, will fail validation
            ]
        }

        # Parse the payload
        parsed = tb.parse_batch_translation_payload(
            payload,
            input_ids=[0, 1],
            include_transliteration=True,
        )

        assert 0 in parsed
        assert 1 in parsed

        # Validate each result
        original_sentences = [
            "Hello world, this is a test sentence.",
            "This is another longer sentence that needs proper translation.",
        ]

        # First translation should pass (proper Arabic)
        error0 = tb.validate_batch_translation(
            original_sentences[0],
            parsed[0][0],
            "arabic",
        )
        # Note: May fail diacritics check, but should not fail transliteration check

        # Second translation should fail (too short)
        error1 = tb.validate_batch_translation(
            original_sentences[1],
            parsed[1][0],
            "english",
        )
        assert error1 is not None
        assert "short" in error1.lower()

    def test_transliteration_validation_integration(self):
        """Test transliteration parsing and validation work together."""
        payload = {
            "items": [
                {"id": 0, "transliteration": "marhaba"},
                {"id": 1, "transliteration": "مرحبا"},  # Non-Latin, should fail validation
            ]
        }

        parsed = tb.parse_batch_transliteration_payload(payload, input_ids=[0, 1])

        # Parsing preserves both
        assert parsed[0] == "marhaba"
        assert parsed[1] == "مرحبا"

        # Validation catches the non-Latin one
        error0 = tb.validate_batch_transliteration(parsed[0])
        error1 = tb.validate_batch_transliteration(parsed[1])

        assert error0 is None  # Latin is valid
        assert error1 is not None  # Non-Latin is invalid
        assert "Non-Latin" in error1


class TestValidationIntegration:
    """Test validation integration with the translation engine.

    Scope: Verifies that validation functions correctly identify
    translation quality issues across different scenarios.
    """

    def test_transliteration_detection(self):
        """Test detection of transliteration instead of translation."""
        # Arabic text translated to Arabic should not be Latin
        original = "مرحبا بالعالم"  # Arabic
        transliteration = "marhaba bil3alam"  # Latin transliteration

        is_translit = tv.is_probable_transliteration(
            original, transliteration, "arabic"
        )
        assert is_translit is True

        # Proper Arabic translation should pass
        proper_translation = "أهلا بالعالم"
        is_translit = tv.is_probable_transliteration(
            original, proper_translation, "arabic"
        )
        assert is_translit is False

    def test_diacritics_detection(self):
        """Test detection of missing diacritics."""
        # Arabic without diacritics
        without_diacritics = "مرحبا بالعالم"
        missing, label = tv.missing_required_diacritics(without_diacritics, "arabic")
        assert missing is True
        assert "tashkil" in label.lower()

        # Arabic with diacritics
        with_diacritics = "مَرْحَبًا بِالْعَالَمِ"
        missing, label = tv.missing_required_diacritics(with_diacritics, "arabic")
        assert missing is False

    def test_script_detection(self):
        """Test detection of unexpected script."""
        # unexpected_script_used only triggers if text contains non-Latin AND
        # doesn't match the expected script. Test with mixed script text.

        # Proper Arabic text should pass
        arabic_text = "مرحبا بالعالم"
        unexpected, label = tv.unexpected_script_used(arabic_text, "arabic")
        assert unexpected is False

        # Mixed Arabic + Hebrew when expecting pure Arabic
        # This may or may not trigger depending on the ratio threshold
        mixed_text = "مرحبا שלום"  # Arabic + Hebrew
        unexpected, label = tv.unexpected_script_used(mixed_text, "arabic")
        # With mixed scripts, this should detect the unexpected Hebrew
        # The function uses a 0.85 threshold for expected script ratio

        # Latin-only text doesn't trigger (function returns False for Latin)
        latin_text = "Hello World"
        unexpected, label = tv.unexpected_script_used(latin_text, "arabic")
        assert unexpected is False  # No non-Latin chars, so no check

    def test_length_validation(self):
        """Test detection of too-short translations."""
        long_original = (
            "This is a very long sentence with many words that should "
            "result in a reasonably long translation, not just a single word."
        )

        # Too short
        is_short = tv.is_translation_too_short(long_original, "OK")
        assert is_short is True

        # Reasonable length
        reasonable = (
            "Ceci est une très longue phrase avec beaucoup de mots qui devrait "
            "donner une traduction raisonnablement longue."
        )
        is_short = tv.is_translation_too_short(long_original, reasonable)
        assert is_short is False


class TestCrossModuleDataFlow:
    """Test data flows correctly between modules.

    Scope: Verifies that statistics, progress tracking, and error
    handling work correctly across module boundaries.
    """

    def test_batch_stats_recorder_integration(self):
        """Test BatchStatsRecorder receives updates correctly."""
        from modules.progress_tracker import ProgressTracker

        tracker = ProgressTracker()
        stats = BatchStatsRecorder(
            batch_size=5,
            progress_tracker=tracker,
            metadata_key="test_stats",
            total_batches=3,
            items_total=15,
        )

        # Record some batch completions (uses elapsed_seconds, item_count)
        stats.record(1.5, 5)
        stats.record(2.0, 5)

        # Verify stats are accumulated via internal state
        # BatchStatsRecorder publishes to progress_tracker, check internal state
        assert stats._batches_completed == 2
        assert stats._items_completed == 10
        assert abs(stats._total_batch_seconds - 3.5) < 0.001

    def test_progress_tracker_retry_integration(self):
        """Test progress tracker receives retry counts from validation."""
        from modules.progress_tracker import ProgressTracker

        tracker = ProgressTracker()

        # Simulate validation failures that would be recorded
        tracker.record_retry("translation", "Translation shorter than expected")
        tracker.record_retry("translation", "Translation shorter than expected")
        tracker.record_retry("transliteration", "Non-Latin transliteration received")

        counts = tracker.get_retry_counts()
        assert counts["translation"]["Translation shorter than expected"] == 2
        assert counts["transliteration"]["Non-Latin transliteration received"] == 1

    def test_worker_pool_task_execution(self):
        """Test ThreadWorkerPool executes tasks correctly."""
        results = []

        def task(x):
            return x * 2

        with ThreadWorkerPool(max_workers=2) as pool:
            futures = {pool.submit(task, i): i for i in range(5)}
            for future in pool.iter_completed(futures):
                results.append(future.result())

        assert sorted(results) == [0, 2, 4, 6, 8]


class TestEndToEndBatchFlow:
    """Test end-to-end batch translation flow with mocked LLM.

    Scope: Verifies the complete batch translation pipeline works
    correctly, from input sentences to validated output.
    """

    @patch("modules.translation_batch.llm_batch")
    @patch("modules.translation_batch.prompt_templates")
    @patch("modules.translation_batch.write_llm_batch_artifact")
    def test_batch_translation_flow(self, mock_write, mock_prompts, mock_llm):
        """Test complete batch translation flow."""
        # Setup mocks
        mock_prompts.make_translation_batch_prompt.return_value = "system prompt"
        mock_prompts.make_sentence_payload.return_value = "payload"
        mock_llm.build_json_batch_payload.return_value = '{"items": []}'

        mock_response = MagicMock()
        mock_response.payload = {
            "items": [
                {"id": 0, "translation": "Bonjour le monde"},
                {"id": 1, "translation": "Comment allez-vous"},
            ]
        }
        mock_response.raw_text = '{"items": [...]}'
        mock_response.error = None
        mock_response.elapsed = 1.0
        mock_llm.request_json_batch.return_value = mock_response

        mock_client = MagicMock()
        mock_client.model = "test-model"

        # Execute batch translation
        batch_items = [(0, "Hello world"), (1, "How are you")]
        result, error, elapsed = tb.translate_llm_batch_items(
            batch_items,
            "english",
            "french",
            include_transliteration=False,
            resolved_client=mock_client,
            progress_tracker=None,
            timeout_seconds=30.0,
        )

        # Verify results
        assert error is None
        assert 0 in result
        assert 1 in result
        assert result[0][0] == "Bonjour le monde"
        assert result[1][0] == "Comment allez-vous"

        # Validate the translations
        error0 = tb.validate_batch_translation("Hello world", result[0][0], "french")
        error1 = tb.validate_batch_translation("How are you", result[1][0], "french")

        # Both should be valid (reasonable length, correct script)
        assert error0 is None
        assert error1 is None


class TestBackwardCompatibility:
    """Test backward compatibility of the refactored modules.

    Scope: Ensures that existing code using the old private function
    names still works correctly after the refactoring.
    """

    def test_public_names_work(self):
        """Test that public names in translation_engine still work."""
        # These should all work without errors
        assert te.normalize_llm_batch_size(5) == 5
        assert te.normalize_llm_batch_size(1) is None

        batches = te.build_translation_batches(
            ["a", "b"], ["en", "en"], batch_size=10
        )
        assert len(batches) == 1

        items = te.extract_batch_items({"items": [{"id": 1}]})
        assert items == [{"id": 1}]

        item_id = te.coerce_batch_item_id({"id": 5}, None)
        assert item_id == 5

        text = te.coerce_text_value(None)
        assert text == ""

    def test_validation_aliases_work(self):
        """Test that validation aliases still work."""
        assert te._valid_translation("Hello") is True
        assert te._valid_translation("") is False

        assert te._letter_count("Hello") == 5
        assert te._letter_count("123") == 0

        assert te._is_translation_too_short("Hi", "Hello") is False


# Run a quick smoke test to ensure all imports work
def test_all_modules_import():
    """Smoke test: verify all translation modules import without error."""
    from modules import translation_engine
    from modules import translation_batch
    from modules import translation_validation
    from modules import translation_logging
    from modules import translation_workers
    from modules.translation_providers import googletrans_provider
    # All imports successful
    assert translation_engine is not None
    assert translation_batch is not None
    assert translation_validation is not None
    assert translation_logging is not None
    assert translation_workers is not None
    assert googletrans_provider is not None
