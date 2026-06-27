from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services.export_service import ExportResult, ExportServiceError
from modules.webapi.application import create_app
from modules.webapi.routers import exports
from modules.webapi.dependencies import (
    RequestUserContext,
    get_export_service,
    get_request_user,
)

pytestmark = pytest.mark.webapi


class _StubExportService:
    def __init__(self, zip_path: Path) -> None:
        self.zip_path = zip_path
        self.create_calls: list[dict[str, str | None]] = []
        self.download_calls: list[str] = []

    def create_export(
        self,
        *,
        source_kind: str,
        source_id: str,
        player_type: str,
        user_id: str | None,
        user_role: str | None,
    ) -> ExportResult:
        self.create_calls.append(
            {
                "source_kind": source_kind,
                "source_id": source_id,
                "player_type": player_type,
                "user_id": user_id,
                "user_role": user_role,
            }
        )
        return ExportResult(
            export_id="secret-export-id",
            zip_path=self.zip_path,
            download_name="Secret Export.zip",
            created_at="2026-06-24T12:00:00+00:00",
        )

    def resolve_export_download(self, export_id: str) -> ExportResult:
        self.download_calls.append(export_id)
        return ExportResult(
            export_id=export_id,
            zip_path=self.zip_path,
            download_name="Secret Export.zip",
            created_at="2026-06-24T12:00:00+00:00",
        )


def _has_export_metric_count(metrics_text: str, *, operation: str, result: str) -> bool:
    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_text)
    }
    metric = families.get("ebook_tools_export_route_duration_seconds")
    if metric is None:
        return False
    return any(
        sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )


def test_export_routes_record_token_safe_timing(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    zip_path = tmp_path / "secret-export-id.zip"
    zip_path.write_bytes(b"zip")
    service = _StubExportService(zip_path)
    app = create_app()
    app.dependency_overrides[get_export_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="secret-user-id",
        user_role="editor",
    )
    caplog.set_level(logging.DEBUG, logger="modules.webapi.routers.exports")

    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/exports",
                json={
                    "source_kind": "job",
                    "source_id": "secret-job-id",
                    "player_type": "interactive-text",
                },
            )
            download_response = client.get("/api/exports/secret-export-id/download")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert create_response.json()["download_url"] == "/api/exports/secret-export-id/download"
    assert download_response.status_code == 200
    assert download_response.content == b"zip"
    assert service.create_calls == [
        {
            "source_kind": "job",
            "source_id": "secret-job-id",
            "player_type": "interactive-text",
            "user_id": "secret-user-id",
            "user_role": "editor",
        }
    ]
    assert service.download_calls == ["secret-export-id"]

    rendered_logs = caplog.text
    assert "Offline export route operation=create result=success source_kind=job player_type=interactive-text" in rendered_logs
    assert "Offline export route operation=download result=success source_kind=unknown player_type=unknown" in rendered_logs
    assert "secret-job-id" not in rendered_logs
    assert "secret-export-id" not in rendered_logs
    assert "secret-user-id" not in rendered_logs
    assert "Secret Export.zip" not in rendered_logs
    assert str(zip_path) not in rendered_logs

    assert _has_export_metric_count(metrics_response.text, operation="create", result="success")
    assert _has_export_metric_count(metrics_response.text, operation="download", result="success")


@pytest.mark.parametrize(
    ("raised", "expected_status", "expected_detail", "expected_result"),
    [
        (
            KeyError("secret-job-id missing from /Volumes/Data/private/jobs.json"),
            404,
            exports.EXPORT_SOURCE_NOT_FOUND_MESSAGE,
            "not_found",
        ),
        (
            PermissionError("secret-user-id cannot export /Volumes/Data/private/job"),
            403,
            exports.EXPORT_FORBIDDEN_MESSAGE,
            "forbidden",
        ),
        (
            ExportServiceError(
                "Missing metadata manifest at "
                "/Volumes/Data/storage/secret-job-id/metadata/job.json"
            ),
            400,
            exports.EXPORT_CREATE_FAILED_MESSAGE,
            "bad_request",
        ),
    ],
)
def test_export_create_errors_use_token_safe_details(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    raised: Exception,
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    zip_path = tmp_path / "secret-export-id.zip"
    service = _StubExportService(zip_path)

    def fail_create_export(**kwargs) -> ExportResult:
        service.create_calls.append(kwargs)
        raise raised

    service.create_export = fail_create_export
    app = create_app()
    app.dependency_overrides[get_export_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="secret-user-id",
        user_role="editor",
    )
    caplog.set_level(logging.DEBUG, logger="modules.webapi.routers.exports")

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/exports",
                json={
                    "source_kind": "job",
                    "source_id": "secret-job-id",
                    "player_type": "interactive-text",
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json()["detail"] == expected_detail
    assert "secret-job-id" not in response.text
    assert "secret-user-id" not in response.text
    assert "/Volumes/Data" not in response.text

    rendered_logs = caplog.text
    assert f"Offline export route operation=create result={expected_result}" in rendered_logs
    assert "secret-job-id" not in rendered_logs
    assert "secret-user-id" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs
    assert _has_export_metric_count(
        metrics_response.text,
        operation="create",
        result=expected_result,
    )


def test_export_create_response_validation_failure_uses_token_safe_detail(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    zip_path = tmp_path / "secret-export-id.zip"
    service = _StubExportService(zip_path)

    def malformed_create_export(**kwargs) -> ExportResult:
        service.create_calls.append(kwargs)
        return ExportResult(
            export_id={"secret": "secret-export-id"},  # type: ignore[arg-type]
            zip_path=zip_path,
            download_name="Secret Export.zip",
            created_at="2026-06-24T12:00:00+00:00",
        )

    service.create_export = malformed_create_export
    app = create_app()
    app.dependency_overrides[get_export_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="secret-user-id",
        user_role="editor",
    )
    caplog.set_level(logging.DEBUG, logger="modules.webapi.routers.exports")

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/exports",
                json={
                    "source_kind": "job",
                    "source_id": "secret-job-id",
                    "player_type": "interactive-text",
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == exports.EXPORT_CREATE_FAILED_MESSAGE
    assert "secret-export-id" not in response.text
    assert "secret-job-id" not in response.text
    assert "Secret Export.zip" not in response.text

    rendered_logs = caplog.text
    assert "Offline export route operation=create result=error" in rendered_logs
    assert "operation=create result=success" not in rendered_logs
    assert "secret-export-id" not in rendered_logs
    assert "secret-job-id" not in rendered_logs
    assert "secret-user-id" not in rendered_logs
    assert "Secret Export.zip" not in rendered_logs
    assert str(zip_path) not in rendered_logs
    assert _has_export_metric_count(metrics_response.text, operation="create", result="error")


def test_export_download_not_found_stays_token_safe(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    zip_path = tmp_path / "missing-secret-export.zip"
    service = _StubExportService(zip_path)
    app = create_app()
    app.dependency_overrides[get_export_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="secret-user-id",
        user_role="editor",
    )
    caplog.set_level(logging.DEBUG, logger="modules.webapi.routers.exports")

    def raise_missing(export_id: str) -> ExportResult:
        service.download_calls.append(export_id)
        raise ExportServiceError(
            "Export metadata is corrupted at "
            "/Volumes/Data/storage/exports/secret-missing-export-id.json"
        )

    service.resolve_export_download = raise_missing

    try:
        with TestClient(app) as client:
            response = client.get("/api/exports/secret-missing-export-id/download")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == exports.EXPORT_DOWNLOAD_UNAVAILABLE_MESSAGE
    assert service.download_calls == ["secret-missing-export-id"]
    assert "secret-missing-export-id" not in response.text
    assert "/Volumes/Data" not in response.text

    rendered_logs = caplog.text
    assert "Offline export route operation=download result=not_found" in rendered_logs
    assert "secret-missing-export-id" not in rendered_logs
    assert "secret-user-id" not in rendered_logs
    assert str(zip_path) not in rendered_logs

    assert _has_export_metric_count(metrics_response.text, operation="download", result="not_found")


def test_export_download_unexpected_failure_stays_token_safe(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    zip_path = tmp_path / "secret-export-id.zip"
    service = _StubExportService(zip_path)
    app = create_app()
    app.dependency_overrides[get_export_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="secret-user-id",
        user_role="editor",
    )
    caplog.set_level(logging.DEBUG, logger="modules.webapi.routers.exports")

    def fail_download(export_id: str) -> ExportResult:
        service.download_calls.append(export_id)
        raise RuntimeError(
            "zip resolver failed for secret-export-id at "
            "/Volumes/Data/storage/exports/secret-export-id.zip"
        )

    service.resolve_export_download = fail_download

    try:
        with TestClient(app) as client:
            response = client.get("/api/exports/secret-export-id/download")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == exports.EXPORT_DOWNLOAD_UNAVAILABLE_MESSAGE
    assert "secret-export-id" not in response.text
    assert "/Volumes/Data" not in response.text
    assert service.download_calls == ["secret-export-id"]

    rendered_logs = caplog.text
    assert "Offline export route operation=download result=error" in rendered_logs
    assert "operation=download result=success" not in rendered_logs
    assert "secret-export-id" not in rendered_logs
    assert "secret-user-id" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs
    assert str(zip_path) not in rendered_logs
    assert _has_export_metric_count(metrics_response.text, operation="download", result="error")
