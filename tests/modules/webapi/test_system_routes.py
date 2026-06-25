from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from modules.services.job_manager import (
    BackpressurePolicy,
    BackpressureState,
    PipelineJob,
    PipelineJobStatus,
)
from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_auth_service,
    get_pipeline_job_manager,
    get_runtime_context_provider,
)
from modules.webapi import runtime_descriptor as runtime_descriptor_module
from modules.webapi.routes import system_routes as pipeline_system_routes
from modules.webapi.runtime_descriptor import (
    CREATION_DESCRIPTOR,
    LIBRARY_ACTIONS_DESCRIPTOR,
    OFFLINE_EXPORTS_DESCRIPTOR,
    PLAYBACK_STATE_DESCRIPTOR,
    assert_runtime_descriptor_is_public,
    build_runtime_descriptor,
    find_sensitive_descriptor_keys,
)

import pytest

pytestmark = pytest.mark.webapi


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **_: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **_: object) -> None:
        self.messages.append(message % args if args else message)


class _FakeJobManager:
    def __init__(
        self,
        *,
        state: BackpressureState | None = None,
        policy: BackpressurePolicy | None = None,
        accepting: bool = True,
        jobs: dict[str, PipelineJob] | None = None,
    ) -> None:
        self._state = state
        self._policy = policy
        self._accepting = accepting
        self._jobs = jobs or {}

    @property
    def backpressure_state(self) -> BackpressureState | None:
        return self._state

    @property
    def backpressure_policy(self) -> BackpressurePolicy | None:
        return self._policy

    @property
    def is_accepting_jobs(self) -> bool:
        return self._accepting

    def list(self, **_: Any) -> dict[str, PipelineJob]:
        return self._jobs


class _StubRuntimeContextProvider:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def resolve_config(self) -> dict[str, Any]:
        return dict(self._config)


@pytest.fixture
def admin_system_client(tmp_path) -> Iterator[tuple[TestClient, str, _FakeJobManager]]:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("admin", "secret", roles=["admin"])
    admin_token = auth_service.session_manager.create_session("admin")

    manager = _FakeJobManager(
        state=BackpressureState(
            queue_depth=2,
            pending_count=2,
            active_count=1,
            rejection_count=3,
            delay_count=4,
            is_under_pressure=True,
        ),
        policy=BackpressurePolicy(soft_limit=2, hard_limit=5),
        accepting=True,
    )

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager

    with TestClient(app) as client:
        yield client, admin_token, manager

    app.dependency_overrides.clear()


def test_runtime_descriptor_helper_returns_pipeline_contract() -> None:
    payload = build_runtime_descriptor("test-version")

    assert payload["status"] == "ok"
    assert payload["app"] == "ebook-tools"
    assert payload["service"] == "ebook-tools-api"
    assert payload["version"] == "test-version"
    assert payload["healthPath"] == "/_health"
    assert payload["auth"] == {
        "loginPath": "/api/auth/login",
        "sessionPath": "/api/auth/session",
        "tokenTransport": "Authorization: Bearer",
    }
    assert payload["clientConfig"] == {
        "apiBaseUrlEnvironment": [
            "INTERACTIVE_READER_API_BASE_URL",
            "EBOOK_TOOLS_API_BASE_URL",
            "E2E_API_BASE_URL",
        ],
        "credentialEnvironment": [
            "E2E_USERNAME",
            "E2E_PASSWORD",
        ],
        "sessionTokenStorage": "device-keychain",
        "legacyTokenMigration": "userdefaults-authToken",
    }
    assert payload["applePipeline"] == {
        "manifestId": "ebook-tools",
        "simulatorProfiles": ["ios", "ipados", "tvos", "tvos-cinema"],
        "deviceProfiles": ["iphone", "ipad", "appletv", "cinema"],
    }
    assert payload["creation"] == CREATION_DESCRIPTOR
    assert payload["creation"]["acquisitionProvidersPath"] == "/api/acquisition/providers"
    assert payload["creation"]["acquisitionDiscoverPath"] == "/api/acquisition/discover"
    assert payload["offlineExports"] == {
        "createPath": "/api/exports",
        "downloadPathTemplate": "/api/exports/{export_id}/download",
        "sourceKinds": ["job", "library"],
        "playerTypes": ["interactive-text"],
    }
    assert payload["offlineExports"] == OFFLINE_EXPORTS_DESCRIPTOR | {
        "sourceKinds": ["job", "library"],
        "playerTypes": ["interactive-text"],
    }
    assert payload["libraryActions"] == LIBRARY_ACTIONS_DESCRIPTOR
    assert payload["playbackState"] == PLAYBACK_STATE_DESCRIPTOR
    assert_runtime_descriptor_is_public(payload)


def test_runtime_descriptor_returns_fresh_public_lists() -> None:
    first = build_runtime_descriptor("test-version")
    second = build_runtime_descriptor("test-version")

    first["clientConfig"]["apiBaseUrlEnvironment"].append("MUTATED")
    first["applePipeline"]["simulatorProfiles"].append("mutated")
    first["creation"]["bookOptionsPath"] = "MUTATED"

    assert second["clientConfig"]["apiBaseUrlEnvironment"] == [
        "INTERACTIVE_READER_API_BASE_URL",
        "EBOOK_TOOLS_API_BASE_URL",
        "E2E_API_BASE_URL",
    ]
    assert second["applePipeline"]["simulatorProfiles"] == [
        "ios",
        "ipados",
        "tvos",
        "tvos-cinema",
    ]
    assert second["creation"]["bookOptionsPath"] == "/api/books/options"


def test_runtime_descriptor_uses_prevalidated_static_template(monkeypatch) -> None:
    calls = []

    def fail_if_called(payload: object) -> None:
        calls.append(payload)
        raise AssertionError("runtime descriptor guard should not run per request")

    monkeypatch.setattr(
        runtime_descriptor_module,
        "assert_runtime_descriptor_is_public",
        fail_if_called,
    )

    payload = build_runtime_descriptor("fast-path")

    assert payload["version"] == "fast-path"
    assert calls == []


def test_runtime_descriptor_guard_flags_secret_like_keys() -> None:
    payload = {
        "clientConfig": {
            "tokenTransport": "Authorization: Bearer",
            "sessionTokenStorage": "device-keychain",
            "nested": [{"apiSecret": "redacted"}],
        }
    }

    assert find_sensitive_descriptor_keys(payload) == ["apisecret"]
    with pytest.raises(ValueError, match="apisecret"):
        assert_runtime_descriptor_is_public(payload)


def test_pipeline_defaults_endpoint_returns_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)
    secret_input = tmp_path / "Secret Book.epub"
    secret_input.write_text("epub", encoding="utf-8")
    app = create_app()
    app.dependency_overrides[get_runtime_context_provider] = lambda: _StubRuntimeContextProvider(
        {
            "input_file": str(secret_input),
            "books_dir": str(tmp_path),
            "target_language": "Arabic",
        }
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/pipelines/defaults",
                headers={"X-User-Id": "tester", "X-User-Role": "editor"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["config"]["input_file"] == str(secret_input)
    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline defaults result=success" in rendered_logs
    assert "config_keys=3" in rendered_logs
    assert "has_input_file=True" in rendered_logs
    assert "tester" not in rendered_logs
    assert str(secret_input) not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_pipeline_defaults_route_duration_seconds_count{operation="defaults",result="success"}'
        in metrics_response.text
    )


def test_pipeline_defaults_endpoint_rejects_viewer_with_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)
    app = create_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/pipelines/defaults",
            headers={"X-User-Id": "viewer-user", "X-User-Role": "viewer"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 403
    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline defaults result=forbidden" in rendered_logs
    assert "viewer-user" not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_pipeline_defaults_route_duration_seconds_count{operation="defaults",result="forbidden"}'
        in metrics_response.text
    )


def test_llm_models_endpoint_records_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    threadpool_calls: list[str] = []
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)

    def fake_list_available_llm_models() -> list[str]:
        return ["ollama_local:secret-model", "lmstudio_local:private-model"]

    async def fake_run_in_threadpool(func, *args, **kwargs):
        threadpool_calls.append(getattr(func, "__name__", repr(func)))
        return func(*args, **kwargs)

    monkeypatch.setattr(pipeline_system_routes, "list_available_llm_models", fake_list_available_llm_models)
    monkeypatch.setattr(pipeline_system_routes, "run_in_threadpool", fake_run_in_threadpool)
    app = create_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/pipelines/llm-models",
            headers={"X-User-Id": "model-viewer", "X-User-Role": "viewer"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "models": ["ollama_local:secret-model", "lmstudio_local:private-model"]
    }
    assert threadpool_calls == ["fake_list_available_llm_models"]
    rendered_logs = "\n".join(logger.messages)
    assert "LLM model inventory result=success" in rendered_logs
    assert "models=2" in rendered_logs
    assert "model-viewer" not in rendered_logs
    assert "secret-model" not in rendered_logs
    assert "private-model" not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_llm_model_route_duration_seconds_count{operation="list",result="success"}'
        in metrics_response.text
    )


def test_llm_models_endpoint_rejects_guest_with_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)
    app = create_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/pipelines/llm-models",
            headers={"X-User-Id": "guest-user", "X-User-Role": "guest"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 403
    rendered_logs = "\n".join(logger.messages)
    assert "LLM model inventory result=forbidden" in rendered_logs
    assert "guest-user" not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_llm_model_route_duration_seconds_count{operation="list",result="forbidden"}'
        in metrics_response.text
    )


def test_public_runtime_descriptor_returns_non_secret_contract() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/system/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"] == "ebook-tools"
    assert payload["service"] == "ebook-tools-api"
    assert payload["healthPath"] == "/_health"
    assert payload["auth"]["loginPath"] == "/api/auth/login"
    assert payload["auth"]["sessionPath"] == "/api/auth/session"
    assert payload["clientConfig"]["sessionTokenStorage"] == "device-keychain"
    assert payload["clientConfig"]["legacyTokenMigration"] == "userdefaults-authToken"
    assert "INTERACTIVE_READER_API_BASE_URL" in payload["clientConfig"]["apiBaseUrlEnvironment"]
    assert payload["clientConfig"]["credentialEnvironment"] == [
        "E2E_USERNAME",
        "E2E_PASSWORD",
    ]
    assert payload["applePipeline"]["manifestId"] == "ebook-tools"
    assert payload["applePipeline"]["simulatorProfiles"] == [
        "ios",
        "ipados",
        "tvos",
        "tvos-cinema",
    ]
    assert payload["applePipeline"]["deviceProfiles"] == [
        "iphone",
        "ipad",
        "appletv",
        "cinema",
    ]
    assert payload["creation"] == CREATION_DESCRIPTOR
    assert_runtime_descriptor_is_public(payload)


def test_admin_system_status_returns_queue_pressure_snapshot(admin_system_client) -> None:
    client, admin_token, _ = admin_system_client

    response = client.get(
        "/api/admin/system/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["queuePressure"] == {
        "acceptingJobs": True,
        "isUnderPressure": True,
        "queueDepth": 2,
        "activeCount": 1,
        "softLimit": 2,
        "hardLimit": 5,
        "rejectionCount": 3,
        "delayCount": 4,
    }


def test_pipeline_intake_status_returns_editor_queue_snapshot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("editor", "secret", roles=["editor"])
    editor_token = auth_service.session_manager.create_session("editor")

    manager = _FakeJobManager(
        state=BackpressureState(
            queue_depth=4,
            pending_count=4,
            active_count=2,
            rejection_count=9,
            delay_count=7,
            is_under_pressure=True,
        ),
        policy=BackpressurePolicy(soft_limit=3, hard_limit=6),
        accepting=True,
    )

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_pipeline_job_manager] = lambda: manager

    with TestClient(app) as client:
        response = client.get(
            "/api/pipelines/intake/status",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        metrics_response = client.get("/metrics")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "acceptingJobs": True,
        "isUnderPressure": True,
        "queueDepth": 4,
        "activeCount": 2,
        "softLimit": 3,
        "hardLimit": 6,
        "delayCount": 7,
    }
    assert "rejectionCount" not in response.json()
    rendered_logs = "\n".join(logger.messages)
    assert (
        "Pipeline intake status result=success" in rendered_logs
        and "queue_depth=4" in rendered_logs
        and "active=2" in rendered_logs
        and "accepting=True" in rendered_logs
        and "under_pressure=True" in rendered_logs
    )
    assert "editor" not in rendered_logs
    assert editor_token not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_pipeline_intake_route_duration_seconds_count{operation="status",result="success"}'
        in metrics_response.text
    )


def test_pipeline_intake_status_rejects_viewer(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("viewer", "secret", roles=["viewer"])
    viewer_token = auth_service.session_manager.create_session("viewer")

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_pipeline_job_manager] = lambda: _FakeJobManager()

    with TestClient(app) as client:
        response = client.get(
            "/api/pipelines/intake/status",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        metrics_response = client.get("/metrics")

    app.dependency_overrides.clear()

    assert response.status_code == 403
    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline intake status result=forbidden" in rendered_logs
    assert "viewer" not in rendered_logs
    assert viewer_token not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_pipeline_intake_route_duration_seconds_count{operation="status",result="forbidden"}'
        in metrics_response.text
    )


def test_image_node_availability_records_token_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)

    def fake_probe(base_urls: list[str]) -> tuple[list[str], list[str]]:
        return ([base_urls[0]], base_urls[1:])

    monkeypatch.setattr(pipeline_system_routes, "probe_drawthings_base_urls", fake_probe)
    app = create_app()
    secret_primary = "http://secret-image-node.local:7860"
    secret_fallback = "http://10.0.0.42:7860"

    with TestClient(app) as client:
        response = client.post(
            "/api/pipelines/image-nodes/availability",
            json={"base_urls": [secret_primary, secret_fallback]},
            headers={"X-User-Id": "image-editor", "X-User-Role": "editor"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] == [secret_primary]
    assert payload["unavailable"] == [secret_fallback]
    rendered_logs = "\n".join(logger.messages)
    assert "Image node availability result=success" in rendered_logs
    assert "requested=2" in rendered_logs
    assert "available=1" in rendered_logs
    assert "unavailable=1" in rendered_logs
    assert "image-editor" not in rendered_logs
    assert secret_primary not in rendered_logs
    assert secret_fallback not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_image_node_route_duration_seconds_count{operation="availability",result="success"}'
        in metrics_response.text
    )


def test_image_node_availability_rejects_viewer_with_safe_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(pipeline_system_routes, "logger", logger)
    app = create_app()
    secret_node = "http://secret-image-node.local:7860"

    with TestClient(app) as client:
        response = client.post(
            "/api/pipelines/image-nodes/availability",
            json={"base_urls": [secret_node]},
            headers={"X-User-Id": "image-viewer", "X-User-Role": "viewer"},
        )
        metrics_response = client.get("/metrics")

    assert response.status_code == 403
    rendered_logs = "\n".join(logger.messages)
    assert "Image node availability result=forbidden" in rendered_logs
    assert "image-viewer" not in rendered_logs
    assert secret_node not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_image_node_route_duration_seconds_count{operation="availability",result="forbidden"}'
        in metrics_response.text
    )


def test_restart_request_rejects_when_pipeline_jobs_are_running(admin_system_client) -> None:
    client, admin_token, manager = admin_system_client
    manager._jobs = {
        "job-1": PipelineJob(
            job_id="job-1",
            status=PipelineJobStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
        )
    }

    response = client.post(
        "/api/admin/system/restart",
        json={"delaySeconds": 1, "force": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 409
    assert "1 job(s) currently running" in response.json()["detail"]
