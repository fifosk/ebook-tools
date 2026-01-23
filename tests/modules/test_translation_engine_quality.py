import pytest

from modules import translation_engine
from modules import prompt_templates
from modules.llm_client import LLMResponse
from modules.progress_tracker import ProgressTracker


class StubLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.model = "stub-model"
        self.debug_enabled = False
        self.llm_source = "local"

    def send_chat_request(
        self,
        payload,
        *,
        max_attempts: int = 3,
        timeout=None,
        validator=None,
        backoff_seconds: float = 1.0,
    ) -> LLMResponse:
        try:
            text = self.responses.pop(0)
        except IndexError:
            text = ""
        return LLMResponse(text=text, status_code=200, token_usage={})


@pytest.mark.parametrize("attempts", [2])
def test_retry_when_transliteration_returned(monkeypatch, attempts):
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", attempts)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    client = StubLLMClient(["konnichiwa sekai", "こんにちは 世界"])

    result = translation_engine.translate_sentence_simple(
        "こんにちは、世界",
        "japanese",
        "japanese",
        include_transliteration=True,
        client=client,
    )

    assert result == "こんにちは 世界"


@pytest.mark.parametrize("attempts", [2])
def test_retry_when_translation_too_short(monkeypatch, attempts):
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", attempts)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    original = (
        "This is a deliberately long source sentence with several clauses to ensure "
        "the short-response heuristic triggers a retry when the model responds too tersely."
    )
    client = StubLLMClient(
        [
            "Okay.",
            "This is a fuller translation that roughly mirrors the length and meaning of the original sentence.",
        ]
    )

    result = translation_engine.translate_sentence_simple(
        original,
        "english",
        "english",
        include_transliteration=False,
        client=client,
    )

    assert "fuller translation" in result


@pytest.mark.parametrize("attempts", [2])
def test_retry_when_missing_diacritics(monkeypatch, attempts):
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", attempts)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    client = StubLLMClient(
        [
            "مرحبا بالعالم",
            "مَرْحَبًا بِالْعَالَمِ",
        ]
    )

    result = translation_engine.translate_sentence_simple(
        "مرحبا بالعالم",
        "arabic",
        "arabic",
        include_transliteration=False,
        client=client,
    )

    assert "َ" in result or "ِ" in result or "ً" in result


@pytest.mark.parametrize("attempts", [2])
def test_fallback_without_diacritics(monkeypatch, attempts):
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", attempts)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    client = StubLLMClient(
        [
            "مرحبا بالعالم",
            "اهلا بكم جميعا",
        ]
    )

    result = translation_engine.translate_sentence_simple(
        "مرحبا بالعالم",
        "arabic",
        "arabic",
        include_transliteration=False,
        client=client,
    )

    assert "مرحبا" in result or "اهلا" in result


def test_records_retry_counts(monkeypatch):
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", 2)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    tracker = ProgressTracker()
    client = StubLLMClient(
        [
            "OK.",
            "Proper translated output with vowels",
        ]
    )

    translation_engine.translate_sentence_simple(
        "A very long sentence that should trigger the short translation retry.",
        "english",
        "arabic",
        progress_tracker=tracker,
        client=client,
    )

    counts = tracker.get_retry_counts()
    assert counts.get("translation", {}).get("Translation shorter than expected") == 1


def test_prompts_include_diacritic_guidance():
    arabic_prompt = prompt_templates.make_translation_prompt("english", "arabic")
    hebrew_prompt = prompt_templates.make_translation_prompt("english", "hebrew")
    translit_prompt = prompt_templates.make_transliteration_prompt("arabic")

    assert "diacritics" in arabic_prompt.lower()
    assert "niqqud" in hebrew_prompt.lower()
    assert "vowel" in translit_prompt.lower()
