from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_pipeline_service,
    get_request_user,
)


pytestmark = pytest.mark.webapi


class _RestartValueErrorPipelineService:
    def restart_job(self, job_id: str, *, user_id=None, user_role=None):
        raise ValueError("Restart is not supported for job type 'youtube_dub'")


def test_restart_job_action_value_error_returns_client_error() -> None:
    app = create_app()
    app.dependency_overrides[get_pipeline_service] = lambda: _RestartValueErrorPipelineService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/api/pipelines/jobs/job-1/restart")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Restart is not supported for job type 'youtube_dub'"
    }
