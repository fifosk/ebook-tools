from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from modules.llm_client import LLMResponse
from modules.webapi.application import create_app

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
