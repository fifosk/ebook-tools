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
