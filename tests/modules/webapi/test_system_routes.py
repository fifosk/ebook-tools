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
from modules.webapi.dependencies import get_auth_service, get_pipeline_job_manager
from modules.webapi.runtime_descriptor import (
    assert_runtime_descriptor_is_public,
    build_runtime_descriptor,
    find_sensitive_descriptor_keys,
)

import pytest

pytestmark = pytest.mark.webapi


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
    assert_runtime_descriptor_is_public(payload)


def test_runtime_descriptor_returns_fresh_public_lists() -> None:
    first = build_runtime_descriptor("test-version")
    second = build_runtime_descriptor("test-version")

    first["clientConfig"]["apiBaseUrlEnvironment"].append("MUTATED")
    first["applePipeline"]["simulatorProfiles"].append("mutated")

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


def test_pipeline_defaults_endpoint_returns_config() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/pipelines/defaults",
            headers={"X-User-Id": "tester", "X-User-Role": "editor"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "config" in payload


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
