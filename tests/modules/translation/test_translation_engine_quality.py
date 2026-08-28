import pytest

from modules import translation_engine
from modules import prompt_templates
from modules.llm_client import LLMResponse
from modules.progress_tracker import ProgressTracker

pytestmark = pytest.mark.translation


def test_sentence_retry_budget_counts_actual_requests(monkeypatch):
    from modules.llm_client import ClientSettings, LLMClient

    client = LLMClient(ClientSettings(model="test-model"))
    calls = []
    sleeps = []

    def execute(payload, **kwargs):
        calls.append(kwargs)
        return LLMResponse(text="", status_code=0, token_usage={}, error="Read timed out")

    monkeypatch.setattr(client, "_execute_request", execute)
    monkeypatch.setattr(translation_engine.time, "sleep", sleeps.append)
    _, error, _ = translation_engine._translate_with_llm(
        "Hello", "English", "Arabic", include_transliteration=True,
        resolved_client=client, progress_tracker=None, timeout_seconds=60,
    )
    assert error == "Read timed out"
    assert len(calls) == translation_engine._TRANSLATION_RESPONSE_ATTEMPTS
    assert len(sleeps) == translation_engine._TRANSLATION_RESPONSE_ATTEMPTS - 1


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


def test_single_translation_retries_missing_dialogue(monkeypatch):
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", 2)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    client = StubLLMClient(["Miten menee?", "Miten menee? Hyvin. Oli hyvä viikko."])
    result, error, _ = translation_engine._translate_with_llm(
        "How are things? Good. Had a good week.", "English", "Finnish",
        include_transliteration=False, resolved_client=client,
        progress_tracker=None, timeout_seconds=60,
    )
    assert result == "Miten menee? Hyvin. Oli hyvä viikko."
    assert error is None


@pytest.mark.parametrize("last_response", ["Miten menee?", ""])
def test_exhausted_completeness_retries_never_return_rejected_text(monkeypatch, last_response):
    from modules.retry_annotations import is_failure_annotation

    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", 2)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    result, error, _ = translation_engine._translate_with_llm(
        "How are things? Good. Had a good week.", "English", "Finnish",
        include_transliteration=False,
        resolved_client=StubLLMClient(["Miten menee?", last_response]),
        progress_tracker=None, timeout_seconds=60,
    )
    assert is_failure_annotation(result)
    assert error


@pytest.mark.parametrize("streaming", [False, True], ids=["subtitles-and-video", "book-pipeline"])
def test_incomplete_batch_retries_neighbors_in_both_translation_flows(monkeypatch, streaming):
    from queue import Queue
    from modules import llm_batch, translation_batch

    bad_payload = {"items": [
        {"id": 0, "translation": "Miten menee?"},
        {"id": 1, "translation": "Hyvin. Oli hyvä viikko. Odota tässä."},
    ]}
    monkeypatch.setattr(llm_batch, "request_json_batch", lambda **kwargs:
                        llm_batch.JsonBatchResponse(bad_payload, "", None, 0.1))
    monkeypatch.setattr(translation_batch, "write_llm_batch_artifact", lambda **kwargs: None)
    monkeypatch.setattr(translation_engine, "resolve_llm_batch_log_dir", lambda *args: None)
    client = StubLLMClient(["Miten menee? Hyvin. Oli hyvä viikko.", "Odota tässä."])
    source = ["How are things? Good. Had a good week.", "Wait here."]
    tracker = ProgressTracker()
    kwargs = dict(client=client, llm_batch_size=2, max_workers=1, progress_tracker=tracker)
    if streaming:
        queue = Queue()
        thread = translation_engine.start_translation_pipeline(
            source, "English", ["Finnish", "Finnish"], start_sentence=1,
            output_queue=queue, consumer_count=1, **kwargs,
        )
        thread.join(timeout=5)
        assert not thread.is_alive()
        tasks = [queue.get_nowait(), queue.get_nowait()]
        result = [task.translation for task in sorted(tasks, key=lambda task: task.index)]
        assert queue.get_nowait() is None
    else:
        result = translation_engine.translate_batch(source, "English", "Finnish", **kwargs)
    assert result == ["Miten menee? Hyvin. Oli hyvä viikko.", "Odota tässä."]
    assert not client.responses  # The neighboring item's borrowed content was retried too.
    assert tracker.get_retry_counts()['translation'][
        'Incomplete translation batch; retrying items independently'
    ] == 2


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
