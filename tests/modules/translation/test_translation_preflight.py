from types import SimpleNamespace

import pytest
import requests

from modules import translation_preflight as pf
from modules.llm_client import ClientSettings, LLMClient

pytestmark = pytest.mark.translation


@pytest.fixture(autouse=True)
def clean_cache():
    pf._cache.clear()
    yield
    pf._cache.clear()


def cloud():
    return LLMClient(ClientSettings(model="test-model", llm_source="cloud", api_key="test-token",
                                   api_url="https://example.test/v1/chat/completions"))


@pytest.mark.parametrize("status,payload,expected", [
    (200, {"data": [{"id": "test-model"}]}, "available"),
    (200, {"data": [{"id": "other-model"}]}, "unavailable"),
    (200, {"data": []}, "unavailable"),
    (200, {}, "unknown"),
    (200, {"data": [{"id": ["malformed"]}]}, "unknown"),
    (401, {"error": "private-provider-message"}, "unavailable"),
    (403, {}, "unavailable"),
    (429, {}, "unknown"),
    (503, {}, "unknown"),
])
def test_authoritative_availability_and_safe_ttl(monkeypatch, status, payload, expected):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(status_code=status, json=lambda: payload)
    monkeypatch.setattr(pf.requests, "get", get)
    result = pf.check_model(cloud())
    assert result[0] == expected
    assert "private-provider-message" not in result[1]
    assert pf.check_model(cloud()) == result
    assert len(calls) == 1
    assert calls[0][0] == "https://example.test/v1/models"
    assert calls[0][1]["timeout"] == (2, 3)
    assert "test-token" not in repr(pf._cache)


def test_network_failure_does_not_invent_model_absence(monkeypatch):
    def get(*args, **kwargs):
        raise requests.Timeout("private endpoint")
    monkeypatch.setattr(pf.requests, "get", get)
    assert pf.check_model(cloud())[0] == "unknown"


def test_managed_job_fails_before_translation_and_never_changes_model(tmp_path, monkeypatch):
    from modules.progress_tracker import ProgressTracker
    from modules import translation_engine as te
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(pf.cfg, "get_runtime_context", lambda *args: SimpleNamespace(output_dir=tmp_path / "media"))
    monkeypatch.setattr(pf, "check_model", lambda client: ("unavailable", "Selected model unavailable"))
    monkeypatch.setattr(te, "_iter_translated_batches", lambda *args, **kwargs: pytest.fail("inference was scheduled"))
    llm = cloud()
    tracker = ProgressTracker()
    with pytest.raises(RuntimeError, match="Selected model unavailable"):
        te.translate_batch(["Hello"], "English", "Finnish", client=llm, llm_batch_size=10, progress_tracker=tracker)
    assert llm.model == "test-model"
    assert tracker.get_generated_files()["translation_preflight"]["status"] == "unavailable"


@pytest.mark.parametrize("kind", ["subtitle", "video"])
@pytest.mark.parametrize("batch_size", [1, 2])
@pytest.mark.parametrize("explicit_model", [None, "explicit-model"])
def test_preflight_and_inference_share_effective_default(
    tmp_path, monkeypatch, kind, batch_size, explicit_model,
):
    from modules import llm_client_manager as manager, translation_engine as engine
    from modules.services.youtube_dubbing import translation as video
    from modules.services.youtube_dubbing.common import _AssDialogue
    from modules.subtitles import processing as subtitle
    from modules.subtitles.language import SubtitleLanguageContext
    from modules.subtitles.models import SubtitleJobOptions

    (tmp_path / "data").mkdir()
    monkeypatch.setattr(pf.cfg, "get_runtime_context", lambda *args: SimpleNamespace(output_dir=tmp_path / "media", llm_source="local", local_ollama_url="http://bundled.invalid:11434/api", cloud_ollama_url="https://cloud.invalid/v1/chat/completions"))
    monkeypatch.setattr(pf.cfg, "DEFAULT_MODEL", "bundled-model")
    monkeypatch.setattr(manager, "_DEFAULT_CLIENT_SETTINGS", ClientSettings(
        model="configured-model", llm_source="cloud", api_key="test-token",
        api_url="https://configured.invalid/v1/chat/completions", allow_fallback=False))
    checked, inferred = [], []
    def identity(client):
        from modules.llm_endpoints import resolve_endpoints
        return (client.model, tuple(endpoint.url for endpoint in resolve_endpoints(client.settings)))
    def check(client):
        checked.append(identity(client))
        return "available", "Fixture model available"
    def single(*args, resolved_client, **kwargs):
        inferred.append(identity(resolved_client))
        return "Odota täällä.", None, 0.01
    def batch(items, *args, resolved_client, **kwargs):
        inferred.append(identity(resolved_client))
        return {idx: ("Odota täällä.", "") for idx, _ in items}, None, 0.01
    monkeypatch.setattr(pf, "check_model", check)
    monkeypatch.setattr(engine, "_translate_with_llm", single)
    monkeypatch.setattr(engine, "translate_llm_batch_items", batch)
    if kind == "video":
        result = video.translate_dialogues(
            [_AssDialogue(start=0, end=2, translation="Wait here.", original="Wait here.")],
            source_language="English", target_language="Finnish", translation_batch_size=batch_size,
            include_transliteration=False, transliterator=None, llm_model=explicit_model,
            tracker=None, offset=0, total_dialogues=1)
        assert result[0].translation == "Odota täällä."
    else:
        monkeypatch.setattr(subtitle, "_resolve_language_context", lambda *args: SubtitleLanguageContext(
            detected_language="English", detection_source="test", detection_sample="",
            translation_source_language="English", origin_language="English", origin_translation_needed=False))
        source = tmp_path / "source.srt"
        source.write_text("1\n00:00:00,000 --> 00:00:02,000\nWait here.\n")
        output = tmp_path / "result.srt"
        subtitle.process_subtitle_file(source, output, SubtitleJobOptions(
            input_language="English", target_language="Finnish", llm_model=explicit_model,
            translation_batch_size=batch_size, enable_transliteration=False, highlight=False))
        assert "Odota täällä." in output.read_text()
    assert checked and inferred
    assert {entry[0] for entry in inferred} == {explicit_model or "configured-model"}
    assert all(entry == inferred[0] for entry in checked)
