from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.llm_client import LLMResponse
from modules.webapi.application import create_app
from modules.webapi.routers import assistant as assistant_router

import pytest

pytestmark = pytest.mark.webapi


class _FakeClient:
    def __init__(self, model: str = "fake-model") -> None:
        self.model = model

    def send_chat_request(self, payload, *, max_attempts=3, timeout=None, validator=None, backoff_seconds=1.0):
        _ = payload
        return LLMResponse(
            text="Definition: test answer",
            status_code=200,
            token_usage={"prompt_eval_count": 1, "eval_count": 2},
            raw={"ok": True},
            error=None,
            source="local",
        )

    def close(self) -> None:
        return


@contextmanager
def _fake_create_client(*, model=None, **_kwargs):
    client = _FakeClient(model=model or "fake-model")
    try:
        yield client
    finally:
        client.close()


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def _record(self, message: str, *args, **kwargs) -> None:
        if args:
            message = message % args
        self.messages.append(message)

    def debug(self, message: str, *args, **kwargs) -> None:
        self._record(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._record(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._record(message, *args, **kwargs)

    @property
    def rendered(self) -> str:
        return "\n".join(self.messages)


def _has_assistant_lookup_metric_count(
    metrics_text: str,
    *,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_assistant_lookup_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == "lookup"
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


def test_assistant_lookup_endpoint_returns_answer(monkeypatch) -> None:
    monkeypatch.setattr("modules.services.assistant.create_client", _fake_create_client)
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/lookup",
            json={
                "query": "hola",
                "input_language": "Spanish",
                "lookup_language": "English",
                "llm_model": "demo-model",
                "history": [{"role": "user", "content": "previous"}],
                "context": {"source": "test"},
            },
            headers={"X-User-Id": "test-user"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert payload["model"] == "demo-model"
    assert payload["source"] == "local"


def test_assistant_lookup_records_token_safe_success_telemetry(monkeypatch) -> None:
    logger = _RecordingLogger()
    monkeypatch.setattr("modules.services.assistant.create_client", _fake_create_client)
    monkeypatch.setattr(assistant_router, "logger", logger)
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/lookup",
            json={
                "query": "secret lookup word",
                "input_language": "Spanish",
                "lookup_language": "English",
                "llm_model": "private-model",
            },
            headers={"X-User-Id": "test-user"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert metrics_response.status_code == 200
    assert _has_assistant_lookup_metric_count(metrics_response.text, result="success")
    assert "Assistant lookup route operation=lookup result=success" in logger.rendered
    rendered = logger.rendered + metrics_response.text
    assert "secret lookup word" not in rendered
    assert "Spanish" not in rendered
    assert "English" not in rendered
    assert "private-model" not in rendered


def test_assistant_lookup_backend_failure_uses_generic_detail_and_token_safe_telemetry(
    monkeypatch,
) -> None:
    logger = _RecordingLogger()
    secret_message = (
        "LLM failed for secret lookup word using private-model at "
        "/Volumes/Data/private/llm.log api_key=secret-key"
    )

    def _fail_lookup(**kwargs):
        raise RuntimeError(secret_message)

    monkeypatch.setattr(assistant_router, "lookup_dictionary_entry", _fail_lookup)
    monkeypatch.setattr(assistant_router, "logger", logger)
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/lookup",
            json={
                "query": "secret lookup word",
                "input_language": "Turkish",
                "lookup_language": "English",
                "llm_model": "private-model",
                "system_prompt": "private prompt text",
            },
            headers={"X-User-Id": "test-user"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 502
    assert response.json() == {"detail": "Unable to complete assistant lookup."}
    assert metrics_response.status_code == 200
    assert _has_assistant_lookup_metric_count(metrics_response.text, result="error")
    assert "response detail suppressed" in logger.rendered
    rendered = response.text + logger.rendered + metrics_response.text
    assert secret_message not in rendered
    assert "secret lookup word" not in rendered
    assert "private-model" not in rendered
    assert "/Volumes/Data/private/llm.log" not in rendered
    assert "secret-key" not in rendered
    assert "private prompt text" not in rendered
