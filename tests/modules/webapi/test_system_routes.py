from __future__ import annotations

from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.runtime_descriptor import (
    assert_runtime_descriptor_is_public,
    build_runtime_descriptor,
    find_sensitive_descriptor_keys,
)

import pytest

pytestmark = pytest.mark.webapi


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
