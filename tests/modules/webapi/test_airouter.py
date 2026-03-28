"""Tests for the AI Router proxy (/api/airouter/).

Covers authentication, model discovery forwarding, chat completion forwarding
(both streaming and non-streaming), DB-fallback key resolution, and an
external client simulation that mirrors how AI Coworker will integrate using
its service account credentials.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

import modules.webapi.routers.airouter as airouter_mod
from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_auth_service

pytestmark = pytest.mark.webapi


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_auth(tmp_path) -> Tuple[AuthService, str]:
    """Create an auth service with an ai_coworker user and return (service, token)."""
    store_path = tmp_path / "users.json"
    sessions_path = tmp_path / "sessions.json"
    service = AuthService(
        LocalUserStore(storage_path=store_path),
        SessionManager(session_file=sessions_path),
    )
    service.user_store.create_user("ai_coworker", "test-secret", roles=["editor"])
    token = service.session_manager.create_session("ai_coworker")
    return service, token


@pytest.fixture
def auth_client(tmp_path, monkeypatch) -> Iterator[Tuple[TestClient, str]]:
    """Yield (TestClient, bearer_token) with ai_coworker authenticated.

    Sets a fake API key so that chat endpoints pass the ``_require_api_key``
    guard.
    """
    monkeypatch.setattr(airouter_mod, "_API_KEY", "test-cloud-key")
    auth_service, token = _build_auth(tmp_path)
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    with TestClient(app) as client:
        yield client, token
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(tmp_path) -> Iterator[TestClient]:
    """Yield an unauthenticated TestClient."""
    auth_service, _ = _build_auth(tmp_path)
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_MODELS_RESPONSE = {
    "object": "list",
    "data": [
        {"id": "llama3.1:8b", "object": "model", "owned_by": "library"},
        {"id": "gemma2:9b", "object": "model", "owned_by": "library"},
    ],
}

_FAKE_CHAT_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello! How can I help you?"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
}

_FAKE_STREAM_CHUNKS = [
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"},"index":0}]}\n\n',
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":"!"},"index":0}]}\n\n',
    "data: [DONE]\n\n",
]


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


class TestAuthEnforcement:
    """Verify that unauthenticated requests are rejected."""

    def test_models_requires_auth(self, anon_client: TestClient) -> None:
        response = anon_client.get("/api/airouter/v1/models")
        assert response.status_code == 401

    def test_chat_requires_auth(self, anon_client: TestClient) -> None:
        response = anon_client.post(
            "/api/airouter/v1/chat/completions",
            json={"model": "llama3.1:8b", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# API key guard
# ---------------------------------------------------------------------------


class TestApiKeyGuard:
    """Verify that chat completions fail clearly when no cloud API key is set."""

    def test_chat_returns_503_when_no_api_key(
        self, tmp_path, monkeypatch
    ) -> None:
        """Authenticated user gets 503 when OLLAMA_CLOUD_API_KEY is empty."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "")
        auth_service, token = _build_auth(tmp_path)
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: auth_service

        with TestClient(app) as client:
            response = client.post(
                "/api/airouter/v1/chat/completions",
                json={"model": "llama3.1:8b", "messages": [{"role": "user", "content": "hi"}]},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()
        app.dependency_overrides.clear()

    def test_models_works_without_api_key(
        self, tmp_path, monkeypatch
    ) -> None:
        """Model listing should still work even without an API key
        (Ollama Cloud /v1/models doesn't require auth)."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "")
        auth_service, token = _build_auth(tmp_path)
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: auth_service

        with patch("modules.webapi.routers.airouter._get_client") as mock_get_client:
            mock_response = httpx.Response(200, json=_FAKE_MODELS_RESPONSE)
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_async_client

            with TestClient(app) as client:
                response = client.get(
                    "/api/airouter/v1/models",
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 200
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Model listing
# ---------------------------------------------------------------------------


class TestModelListing:
    """Verify model discovery is forwarded correctly."""

    @patch("modules.webapi.routers.airouter._get_client")
    def test_list_models_returns_upstream_response(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        client, token = auth_client

        mock_response = httpx.Response(200, json=_FAKE_MODELS_RESPONSE)
        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        response = client.get(
            "/api/airouter/v1/models",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["object"] == "list"
        assert len(payload["data"]) == 2
        assert payload["data"][0]["id"] == "llama3.1:8b"

    @patch("modules.webapi.routers.airouter._get_client")
    def test_list_models_propagates_upstream_error(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        client, token = auth_client

        mock_response = httpx.Response(503, text="Service Unavailable")
        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        response = client.get(
            "/api/airouter/v1/models",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Chat completions (non-streaming)
# ---------------------------------------------------------------------------


class TestChatCompletions:
    """Verify non-streaming chat completion forwarding."""

    @patch("modules.webapi.routers.airouter._get_client")
    def test_chat_returns_upstream_response(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        client, token = auth_client

        mock_response = httpx.Response(200, json=_FAKE_CHAT_RESPONSE)
        mock_async_client = AsyncMock()
        mock_async_client.post = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        response = client.post(
            "/api/airouter/v1/chat/completions",
            json={
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": "Say hello"}],
                "stream": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["choices"][0]["message"]["content"] == "Hello! How can I help you?"
        assert payload["usage"]["total_tokens"] == 18

    @patch("modules.webapi.routers.airouter._get_client")
    def test_chat_injects_api_key_header(
        self, mock_get_client, auth_client: Tuple[TestClient, str], monkeypatch
    ) -> None:
        """Verify the server-side OLLAMA_CLOUD_API_KEY is injected into upstream requests."""
        client, token = auth_client

        monkeypatch.setattr(airouter_mod, "_API_KEY", "test-cloud-key-12345")

        captured_headers: dict = {}

        async def _capture_post(url, *, content, headers):
            captured_headers.update(headers)
            return httpx.Response(200, json=_FAKE_CHAT_RESPONSE)

        mock_async_client = AsyncMock()
        mock_async_client.post = _capture_post
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        client.post(
            "/api/airouter/v1/chat/completions",
            json={
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": "test"}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert captured_headers.get("Authorization") == "Bearer test-cloud-key-12345"

    @patch("modules.webapi.routers.airouter._get_client")
    def test_chat_propagates_upstream_error(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        client, token = auth_client

        mock_response = httpx.Response(429, text="Rate limit exceeded")
        mock_async_client = AsyncMock()
        mock_async_client.post = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        response = client.post(
            "/api/airouter/v1/chat/completions",
            json={
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": "hello"}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 429


# ---------------------------------------------------------------------------
# Chat completions (streaming)
# ---------------------------------------------------------------------------


class _FakeStreamResponse:
    """Minimal async-context-manager mock for ``httpx.AsyncClient.stream()``."""

    def __init__(self, status_code: int, chunks: list[bytes]) -> None:
        self.status_code = status_code
        self._chunks = chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def aread(self) -> bytes:
        return b"".join(self._chunks)

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class TestChatCompletionsStreaming:
    """Verify streaming (SSE) chat completion forwarding."""

    @patch("modules.webapi.routers.airouter._get_client")
    def test_streaming_chat_returns_sse(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        client, token = auth_client

        raw_bytes = "".join(_FAKE_STREAM_CHUNKS).encode("utf-8")
        fake_stream = _FakeStreamResponse(200, [raw_bytes])

        mock_async_client = AsyncMock()
        mock_async_client.stream = lambda *a, **kw: fake_stream
        mock_async_client.aclose = AsyncMock()
        mock_get_client.return_value = mock_async_client

        response = client.post(
            "/api/airouter/v1/chat/completions",
            json={
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.text
        assert "Hello" in body
        assert "[DONE]" in body


# ---------------------------------------------------------------------------
# External client simulation (AI Coworker integration)
# ---------------------------------------------------------------------------


class TestExternalClientSimulation:
    """Simulate the full AI Coworker integration flow.

    This mirrors what an external consumer will do:
    1. Login with username/password to get a session token
    2. List available models
    3. Send a chat completion request
    """

    @patch("modules.webapi.routers.airouter._get_client")
    def test_full_ai_coworker_flow(
        self, mock_get_client, tmp_path, monkeypatch
    ) -> None:
        """End-to-end: login → list models → chat completion."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "test-cloud-key")

        # --- Setup auth with ai_coworker credentials ---
        store_path = tmp_path / "users.json"
        sessions_path = tmp_path / "sessions.json"
        auth_service = AuthService(
            LocalUserStore(storage_path=store_path),
            SessionManager(session_file=sessions_path),
        )
        auth_service.user_store.create_user(
            "ai_coworker", "s3cure-p@ssw0rd!", roles=["editor"]
        )

        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: auth_service

        with TestClient(app) as client:
            # --- Step 1: Login with credentials ---
            login_resp = client.post(
                "/api/auth/login",
                json={"username": "ai_coworker", "password": "s3cure-p@ssw0rd!"},
            )
            assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
            token = login_resp.json()["token"]
            assert token, "Expected a non-empty session token"

            auth_headers = {"Authorization": f"Bearer {token}"}

            # --- Step 2: Discover available models ---
            mock_response = httpx.Response(200, json=_FAKE_MODELS_RESPONSE)
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_async_client

            models_resp = client.get("/api/airouter/v1/models", headers=auth_headers)
            assert models_resp.status_code == 200
            models = models_resp.json()["data"]
            assert len(models) >= 1
            chosen_model = models[0]["id"]

            # --- Step 3: Send a chat completion ---
            mock_chat_response = httpx.Response(200, json=_FAKE_CHAT_RESPONSE)
            mock_async_client_2 = AsyncMock()
            mock_async_client_2.post = AsyncMock(return_value=mock_chat_response)
            mock_async_client_2.__aenter__ = AsyncMock(return_value=mock_async_client_2)
            mock_async_client_2.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_async_client_2

            chat_resp = client.post(
                "/api/airouter/v1/chat/completions",
                json={
                    "model": chosen_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Translate 'hello' to Arabic."},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 256,
                },
                headers=auth_headers,
            )
            assert chat_resp.status_code == 200
            reply = chat_resp.json()
            assert reply["choices"][0]["message"]["content"]
            assert reply["usage"]["total_tokens"] > 0

        app.dependency_overrides.clear()

    def test_expired_or_invalid_token_rejected(self, tmp_path) -> None:
        """Verify that a bogus token gets 401."""
        auth_service, _ = _build_auth(tmp_path)
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: auth_service

        with TestClient(app) as client:
            response = client.get(
                "/api/airouter/v1/models",
                headers={"Authorization": "Bearer bogus-invalid-token"},
            )
            assert response.status_code == 401

        app.dependency_overrides.clear()

    @patch("modules.webapi.routers.airouter._get_client")
    def test_ai_coworker_query_param_auth(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        """AI Coworker can also pass token via ?access_token= query param."""
        client, token = auth_client

        mock_response = httpx.Response(200, json=_FAKE_MODELS_RESPONSE)
        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        response = client.get(f"/api/airouter/v1/models?access_token={token}")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Upstream connection errors
# ---------------------------------------------------------------------------


class TestUpstreamErrors:
    """Verify graceful handling of upstream connectivity issues."""

    @patch("modules.webapi.routers.airouter._get_client")
    def test_upstream_connection_error_returns_502(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        client, token = auth_client

        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        response = client.get(
            "/api/airouter/v1/models",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 502
        assert "Connection refused" in response.json()["detail"]

    @patch("modules.webapi.routers.airouter._get_client")
    def test_upstream_timeout_returns_502(
        self, mock_get_client, auth_client: Tuple[TestClient, str]
    ) -> None:
        client, token = auth_client

        mock_async_client = AsyncMock()
        mock_async_client.post = AsyncMock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        response = client.post(
            "/api/airouter/v1/chat/completions",
            json={
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": "hello"}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 502


# ---------------------------------------------------------------------------
# API key resolution fallback (DB / config settings)
# ---------------------------------------------------------------------------


class TestApiKeyResolution:
    """Verify that _resolve_api_key falls back to config settings."""

    def test_resolve_falls_back_to_settings(self, monkeypatch) -> None:
        """When env var is empty, _resolve_api_key reads from get_settings()."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "")

        mock_settings = MagicMock()
        mock_settings.ollama_api_key = MagicMock()
        mock_settings.ollama_api_key.get_secret_value.return_value = "db-secret-key"

        with patch(
            "modules.config_manager.loader.get_settings", return_value=mock_settings
        ):
            key = airouter_mod._resolve_api_key()

        assert key == "db-secret-key"
        # Verify the key was cached in the module-level _API_KEY
        assert airouter_mod._API_KEY == "db-secret-key"
        # Cleanup
        monkeypatch.setattr(airouter_mod, "_API_KEY", "")

    def test_resolve_prefers_env_var(self, monkeypatch) -> None:
        """When env var is set, _resolve_api_key returns it without touching settings."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "env-var-key")

        key = airouter_mod._resolve_api_key()
        assert key == "env-var-key"

    def test_resolve_returns_empty_when_nothing_configured(
        self, monkeypatch
    ) -> None:
        """Returns empty string when neither env var nor settings have a key."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "")

        mock_settings = MagicMock()
        mock_settings.ollama_api_key = None

        with patch(
            "modules.config_manager.loader.get_settings", return_value=mock_settings
        ):
            key = airouter_mod._resolve_api_key()

        assert key == ""

    @patch("modules.webapi.routers.airouter._get_client")
    def test_chat_uses_db_key_when_env_empty(
        self, mock_get_client, tmp_path, monkeypatch
    ) -> None:
        """End-to-end: env var empty → _resolve_api_key loads from settings → chat works."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "")

        mock_settings = MagicMock()
        mock_settings.ollama_api_key = MagicMock()
        mock_settings.ollama_api_key.get_secret_value.return_value = "fallback-db-key"

        auth_service, token = _build_auth(tmp_path)
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: auth_service

        captured_headers: dict = {}

        async def _capture_post(url, *, content, headers):
            captured_headers.update(headers)
            return httpx.Response(200, json=_FAKE_CHAT_RESPONSE)

        mock_async_client = AsyncMock()
        mock_async_client.post = _capture_post
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_async_client

        with patch(
            "modules.config_manager.loader.get_settings", return_value=mock_settings
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/api/airouter/v1/chat/completions",
                    json={
                        "model": "mistral:7b",
                        "messages": [{"role": "user", "content": "hello"}],
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 200
        assert captured_headers.get("Authorization") == "Bearer fallback-db-key"
        app.dependency_overrides.clear()
        monkeypatch.setattr(airouter_mod, "_API_KEY", "")


# ---------------------------------------------------------------------------
# External client simulation — realistic AI Coworker flow with Ollama Cloud
# ---------------------------------------------------------------------------


class TestExternalClientOllamaCloudSimulation:
    """Simulate AI Coworker calling airouter with only its session token.

    The client authenticates with ebook-tools credentials and sends chat
    completions to Ollama Cloud models (cogito, mistral, etc.) without ever
    providing an Ollama API key — the proxy injects it transparently.
    """

    @patch("modules.webapi.routers.airouter._get_client")
    def test_ai_coworker_chat_with_mistral_model(
        self, mock_get_client, tmp_path, monkeypatch
    ) -> None:
        """AI Coworker authenticates, picks mistral, sends chat — no API key provided."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "server-side-ollama-key")

        store_path = tmp_path / "users.json"
        sessions_path = tmp_path / "sessions.json"
        auth_service = AuthService(
            LocalUserStore(storage_path=store_path),
            SessionManager(session_file=sessions_path),
        )
        auth_service.user_store.create_user(
            "ai_coworker", "s3cure-p@ssw0rd!", roles=["editor"]
        )

        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: auth_service

        # Fake upstream responses
        models_response = {
            "object": "list",
            "data": [
                {"id": "cogito:latest", "object": "model", "owned_by": "library"},
                {"id": "mistral:latest", "object": "model", "owned_by": "library"},
                {"id": "llama3.1:70b", "object": "model", "owned_by": "library"},
            ],
        }
        chat_response = {
            "id": "chatcmpl-xyz789",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "مرحبا! كيف يمكنني مساعدتك؟",
                    },
                    "finish_reason": "stop",
                }
            ],
            "model": "mistral:latest",
            "usage": {"prompt_tokens": 25, "completion_tokens": 12, "total_tokens": 37},
        }

        captured_model_headers: dict = {}
        captured_chat_headers: dict = {}

        async def _capture_get(url, *, headers):
            captured_model_headers.update(headers)
            return httpx.Response(200, json=models_response)

        async def _capture_post(url, *, content, headers):
            captured_chat_headers.update(headers)
            # Verify the request body has the model we chose
            body = json.loads(content)
            assert body["model"] == "mistral:latest"
            return httpx.Response(200, json=chat_response)

        with TestClient(app) as client:
            # Step 1: Login with ai_coworker credentials (NO Ollama key)
            login_resp = client.post(
                "/api/auth/login",
                json={"username": "ai_coworker", "password": "s3cure-p@ssw0rd!"},
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Step 2: Discover models (client only sends session token)
            mock_async_client = AsyncMock()
            mock_async_client.get = _capture_get
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_async_client

            models_resp = client.get("/api/airouter/v1/models", headers=headers)
            assert models_resp.status_code == 200
            available_models = [m["id"] for m in models_resp.json()["data"]]
            assert "mistral:latest" in available_models

            # Verify the proxy injected the server-side key (not the client's session token)
            assert captured_model_headers["Authorization"] == "Bearer server-side-ollama-key"

            # Step 3: Chat completion with chosen model (still no Ollama key from client)
            mock_async_client_2 = AsyncMock()
            mock_async_client_2.post = _capture_post
            mock_async_client_2.__aenter__ = AsyncMock(return_value=mock_async_client_2)
            mock_async_client_2.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_async_client_2

            chat_resp = client.post(
                "/api/airouter/v1/chat/completions",
                json={
                    "model": "mistral:latest",
                    "messages": [
                        {"role": "system", "content": "You are a helpful translator."},
                        {"role": "user", "content": "Translate 'hello' to Arabic."},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 512,
                },
                headers=headers,
            )
            assert chat_resp.status_code == 200

            reply = chat_resp.json()
            assert reply["model"] == "mistral:latest"
            assert reply["choices"][0]["message"]["content"]  # non-empty
            assert reply["usage"]["total_tokens"] > 0

            # Verify the proxy injected the server-side key, NOT the client's session token
            assert captured_chat_headers["Authorization"] == "Bearer server-side-ollama-key"

        app.dependency_overrides.clear()

    @patch("modules.webapi.routers.airouter._get_client")
    def test_ai_coworker_streaming_chat_with_cogito(
        self, mock_get_client, tmp_path, monkeypatch
    ) -> None:
        """AI Coworker streams a chat completion from cogito model — no Ollama key provided."""
        monkeypatch.setattr(airouter_mod, "_API_KEY", "server-side-ollama-key")

        auth_service, token = _build_auth(tmp_path)
        app = create_app()
        app.dependency_overrides[get_auth_service] = lambda: auth_service

        stream_chunks = [
            'data: {"id":"chatcmpl-s1","object":"chat.completion.chunk","model":"cogito:latest","choices":[{"delta":{"content":"مرحبا"},"index":0}]}\n\n',
            'data: {"id":"chatcmpl-s1","object":"chat.completion.chunk","model":"cogito:latest","choices":[{"delta":{"content":"!"},"index":0}]}\n\n',
            "data: [DONE]\n\n",
        ]
        raw_bytes = "".join(stream_chunks).encode("utf-8")
        fake_stream = _FakeStreamResponse(200, [raw_bytes])

        mock_async_client = AsyncMock()
        mock_async_client.stream = lambda *a, **kw: fake_stream
        mock_async_client.aclose = AsyncMock()
        mock_get_client.return_value = mock_async_client

        with TestClient(app) as client:
            response = client.post(
                "/api/airouter/v1/chat/completions",
                json={
                    "model": "cogito:latest",
                    "messages": [{"role": "user", "content": "Say hello in Arabic"}],
                    "stream": True,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.text
        assert "مرحبا" in body
        assert "cogito:latest" in body
        assert "[DONE]" in body

        app.dependency_overrides.clear()
