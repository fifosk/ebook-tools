import json
from types import SimpleNamespace

import pytest

from modules import translation_batch as tb, translation_checkpoints as cp, translation_engine as te
from modules.llm_client import ClientSettings, LLMClient, LLMResponse
from modules.progress_tracker import ProgressTracker

pytestmark = pytest.mark.translation


@pytest.fixture
def job_context(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    context = SimpleNamespace(output_dir=tmp_path / "media")
    monkeypatch.setattr(cp.cfg, "get_runtime_context", lambda *args: context)
    return context


def client():
    return LLMClient(ClientSettings(model="test-model", llm_source="cloud", api_url="https://example.test/v1/chat/completions"))


def test_checkpoint_request_identity_private_and_optout(job_context, monkeypatch):
    llm = client()
    path = cp.checkpoint_path(llm, {"text": "Hello", "prompt": "full translation"}, kind="sentence")
    cp.write_checkpoint(path, "Hei")
    assert cp.read_checkpoint(path) == "Hei"
    assert "Hello" not in str(path)
    for request in ({"text": "Other"}, {"text": "Hello", "prompt": "new prompt"}):
        assert cp.read_checkpoint(cp.checkpoint_path(llm, request, kind="sentence")) is None
    monkeypatch.setattr(cp, "_VALIDATOR_VERSION", "new-validator")
    assert cp.checkpoint_path(llm, {"text": "Hello", "prompt": "full translation"}, kind="sentence") != path
    monkeypatch.setenv("EBOOK_TRANSLATION_CHECKPOINTS", "0")
    assert cp.checkpoint_path(llm, {}, kind="sentence") is None


def test_sentence_reuses_disk_but_not_invalid_text_or_changed_model(job_context, monkeypatch):
    calls = []
    def send(self, payload, **kwargs):
        calls.append(payload)
        return LLMResponse(text="Odota tässä.", status_code=200, token_usage={})
    monkeypatch.setattr(LLMClient, "send_chat_request", send)
    tracker = ProgressTracker()
    def run(llm):
        return te._translate_with_llm("Wait here.", "English", "Finnish", include_transliteration=False,
                                     resolved_client=llm, progress_tracker=tracker, timeout_seconds=1)
    assert run(client())[0] == "Odota tässä."
    assert run(client())[2] == 0  # fresh client reads persisted checkpoint
    assert len(calls) == 1
    assert tracker.get_generated_files()["translation_flow"]["cached"] == 1
    stored = next((job_context.output_dir.parent / "data/translation_checkpoints").glob("*.json"))
    stored.write_text(json.dumps("N/A"))
    run(client())
    assert len(calls) == 2
    other = LLMClient(client().settings.with_updates(model="other-model"))
    run(other)
    assert len(calls) == 3
    stored.write_text("{truncated")
    run(client())
    assert len(calls) == 4


def test_batch_revalidates_all_items_and_never_checkpoints_incomplete_batch(job_context, monkeypatch):
    from modules.llm_batch import JsonBatchResponse
    calls = []
    payload = {"items": [{"id": 0, "translation": "Odota tässä."}, {"id": 1, "translation": "Tule tänne."}]}
    def send(**kwargs):
        calls.append(kwargs)
        return JsonBatchResponse(payload, "", None, .1)
    monkeypatch.setattr(tb.llm_batch, "request_json_batch", send)
    tracker = ProgressTracker()
    def run():
        return tb.translate_llm_batch_items([(0, "Wait here."), (1, "Come here.")], "English", "Finnish",
            include_transliteration=False, resolved_client=client(), progress_tracker=tracker, timeout_seconds=1)
    original = run()[0]
    assert run() == (original, None, 0.0)
    assert len(calls) == 1
    stored = next((job_context.output_dir.parent / "data/translation_checkpoints").glob("*.json"))
    stored.write_text(json.dumps({"items": [{"id": 0, "translation": "N/A"}]}))
    payload["items"][1]["translation"] = "N/A"
    result, error, _ = run()
    assert len(calls) == 2
    assert tb.validate_batch_translation("Come here.", result.get(1, ("", ""))[0], "Finnish")
    run()
    assert len(calls) == 3  # rejected output was not saved


def test_write_failure_is_a_miss_and_different_jobs_do_not_share(job_context, monkeypatch, tmp_path):
    path = cp.checkpoint_path(client(), {}, kind="sentence")
    monkeypatch.setattr(cp.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("full")))
    cp.write_checkpoint(path, "Hei")
    assert cp.read_checkpoint(path) is None
    assert list(path.parent.glob(".checkpoint-*")) == []
    old_path = path
    job_context.output_dir = tmp_path / "other-job/media"
    (job_context.output_dir.parent / "data").mkdir(parents=True)
    assert cp.checkpoint_path(client(), {}, kind="sentence") != old_path


def test_flow_aggregates_windows_and_translation_total_excludes_audio():
    tracker = ProgressTracker(total_blocks=8, throttle_interval=0)
    tracker.set_translation_total(4)
    events = []
    tracker.register_observer(events.append)
    tracker.record_translation_flow(accepted=2, cached=1, in_flight=2)
    tracker.record_translation_flow(accepted=2, repaired=1, in_flight=0)
    flow = tracker.get_generated_files()["translation_flow"]
    assert flow == {"accepted": 4, "cached": 1, "repaired": 1, "failed": 0, "in_flight": 0}
    tracker.record_translation_completion(0, 1)
    assert events[-1].metadata["translation_total"] == 4
    assert events[-1].snapshot.total == 4
