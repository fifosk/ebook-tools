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


def test_provider_pressure_reduces_admission_without_exceeding_worker_ceiling(monkeypatch):
    import threading
    lock = threading.Lock()
    attempts = 0
    limits = []
    tracker = ProgressTracker(throttle_interval=0)
    tracker.register_observer(lambda event: limits.append(
        event.metadata.get("generated_files", {}).get("translation_flow", {}).get("concurrency")))

    def batch(items, *args, **kwargs):
        nonlocal attempts
        with lock:
            attempts += 1
            pressure = attempts <= 4
        return ({idx: ("Odota tässä.", "") for idx, _ in items}, "HTTP 429" if pressure else None, .01)

    monkeypatch.setattr(translation_engine, "translate_llm_batch_items", batch)
    monkeypatch.setattr(translation_engine, "translate_sentence_simple", lambda *args, **kwargs: "Odota tässä.")
    result = translation_engine.translate_batch(
        ["Wait here."] * 40, "English", "Finnish", client=StubLLMClient([]),
        max_workers=4, llm_batch_size=2, progress_tracker=tracker,
    )
    assert result == ["Odota tässä."] * 40
    limits = [value for value in limits if value is not None]
    assert min(limits) < 4 and max(limits) == 4
    flow = tracker.get_generated_files()["translation_flow"]
    assert flow["accepted"] == 40 and flow["repaired"] == 8
    assert flow["in_flight"] == flow["repairs_waiting"] == 0


@pytest.mark.parametrize("streaming", [False, True], ids=["subtitles-and-video", "book-pipeline"])
def test_batch_repairs_use_idle_workers_without_hiding_valid_items(monkeypatch, streaming):
    from queue import Queue
    from threading import Event, Lock, Thread

    release = Event()
    repairs_running = Event()
    valid_complete = Event()
    lock = Lock()
    active = peak = 0
    calls = []
    results = []
    errors = []
    source = [f"Wait here {i}." for i in range(4)]
    expected = [f"Odota tässä {i}." for i in range(4)]

    def repair(sentence, *args, **kwargs):
        nonlocal active, peak
        with lock:
            calls.append(sentence)
            active += 1
            peak = max(peak, active)
            if active == 2:
                repairs_running.set()
        try:
            assert release.wait(5)
            return expected[source.index(sentence)]
        finally:
            with lock:
                active -= 1

    tracker = ProgressTracker()
    original_completion = tracker.record_translation_completion

    def completed(index, number):
        original_completion(index, number)
        if index == 0:
            valid_complete.set()

    monkeypatch.setattr(tracker, "record_translation_completion", completed)
    monkeypatch.setattr(translation_engine, "translate_llm_batch_items", lambda *args, **kwargs:
                        ({0: (expected[0], "")}, None, 0.01))
    monkeypatch.setattr(translation_engine, "translate_sentence_simple", repair)
    monkeypatch.setattr(translation_engine, "resolve_llm_batch_log_dir", lambda *args: None)
    kwargs = dict(client=StubLLMClient([]), llm_batch_size=4, max_workers=2, progress_tracker=tracker)
    queue = Queue()
    if streaming:
        thread = translation_engine.start_translation_pipeline(
            source, "English", ["Finnish"] * len(source), start_sentence=1,
            output_queue=queue, consumer_count=1, **kwargs,
        )
    else:
        def run():
            try:
                results.extend(translation_engine.translate_batch(source, "English", "Finnish", **kwargs))
            except BaseException as exc:
                errors.append(exc)
        thread = Thread(target=run)
        thread.start()
    try:
        assert repairs_running.wait(2), "repairs remained serial despite idle workers"
        assert valid_complete.wait(1), "accepted translation was held behind unrelated repairs"
        if streaming:
            first = queue.get(timeout=1)
            assert first.index == 0
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()
    assert not errors
    assert peak == 2
    assert sorted(calls) == sorted(source[1:])
    if streaming:
        tasks = [first] + [queue.get_nowait() for _ in range(3)]
        results = [task.translation for task in sorted(tasks, key=lambda task: task.index)]
        assert queue.get_nowait() is None
    assert results == expected


@pytest.mark.parametrize("streaming", [False, True], ids=["subtitles-and-video", "book-pipeline"])
def test_batch_submission_is_bounded_and_cancel_does_not_schedule_repairs(monkeypatch, streaming):
    from queue import Queue
    from threading import Event, Lock, Thread
    from modules.translation_workers import ThreadWorkerPool

    release = Event()
    running = Event()
    stop = Event()
    lock = Lock()
    calls = []
    errors = []

    class RecordingPool(ThreadWorkerPool):
        def __init__(self):
            super().__init__(max_workers=2)
            self.submitted = 0

        def submit(self, *args, **kwargs):
            self.submitted += 1
            return super().submit(*args, **kwargs)

    def batch(items, *args, **kwargs):
        with lock:
            calls.append(items)
            if len(calls) == 2:
                running.set()
        assert release.wait(5)
        return {}, "Incomplete translation batch", 0.01

    monkeypatch.setattr(translation_engine, "translate_llm_batch_items", batch)
    repairs = []
    monkeypatch.setattr(translation_engine, "translate_sentence_simple", lambda *args, **kwargs: repairs.append(args))
    monkeypatch.setattr(translation_engine, "resolve_llm_batch_log_dir", lambda *args: None)
    source = [f"Wait here {i}." for i in range(100)]
    with RecordingPool() as pool:
        kwargs = dict(client=StubLLMClient([]), llm_batch_size=2, max_workers=4,
                      worker_pool=pool, stop_event=stop)
        if streaming:
            thread = translation_engine.start_translation_pipeline(
                source, "English", ["Finnish"] * len(source), start_sentence=1,
                output_queue=Queue(), consumer_count=1, **kwargs,
            )
        else:
            def run():
                try:
                    translation_engine.translate_batch(source, "English", "Finnish", **kwargs)
                except BaseException as exc:
                    errors.append(exc)
            thread = Thread(target=run)
            thread.start()
        try:
            assert running.wait(2), errors
            assert pool.submitted == 2, "entire input was submitted ahead of available capacity"
        finally:
            stop.set()
            release.set()
            thread.join(5)
        assert not thread.is_alive()
        assert not errors
        assert pool.submitted == 2
    assert len(calls) == 2
    assert not repairs


@pytest.mark.parametrize("streaming", [False, True], ids=["subtitles-and-video", "book-pipeline"])
def test_batch_exception_repairs_keep_failed_item_visible(monkeypatch, streaming):
    from queue import Queue
    from modules.retry_annotations import is_failure_annotation

    def batch(*args, **kwargs):
        raise RuntimeError("provider connection failed")

    def repair(sentence, *args, **kwargs):
        if sentence == "Wait here.":
            raise RuntimeError("repair connection failed")
        return "Tule tänne."

    monkeypatch.setattr(translation_engine, "translate_llm_batch_items", batch)
    monkeypatch.setattr(translation_engine, "translate_sentence_simple", repair)
    monkeypatch.setattr(translation_engine, "resolve_llm_batch_log_dir", lambda *args: None)
    tracker = ProgressTracker()
    kwargs = dict(client=StubLLMClient([]), llm_batch_size=2, max_workers=2, progress_tracker=tracker)
    source = ["Wait here.", "Come here."]
    if streaming:
        queue = Queue()
        thread = translation_engine.start_translation_pipeline(
            source, "English", ["Finnish"] * 2, start_sentence=10,
            output_queue=queue, consumer_count=1, **kwargs,
        )
        thread.join(5)
        assert not thread.is_alive()
        tasks = sorted([queue.get_nowait(), queue.get_nowait()], key=lambda task: task.index)
        result = [task.translation for task in tasks]
        assert [task.sentence_number for task in tasks] == [10, 11]
        assert queue.get_nowait() is None
    else:
        result = translation_engine.translate_batch(source, "English", "Finnish", **kwargs)
    assert len(result) == 2 and is_failure_annotation(result[0])
    assert result[1] == "Tule tänne."
    assert tracker.get_retry_counts()["translation"]["Batch translation exception"] == 2


@pytest.mark.parametrize("streaming", [False, True], ids=["subtitles-and-video", "book-pipeline"])
def test_scheduled_repairs_preserve_transliteration_and_target_language(monkeypatch, streaming):
    from queue import Queue

    source = ["Hello.", "Thanks.", "Wait here.", "Come here."]
    targets = ["Japanese", "Japanese", "Finnish", "Finnish"]
    translations = ["こんにちは。", "ありがとう。", "Odota tässä.", "Tule tänne."]

    def batch(items, *args, **kwargs):
        return {i: (translations[i], "") for i, _ in items if i != 1}, None, 0.01

    def repair(sentence, src, target, **kwargs):
        assert sentence == source[1] and target == "Japanese"
        return "ありがとう。\narigatou"

    def transliterate(items, target, **kwargs):
        assert items == [(0, translations[0])] and target == "Japanese"
        return {0: "konnichiwa"}

    monkeypatch.setattr(translation_engine, "translate_llm_batch_items", batch)
    monkeypatch.setattr(translation_engine, "translate_sentence_simple", repair)
    monkeypatch.setattr(translation_engine, "resolve_batch_transliterations", transliterate)
    monkeypatch.setattr(translation_engine, "resolve_llm_batch_log_dir", lambda *args: None)
    kwargs = dict(client=StubLLMClient([]), llm_batch_size=2, max_workers=2, include_transliteration=True)
    if streaming:
        queue = Queue()
        thread = translation_engine.start_translation_pipeline(
            source, "English", targets, start_sentence=1,
            output_queue=queue, consumer_count=1, **kwargs,
        )
        thread.join(5)
        assert not thread.is_alive()
        tasks = sorted([queue.get_nowait() for _ in source], key=lambda task: task.index)
        assert [task.target_language for task in tasks] == targets
        result = [task.translation + ("\n" + task.transliteration if task.transliteration else "") for task in tasks]
        assert queue.get_nowait() is None
    else:
        result = translation_engine.translate_batch(source, "English", targets, **kwargs)
    assert result == ["こんにちは。\nkonnichiwa", "ありがとう。\narigatou", *translations[2:]]


@pytest.mark.parametrize("source,language,partial,complete", [
    ("How are things? Good. Had a good week.", "Finnish", "Miten menee?",
     "Miten menee? Hyvin. Oli hyvä viikko."),
    ("Şimdi burada sessizce oturup beni bekle. Bu gece nereye gidiyorsun?", "English",
     "Sit here quietly and wait for me.",
     "Sit here quietly and wait for me. Where are you going tonight?"),
])
def test_single_translation_retries_missing_dialogue(monkeypatch, source, language, partial, complete):
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RESPONSE_ATTEMPTS", 2)
    monkeypatch.setattr(translation_engine, "_TRANSLATION_RETRY_DELAY_SECONDS", 0)
    client = StubLLMClient([partial, complete])
    result, error, _ = translation_engine._translate_with_llm(
        source, "Turkish" if language == "English" else "English", language,
        include_transliteration=False, resolved_client=client,
        progress_tracker=None, timeout_seconds=60,
    )
    assert result == complete
    assert not client.responses  # A plausible first sentence must not bypass repair.
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
