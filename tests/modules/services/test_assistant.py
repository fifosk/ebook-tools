"""Tests for the assistant services module."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

import pytest

from modules.llm_client import LLMResponse
from modules.services.assistant import (
    AssistantLookupResult,
    build_lookup_system_prompt,
    lookup_dictionary_entry,
)


# --- Valid JSON response fixtures ---


def _make_valid_word_json() -> str:
    """Return a valid JSON response for a word lookup."""
    return json.dumps(
        {
            "type": "word",
            "definition": "A common greeting or expression of good wishes.",
            "part_of_speech": "noun",
            "pronunciation": "/həˈloʊ/",
            "etymology": "From Old English 'hāl' meaning healthy, whole.",
            "example": "She said hello to her neighbor.",
            "idioms": None,
            "related_languages": [
                {"language": "German", "word": "Hallo", "transliteration": None},
                {"language": "French", "word": "Allô", "transliteration": None},
                {"language": "Spanish", "word": "Hola", "transliteration": None},
            ],
        }
    )


def _make_valid_sentence_json() -> str:
    """Return a valid JSON response for a sentence lookup."""
    return json.dumps(
        {
            "type": "sentence",
            "definition": "A polite inquiry about someone's well-being.",
            "part_of_speech": None,
            "pronunciation": None,
            "etymology": None,
            "example": None,
            "idioms": ["How are you doing?", "How's it going?"],
            "related_languages": None,
        }
    )


def _make_valid_arabic_word_json() -> str:
    """Return a valid JSON response for a non-Latin word with transliteration."""
    return json.dumps(
        {
            "type": "word",
            "definition": "Book, a written or printed work.",
            "part_of_speech": "noun",
            "pronunciation": "/kitaːb/",
            "etymology": "From the Arabic root k-t-b (to write).",
            "example": "أقرأ كتابًا جميلًا (aqraʾ kitāban jamīlan) - I am reading a beautiful book.",
            "idioms": None,
            "related_languages": [
                {"language": "Persian", "word": "کتاب", "transliteration": "ketāb"},
                {"language": "Turkish", "word": "kitap", "transliteration": None},
                {"language": "Hebrew", "word": "ספר", "transliteration": "sefer"},
            ],
        }
    )


def _make_minimal_valid_json() -> str:
    """Return minimal valid JSON with just required field."""
    return json.dumps(
        {
            "type": "word",
            "definition": "A test definition.",
        }
    )


# --- Invalid JSON response fixtures ---


def _make_plain_text_response() -> str:
    """Return a plain text response (non-JSON)."""
    return "Hello is a greeting used when meeting someone."


def _make_partial_json() -> str:
    """Return truncated/incomplete JSON."""
    return '{"type": "word", "definition": "incomplete...'


def _make_json_missing_definition() -> str:
    """Return JSON missing the required 'definition' field."""
    return json.dumps(
        {
            "type": "word",
            "part_of_speech": "noun",
        }
    )


def _make_json_with_prefix_text() -> str:
    """Return JSON with text before the object."""
    return 'Here is the lookup result:\n' + _make_valid_word_json()


def _make_json_with_suffix_text() -> str:
    """Return JSON with text after the object."""
    return _make_valid_word_json() + '\n\nI hope this helps!'


# --- Fake LLM client for testing ---


class _FakeLLMClient:
    """Fake LLM client that returns configurable responses."""

    def __init__(self, response_text: str, model: str = "test-model") -> None:
        self.model = model
        self.response_text = response_text
        self.last_payload: dict[str, Any] | None = None

    def send_chat_request(
        self, payload, *, max_attempts=3, timeout=None, validator=None, backoff_seconds=1.0
    ):
        self.last_payload = payload
        return LLMResponse(
            text=self.response_text,
            status_code=200,
            token_usage={"prompt_eval_count": 10, "eval_count": 50},
            raw={"ok": True},
            error=None,
            source="local",
        )

    def close(self) -> None:
        pass


def _fake_client_factory(response_text: str, default_model: str = "test-model"):
    """Create a factory function that returns a context manager yielding a fake LLM client."""

    @contextmanager
    def factory(*, model=None, **_kwargs):
        client = _FakeLLMClient(
            response_text=response_text,
            model=model or default_model,
        )
        try:
            yield client
        finally:
            client.close()

    return factory


# --- Tests for build_lookup_system_prompt ---


class TestBuildLookupSystemPrompt:
    """Tests for the system prompt builder."""

    def test_prompt_includes_json_instruction(self) -> None:
        """Prompt should instruct LLM to respond with valid JSON."""
        prompt = build_lookup_system_prompt(input_language="English", lookup_language="Spanish")
        assert "JSON" in prompt
        assert "valid JSON object" in prompt.lower() or "valid json" in prompt.lower()

    def test_prompt_includes_type_field(self) -> None:
        """Prompt should define the 'type' field."""
        prompt = build_lookup_system_prompt(input_language="English", lookup_language="Spanish")
        assert '"type"' in prompt
        assert "word" in prompt
        assert "phrase" in prompt
        assert "sentence" in prompt

    def test_prompt_includes_definition_field(self) -> None:
        """Prompt should define the 'definition' field as required."""
        prompt = build_lookup_system_prompt(input_language="English", lookup_language="Spanish")
        assert '"definition"' in prompt
        assert "required" in prompt.lower()

    def test_prompt_includes_related_languages_structure(self) -> None:
        """Prompt should define the 'related_languages' array structure."""
        prompt = build_lookup_system_prompt(input_language="English", lookup_language="Spanish")
        assert '"related_languages"' in prompt
        assert '"language"' in prompt
        assert '"transliteration"' in prompt

    def test_prompt_includes_transliteration_instruction(self) -> None:
        """Prompt should instruct to include transliteration for non-Latin scripts."""
        prompt = build_lookup_system_prompt(input_language="Arabic", lookup_language="English")
        assert "transliteration" in prompt.lower()
        assert "non-Latin" in prompt or "Arabic" in prompt

    def test_prompt_uses_input_language(self) -> None:
        """Prompt should include the specified input language."""
        prompt = build_lookup_system_prompt(input_language="Japanese", lookup_language="English")
        assert "Japanese" in prompt

    def test_prompt_uses_lookup_language(self) -> None:
        """Prompt should include the specified lookup language."""
        prompt = build_lookup_system_prompt(input_language="English", lookup_language="French")
        assert "French" in prompt

    def test_prompt_handles_empty_input_language(self) -> None:
        """Prompt should handle empty input language gracefully."""
        prompt = build_lookup_system_prompt(input_language="", lookup_language="English")
        assert "input language" in prompt.lower()

    def test_prompt_handles_empty_lookup_language(self) -> None:
        """Prompt should default to English for empty lookup language."""
        prompt = build_lookup_system_prompt(input_language="Spanish", lookup_language="")
        assert "English" in prompt


# --- Tests for JSON response parsing ---


class TestJsonResponseParsing:
    """Tests to verify LLM responses can be parsed as JSON."""

    def test_valid_word_json_is_parseable(self) -> None:
        """Valid word JSON response should be parseable."""
        response_text = _make_valid_word_json()
        parsed = json.loads(response_text)
        assert parsed["type"] == "word"
        assert "definition" in parsed
        assert parsed["definition"]
        assert parsed["related_languages"] is not None

    def test_valid_sentence_json_is_parseable(self) -> None:
        """Valid sentence JSON response should be parseable."""
        response_text = _make_valid_sentence_json()
        parsed = json.loads(response_text)
        assert parsed["type"] == "sentence"
        assert "definition" in parsed
        assert parsed["idioms"] is not None

    def test_valid_arabic_json_includes_transliteration(self) -> None:
        """Arabic word JSON should include transliteration in related languages."""
        response_text = _make_valid_arabic_word_json()
        parsed = json.loads(response_text)
        assert parsed["type"] == "word"
        related = parsed["related_languages"]
        assert any(lang["transliteration"] is not None for lang in related)

    def test_minimal_json_has_required_fields(self) -> None:
        """Minimal JSON should have at least type and definition."""
        response_text = _make_minimal_valid_json()
        parsed = json.loads(response_text)
        assert "type" in parsed
        assert "definition" in parsed

    def test_json_with_prefix_can_be_extracted(self) -> None:
        """JSON with prefix text should be extractable."""
        response_text = _make_json_with_prefix_text()
        # Find the JSON object
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        json_str = response_text[start:end]
        parsed = json.loads(json_str)
        assert "definition" in parsed

    def test_json_with_suffix_can_be_extracted(self) -> None:
        """JSON with suffix text should be extractable."""
        response_text = _make_json_with_suffix_text()
        # Find the JSON object
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        json_str = response_text[start:end]
        parsed = json.loads(json_str)
        assert "definition" in parsed


# --- Tests for lookup_dictionary_entry ---


class TestLookupDictionaryEntry:
    """Tests for the lookup_dictionary_entry function."""

    def test_returns_result_with_json_response(self, monkeypatch) -> None:
        """Function should return result when LLM returns valid JSON."""
        response_text = _make_valid_word_json()
        monkeypatch.setattr(
            "modules.services.assistant.create_client",
            _fake_client_factory(response_text),
        )
        result = lookup_dictionary_entry(
            query="hello",
            input_language="English",
            lookup_language="Spanish",
        )
        assert isinstance(result, AssistantLookupResult)
        assert result.answer == response_text

    def test_returns_result_with_plain_text_response(self, monkeypatch) -> None:
        """Function should still return result for plain text (backward compat)."""
        response_text = _make_plain_text_response()
        monkeypatch.setattr(
            "modules.services.assistant.create_client",
            _fake_client_factory(response_text),
        )
        result = lookup_dictionary_entry(
            query="hello",
            input_language="English",
            lookup_language="Spanish",
        )
        assert isinstance(result, AssistantLookupResult)
        assert result.answer == response_text

    def test_raises_on_empty_query(self) -> None:
        """Function should raise on empty query."""
        with pytest.raises(ValueError, match="empty"):
            lookup_dictionary_entry(
                query="",
                input_language="English",
                lookup_language="Spanish",
            )

    def test_includes_model_in_result(self, monkeypatch) -> None:
        """Result should include the model used."""
        response_text = _make_valid_word_json()
        monkeypatch.setattr(
            "modules.services.assistant.create_client",
            _fake_client_factory(response_text, default_model="custom-model"),
        )
        result = lookup_dictionary_entry(
            query="test",
            input_language="English",
            lookup_language="Spanish",
            llm_model="custom-model",
        )
        assert result.model == "custom-model"


# --- Tests for JSON schema compliance ---


class TestJsonSchemaCompliance:
    """Tests to verify JSON responses comply with expected schema."""

    @pytest.mark.parametrize(
        "json_factory,expected_type",
        [
            (_make_valid_word_json, "word"),
            (_make_valid_sentence_json, "sentence"),
            (_make_valid_arabic_word_json, "word"),
        ],
    )
    def test_type_field_values(self, json_factory, expected_type) -> None:
        """Type field should be one of: word, phrase, sentence."""
        parsed = json.loads(json_factory())
        assert parsed["type"] == expected_type
        assert parsed["type"] in ("word", "phrase", "sentence")

    @pytest.mark.parametrize(
        "json_factory",
        [
            _make_valid_word_json,
            _make_valid_sentence_json,
            _make_valid_arabic_word_json,
            _make_minimal_valid_json,
        ],
    )
    def test_definition_is_non_empty_string(self, json_factory) -> None:
        """Definition field should be a non-empty string."""
        parsed = json.loads(json_factory())
        assert isinstance(parsed["definition"], str)
        assert len(parsed["definition"]) > 0

    def test_related_languages_structure(self) -> None:
        """Related languages should be array of objects with required fields."""
        parsed = json.loads(_make_valid_word_json())
        related = parsed.get("related_languages")
        if related is not None:
            assert isinstance(related, list)
            for lang in related:
                assert isinstance(lang, dict)
                assert "language" in lang
                assert "word" in lang
                # transliteration can be null or string
                assert "transliteration" in lang

    def test_idioms_structure(self) -> None:
        """Idioms should be array of strings when present."""
        parsed = json.loads(_make_valid_sentence_json())
        idioms = parsed.get("idioms")
        if idioms is not None:
            assert isinstance(idioms, list)
            for idiom in idioms:
                assert isinstance(idiom, str)

    def test_optional_fields_can_be_null(self) -> None:
        """Optional fields should accept null values."""
        parsed = json.loads(_make_valid_sentence_json())
        # These should be null for a sentence type
        assert parsed.get("part_of_speech") is None
        assert parsed.get("pronunciation") is None
        assert parsed.get("etymology") is None
        assert parsed.get("example") is None
        assert parsed.get("related_languages") is None
