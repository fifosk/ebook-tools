from __future__ import annotations

from fastapi.testclient import TestClient

from modules.webapi.application import create_app

import pytest

pytestmark = pytest.mark.webapi


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
