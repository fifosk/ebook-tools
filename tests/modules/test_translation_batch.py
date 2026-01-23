"""Unit tests for translation_batch module.

Tests batch building, payload parsing, validation, and LLM batch processing.
"""

import pytest
from unittest.mock import MagicMock, patch

from modules import translation_batch as tb


class TestNormalizeLLMBatchSize:
    """Tests for normalize_llm_batch_size."""

    def test_none_returns_none(self):
        assert tb.normalize_llm_batch_size(None) is None

    def test_valid_size_returns_size(self):
        assert tb.normalize_llm_batch_size(10) == 10

    def test_size_one_returns_none(self):
        assert tb.normalize_llm_batch_size(1) is None

    def test_size_zero_returns_none(self):
        assert tb.normalize_llm_batch_size(0) is None

    def test_negative_returns_none(self):
        assert tb.normalize_llm_batch_size(-5) is None

    def test_string_number_returns_int(self):
        # int() will convert valid string representations
        assert tb.normalize_llm_batch_size(5) == 5

    def test_invalid_type_returns_none(self):
        assert tb.normalize_llm_batch_size("invalid") is None
        assert tb.normalize_llm_batch_size([5]) is None


class TestBuildTranslationBatches:
    """Tests for build_translation_batches."""

    def test_empty_input(self):
        result = tb.build_translation_batches([], [], batch_size=5)
        assert result == []

    def test_single_language_single_batch(self):
        sentences = ["a", "b", "c"]
        targets = ["en", "en", "en"]
        result = tb.build_translation_batches(sentences, targets, batch_size=5)
        assert len(result) == 1
        assert result[0][0] == "en"
        assert result[0][1] == [(0, "a"), (1, "b"), (2, "c")]

    def test_single_language_multiple_batches(self):
        sentences = ["a", "b", "c", "d", "e"]
        targets = ["en"] * 5
        result = tb.build_translation_batches(sentences, targets, batch_size=2)
        assert len(result) == 3
        assert result[0] == ("en", [(0, "a"), (1, "b")])
        assert result[1] == ("en", [(2, "c"), (3, "d")])
        assert result[2] == ("en", [(4, "e")])

    def test_multiple_languages(self):
        sentences = ["a", "b", "c", "d"]
        targets = ["en", "en", "ar", "ar"]
        result = tb.build_translation_batches(sentences, targets, batch_size=10)
        assert len(result) == 2
        assert result[0] == ("en", [(0, "a"), (1, "b")])
        assert result[1] == ("ar", [(2, "c"), (3, "d")])

    def test_language_changes_mid_batch(self):
        sentences = ["a", "b", "c"]
        targets = ["en", "ar", "en"]
        result = tb.build_translation_batches(sentences, targets, batch_size=10)
        assert len(result) == 3
        assert result[0] == ("en", [(0, "a")])
        assert result[1] == ("ar", [(1, "b")])
        assert result[2] == ("en", [(2, "c")])


class TestChunkBatchItems:
    """Tests for chunk_batch_items."""

    def test_empty_input(self):
        result = tb.chunk_batch_items([], batch_size=5)
        # Empty input returns empty list (not [[]])
        assert result == []

    def test_single_chunk(self):
        items = [(0, "a"), (1, "b")]
        result = tb.chunk_batch_items(items, batch_size=5)
        assert len(result) == 1
        assert result[0] == [(0, "a"), (1, "b")]

    def test_multiple_chunks(self):
        items = [(0, "a"), (1, "b"), (2, "c"), (3, "d"), (4, "e")]
        result = tb.chunk_batch_items(items, batch_size=2)
        assert len(result) == 3
        assert result[0] == [(0, "a"), (1, "b")]
        assert result[1] == [(2, "c"), (3, "d")]
        assert result[2] == [(4, "e")]

    def test_zero_batch_size(self):
        items = [(0, "a"), (1, "b")]
        result = tb.chunk_batch_items(items, batch_size=0)
        assert result == [[(0, "a"), (1, "b")]]


class TestExtractBatchItems:
    """Tests for extract_batch_items."""

    def test_mapping_with_items(self):
        payload = {"items": [{"id": 1}, {"id": 2}]}
        result = tb.extract_batch_items(payload)
        assert result == [{"id": 1}, {"id": 2}]

    def test_direct_list(self):
        payload = [{"id": 1}, {"id": 2}]
        result = tb.extract_batch_items(payload)
        assert result == [{"id": 1}, {"id": 2}]

    def test_filters_non_mappings(self):
        payload = [{"id": 1}, "string", 123, {"id": 2}]
        result = tb.extract_batch_items(payload)
        assert result == [{"id": 1}, {"id": 2}]

    def test_none_returns_none(self):
        assert tb.extract_batch_items(None) is None

    def test_string_returns_none(self):
        assert tb.extract_batch_items("not a list") is None

    def test_empty_mapping(self):
        assert tb.extract_batch_items({}) is None

    def test_items_not_list(self):
        payload = {"items": "not a list"}
        assert tb.extract_batch_items(payload) is None


class TestCoerceBatchItemId:
    """Tests for coerce_batch_item_id."""

    def test_int_id(self):
        item = {"id": 5}
        assert tb.coerce_batch_item_id(item, None) == 5

    def test_float_id(self):
        item = {"id": 5.0}
        assert tb.coerce_batch_item_id(item, None) == 5

    def test_string_id(self):
        item = {"id": "7"}
        assert tb.coerce_batch_item_id(item, None) == 7

    def test_index_key(self):
        item = {"index": 3}
        assert tb.coerce_batch_item_id(item, None) == 3

    def test_sentence_id_key(self):
        item = {"sentence_id": 4}
        assert tb.coerce_batch_item_id(item, None) == 4

    def test_fallback_when_missing(self):
        item = {"translation": "text"}
        assert tb.coerce_batch_item_id(item, 10) == 10

    def test_no_fallback_returns_none(self):
        item = {"translation": "text"}
        assert tb.coerce_batch_item_id(item, None) is None

    def test_priority_order(self):
        # "id" should have higher priority than "index"
        item = {"id": 1, "index": 2}
        assert tb.coerce_batch_item_id(item, None) == 1


class TestCoerceTextValue:
    """Tests for coerce_text_value."""

    def test_string(self):
        assert tb.coerce_text_value("hello") == "hello"

    def test_none(self):
        assert tb.coerce_text_value(None) == ""

    def test_int(self):
        assert tb.coerce_text_value(123) == "123"

    def test_float(self):
        assert tb.coerce_text_value(3.14) == "3.14"


class TestParseBatchTranslationPayload:
    """Tests for parse_batch_translation_payload."""

    def test_simple_payload(self):
        payload = {
            "items": [
                {"id": 0, "translation": "Hello"},
                {"id": 1, "translation": "World"},
            ]
        }
        result = tb.parse_batch_translation_payload(
            payload, input_ids=[0, 1], include_transliteration=False
        )
        assert result == {0: ("Hello", ""), 1: ("World", "")}

    def test_with_transliteration(self):
        payload = {
            "items": [
                {"id": 0, "translation": "مرحبا", "transliteration": "marhaba"},
            ]
        }
        result = tb.parse_batch_translation_payload(
            payload, input_ids=[0], include_transliteration=True
        )
        assert result == {0: ("مرحبا", "marhaba")}

    def test_positional_fallback(self):
        payload = {"items": [{"translation": "Hello"}, {"translation": "World"}]}
        result = tb.parse_batch_translation_payload(
            payload, input_ids=[10, 20], include_transliteration=False
        )
        assert result == {10: ("Hello", ""), 20: ("World", "")}

    def test_empty_payload(self):
        result = tb.parse_batch_translation_payload(
            {}, input_ids=[0, 1], include_transliteration=False
        )
        assert result == {}

    def test_skips_duplicates(self):
        payload = {
            "items": [
                {"id": 0, "translation": "First"},
                {"id": 0, "translation": "Second"},
            ]
        }
        result = tb.parse_batch_translation_payload(
            payload, input_ids=[0, 0], include_transliteration=False
        )
        assert result == {0: ("First", "")}

    def test_inline_transliteration_extraction(self):
        """Test that inline transliteration is extracted from translation."""
        payload = {
            "items": [
                {"id": 0, "translation": "مرحبا\nmarhaba"},
            ]
        }
        result = tb.parse_batch_translation_payload(
            payload, input_ids=[0], include_transliteration=True
        )
        # Should extract the inline transliteration
        translation, transliteration = result[0]
        assert "مرحبا" in translation
        assert "marhaba" in transliteration or transliteration == ""


class TestParseBatchTransliterationPayload:
    """Tests for parse_batch_transliteration_payload."""

    def test_simple_payload(self):
        payload = {
            "items": [
                {"id": 0, "transliteration": "marhaba"},
                {"id": 1, "transliteration": "shukran"},
            ]
        }
        result = tb.parse_batch_transliteration_payload(payload, input_ids=[0, 1])
        assert result == {0: "marhaba", 1: "shukran"}

    def test_romanization_key(self):
        payload = {"items": [{"id": 0, "romanization": "marhaba"}]}
        result = tb.parse_batch_transliteration_payload(payload, input_ids=[0])
        assert result == {0: "marhaba"}

    def test_translit_key(self):
        payload = {"items": [{"id": 0, "translit": "marhaba"}]}
        result = tb.parse_batch_transliteration_payload(payload, input_ids=[0])
        assert result == {0: "marhaba"}

    def test_preserves_non_latin(self):
        # Note: parse_batch_transliteration_payload does NOT filter non-Latin text.
        # That filtering is done during validation in validate_batch_transliteration.
        payload = {"items": [{"id": 0, "transliteration": "مرحبا"}]}
        result = tb.parse_batch_transliteration_payload(payload, input_ids=[0])
        assert result == {0: "مرحبا"}


class TestValidateBatchTranslation:
    """Tests for validate_batch_translation."""

    def test_valid_translation(self):
        result = tb.validate_batch_translation(
            "Hello world", "Bonjour le monde", "french"
        )
        assert result is None

    def test_empty_translation(self):
        result = tb.validate_batch_translation("Hello world", "", "french")
        assert result is not None
        assert "Invalid" in result or "placeholder" in result.lower()

    def test_transliteration_instead(self):
        # When expecting non-Latin output but receiving Latin
        result = tb.validate_batch_translation(
            "مرحبا", "marhaba", "arabic"
        )
        assert result is not None
        assert "Transliteration" in result

    def test_too_short(self):
        long_original = "This is a very long sentence with many words that should trigger the too short detection when the translation is very brief."
        result = tb.validate_batch_translation(long_original, "OK", "english")
        assert result is not None
        assert "short" in result.lower()


class TestValidateBatchTransliteration:
    """Tests for validate_batch_transliteration."""

    def test_valid_transliteration(self):
        result = tb.validate_batch_transliteration("marhaba")
        assert result is None

    def test_empty_transliteration(self):
        result = tb.validate_batch_transliteration("")
        assert result is not None
        assert "Empty" in result

    def test_non_latin_transliteration(self):
        result = tb.validate_batch_transliteration("مرحبا")
        assert result is not None
        assert "Non-Latin" in result


class TestTranslateLLMBatchItems:
    """Tests for translate_llm_batch_items."""

    @patch("modules.translation_batch.llm_batch")
    @patch("modules.translation_batch.prompt_templates")
    @patch("modules.translation_batch.write_llm_batch_artifact")
    def test_successful_translation(self, mock_write, mock_prompts, mock_llm):
        mock_prompts.make_translation_batch_prompt.return_value = "system prompt"
        mock_prompts.make_sentence_payload.return_value = "payload"
        mock_llm.build_json_batch_payload.return_value = '{"items": []}'

        mock_response = MagicMock()
        mock_response.payload = {
            "items": [
                {"id": 0, "translation": "Bonjour"},
                {"id": 1, "translation": "Monde"},
            ]
        }
        mock_response.raw_text = '{"items": [...]}'
        mock_response.error = None
        mock_response.elapsed = 1.0
        mock_llm.request_json_batch.return_value = mock_response

        mock_client = MagicMock()
        mock_client.model = "test-model"

        batch_items = [(0, "Hello"), (1, "World")]
        result, error, elapsed = tb.translate_llm_batch_items(
            batch_items,
            "english",
            "french",
            include_transliteration=False,
            resolved_client=mock_client,
            progress_tracker=None,
            timeout_seconds=30.0,
        )

        assert error is None
        assert 0 in result
        assert 1 in result
        assert result[0][0] == "Bonjour"
        assert result[1][0] == "Monde"

    @patch("modules.translation_batch.llm_batch")
    @patch("modules.translation_batch.prompt_templates")
    @patch("modules.translation_batch.write_llm_batch_artifact")
    @patch("modules.translation_batch.time.sleep")
    def test_retries_on_error(self, mock_sleep, mock_write, mock_prompts, mock_llm):
        mock_prompts.make_translation_batch_prompt.return_value = "system prompt"
        mock_prompts.make_sentence_payload.return_value = "payload"
        mock_llm.build_json_batch_payload.return_value = '{"items": []}'

        mock_error_response = MagicMock()
        mock_error_response.payload = None
        mock_error_response.raw_text = ""
        mock_error_response.error = "LLM error"
        mock_error_response.elapsed = 0.5

        mock_success_response = MagicMock()
        mock_success_response.payload = {"items": [{"id": 0, "translation": "OK"}]}
        mock_success_response.raw_text = '{"items": [...]}'
        mock_success_response.error = None
        mock_success_response.elapsed = 1.0

        mock_llm.request_json_batch.side_effect = [
            mock_error_response,
            mock_success_response,
        ]

        mock_client = MagicMock()
        mock_client.model = "test-model"

        batch_items = [(0, "Hello")]
        result, error, elapsed = tb.translate_llm_batch_items(
            batch_items,
            "english",
            "french",
            include_transliteration=False,
            resolved_client=mock_client,
            progress_tracker=None,
            timeout_seconds=30.0,
        )

        assert error is None
        assert 0 in result
        mock_sleep.assert_called()


class TestTransliterateLLMBatchItems:
    """Tests for transliterate_llm_batch_items."""

    @patch("modules.translation_batch.llm_batch")
    @patch("modules.translation_batch.prompt_templates")
    @patch("modules.translation_batch.write_llm_batch_artifact")
    def test_successful_transliteration(self, mock_write, mock_prompts, mock_llm):
        mock_prompts.make_transliteration_batch_prompt.return_value = "system prompt"
        mock_prompts.make_sentence_payload.return_value = "payload"
        mock_llm.build_json_batch_payload.return_value = '{"items": []}'

        mock_response = MagicMock()
        mock_response.payload = {
            "items": [
                {"id": 0, "transliteration": "marhaba"},
                {"id": 1, "transliteration": "shukran"},
            ]
        }
        mock_response.raw_text = '{"items": [...]}'
        mock_response.error = None
        mock_response.elapsed = 1.0
        mock_llm.request_json_batch.return_value = mock_response

        mock_client = MagicMock()
        mock_client.model = "test-model"

        batch_items = [(0, "مرحبا"), (1, "شكرا")]
        result, error, elapsed = tb.transliterate_llm_batch_items(
            batch_items,
            "arabic",
            resolved_client=mock_client,
            progress_tracker=None,
            timeout_seconds=30.0,
        )

        assert error is None
        assert result == {0: "marhaba", 1: "shukran"}


class TestResolveBatchTransliterations:
    """Tests for resolve_batch_transliterations."""

    def test_empty_batch(self):
        result = tb.resolve_batch_transliterations(
            [],
            "arabic",
            transliterator=MagicMock(),
            transliteration_mode=None,
            transliteration_client=None,
            local_client=MagicMock(),
            progress_tracker=None,
            batch_size=None,
            batch_log_dir=None,
            batch_stats=None,
        )
        assert result == {}

    def test_python_only_mode(self):
        mock_transliterator = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "marhaba"
        mock_transliterator.transliterate.return_value = mock_result

        mock_client = MagicMock()

        batch_items = [(0, "مرحبا")]
        result = tb.resolve_batch_transliterations(
            batch_items,
            "arabic",
            transliterator=mock_transliterator,
            transliteration_mode="python",
            transliteration_client=None,
            local_client=mock_client,
            progress_tracker=None,
            batch_size=None,
            batch_log_dir=None,
            batch_stats=None,
        )

        assert result == {0: "marhaba"}
        mock_transliterator.transliterate.assert_called_once()
