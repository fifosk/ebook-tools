from modules.webapi.routes import router, storage_router

import pytest

pytestmark = pytest.mark.webapi


def test_pipeline_router_includes_expected_paths() -> None:
    paths = {route.path for route in router.routes if getattr(route, "methods", None)}

    assert "/jobs" in paths
    assert "/files" in paths
    assert "/defaults" in paths
    assert "/search" in paths
    assert "/jobs/{job_id}/media" in paths
    assert "/{job_id}/events" in paths


def test_storage_router_includes_expected_paths() -> None:
    paths = {route.path for route in storage_router.routes if getattr(route, "methods", None)}

    assert "/jobs/{job_id}/files/{filename:path}" in paths
    assert "/jobs/{job_id}/{filename:path}" in paths
    assert "/covers/{filename:path}" in paths
