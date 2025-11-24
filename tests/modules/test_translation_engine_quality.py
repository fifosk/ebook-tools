import pytest

from modules import translation_engine
from modules.llm_client import LLMResponse


class StubLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.model = "stub-model"
        self.debug_enabled = False

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
