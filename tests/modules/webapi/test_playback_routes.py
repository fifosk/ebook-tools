"""Tests for the playback heartbeat endpoint."""

from __future__ import annotations

from typing import Iterator, Tuple
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_analytics_service, get_auth_service

pytestmark = pytest.mark.webapi


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _build_auth(tmp_path) -> Tuple[AuthService, str]:
    store_path = tmp_path / "users.json"
    sessions_path = tmp_path / "sessions.json"
    service = AuthService(
        LocalUserStore(storage_path=store_path),
        SessionManager(session_file=sessions_path),
    )
    service.user_store.create_user("tester", "secret", roles=["admin"])
    token = service.session_manager.create_session("tester")
    return service, token


@pytest.fixture
def client_with_analytics(tmp_path) -> Iterator[Tuple[TestClient, str, MagicMock]]:
    """TestClient with a mock analytics service and authenticated user."""
    auth_service, token = _build_auth(tmp_path)
    mock_analytics = MagicMock()

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics

    with TestClient(app) as client:
        yield client, token, mock_analytics

    app.dependency_overrides.clear()


@pytest.fixture
def client_no_analytics(tmp_path) -> Iterator[Tuple[TestClient, str]]:
    """TestClient without analytics (simulates no DATABASE_URL)."""
    auth_service, token = _build_auth(tmp_path)

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_analytics_service] = lambda: None

    with TestClient(app) as client:
        yield client, token

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHeartbeatEndpoint:

    def test_valid_heartbeat(self, client_with_analytics) -> None:
        client, token, mock_analytics = client_with_analytics
        response = client.post(
            "/api/playback/heartbeat",
            json={
                "job_id": "test-job",
                "language": "ar",
                "track_kind": "translation",
                "delta_seconds": 30,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_analytics.record_playback_heartbeat.assert_called_once_with(
            user_id="tester",
            job_id="test-job",
            language="ar",
            track_kind="translation",
            delta_seconds=30,
        )

    def test_requires_auth(self, client_with_analytics) -> None:
        client, _, _ = client_with_analytics
        response = client.post(
            "/api/playback/heartbeat",
            json={
                "job_id": "test-job",
                "language": "ar",
                "track_kind": "translation",
                "delta_seconds": 10,
            },
        )
        assert response.status_code == 401

    def test_rejects_negative_delta(self, client_with_analytics) -> None:
        client, token, _ = client_with_analytics
        response = client.post(
            "/api/playback/heartbeat",
            json={
                "job_id": "test-job",
                "language": "en",
                "track_kind": "original",
                "delta_seconds": -5,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_rejects_delta_over_300(self, client_with_analytics) -> None:
        client, token, _ = client_with_analytics
        response = client.post(
            "/api/playback/heartbeat",
            json={
                "job_id": "test-job",
                "language": "en",
                "track_kind": "original",
                "delta_seconds": 500,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_graceful_without_analytics(self, client_no_analytics) -> None:
        """When analytics_service is None, endpoint should still return 200."""
        client, token = client_no_analytics
        response = client.post(
            "/api/playback/heartbeat",
            json={
                "job_id": "test-job",
                "language": "ar",
                "track_kind": "translation",
                "delta_seconds": 15,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_zero_delta_accepted(self, client_with_analytics) -> None:
        """delta_seconds=0 should pass validation (ge=0)."""
        client, token, mock_analytics = client_with_analytics
        response = client.post(
            "/api/playback/heartbeat",
            json={
                "job_id": "test-job",
                "language": "en",
                "track_kind": "original",
                "delta_seconds": 0,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
