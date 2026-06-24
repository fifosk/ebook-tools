from __future__ import annotations

from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services.creation_template_service import CreationTemplateService
from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_creation_template_service,
    get_request_user,
)
from modules.webapi.routers import creation_templates as creation_template_router


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def error(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)


def _has_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_creation_template_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


def test_creation_templates_round_trip_and_strip_secret_payload_keys(tmp_path) -> None:
    app = create_app()
    service = CreationTemplateService(
        file_locator=FileLocator(storage_dir=tmp_path),
    )
    app.dependency_overrides[get_creation_template_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice@example.test",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            first = client.post(
                "/api/creation/templates",
                json={
                    "id": "dan-brown-continuation",
                    "name": "Dan Brown continuation",
                    "mode": "generatedBook",
                    "payload": {
                        "topic": "Dan Brown continuation",
                        "book_title": "The next chapter",
                        "authToken": "do-not-store",
                        "nested": {
                            "api_key": "do-not-store",
                            "language": "Slovak",
                        },
                        "profiles": [
                            {
                                "voice": "alloy",
                                "credential": "do-not-store",
                                "privateKey": "do-not-store",
                            },
                            {
                                "target_language": "fr",
                                "cookies": "do-not-store",
                                "csrfHeader": "do-not-store",
                            },
                        ],
                    },
                },
            )
            second = client.post(
                "/api/creation/templates",
                json={
                    "id": "subtitle-defaults",
                    "name": "Subtitle defaults",
                    "mode": "subtitleJob",
                    "payload": {"source_path": "/nas/demo.srt"},
                },
            )
            listed = client.get("/api/creation/templates")
            filtered = client.get(
                "/api/creation/templates",
                params={"mode": "generated_book"},
            )
            deleted = client.delete("/api/creation/templates/subtitle-defaults")
            listed_after_delete = client.get("/api/creation/templates")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["mode"] == "generated_book"
    assert first.json()["payload"] == {
        "topic": "Dan Brown continuation",
        "book_title": "The next chapter",
        "nested": {"language": "Slovak"},
        "profiles": [
            {"voice": "alloy"},
            {"target_language": "fr"},
        ],
    }
    assert "do-not-store" not in first.text

    assert second.status_code == 200
    assert second.json()["mode"] == "subtitle_job"
    assert listed.status_code == 200
    assert [entry["id"] for entry in listed.json()["templates"]] == [
        "subtitle-defaults",
        "dan-brown-continuation",
    ]
    assert filtered.status_code == 200
    assert [entry["id"] for entry in filtered.json()["templates"]] == [
        "dan-brown-continuation"
    ]
    assert deleted.json() == {"deleted": True, "template_id": "subtitle-defaults"}
    assert [entry["id"] for entry in listed_after_delete.json()["templates"]] == [
        "dan-brown-continuation"
    ]


def test_creation_templates_require_authenticated_user() -> None:
    app = create_app()
    app.dependency_overrides[get_creation_template_service] = lambda: CreationTemplateService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role="anonymous",
    )

    try:
        with TestClient(app) as client:
            list_response = client.get("/api/creation/templates")
            save_response = client.post(
                "/api/creation/templates",
                json={"name": "Template", "mode": "generated_book", "payload": {}},
            )
            delete_response = client.delete("/api/creation/templates/template")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 401
    assert save_response.status_code == 401
    assert delete_response.status_code == 401


def test_creation_templates_record_token_safe_route_telemetry(tmp_path, monkeypatch) -> None:
    app = create_app()
    service = CreationTemplateService(
        file_locator=FileLocator(storage_dir=tmp_path),
    )
    logger = _ListLogger()
    app.dependency_overrides[get_creation_template_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="template-user@example.test",
        user_role="editor",
    )
    monkeypatch.setattr(creation_template_router, "logger", logger)

    try:
        with TestClient(app) as client:
            saved = client.post(
                "/api/creation/templates",
                json={
                    "id": "secret-template-id",
                    "name": "Secret Dan Brown template",
                    "mode": "subtitleJob",
                    "payload": {
                        "source_path": "/nas/secret/demo.srt",
                        "authToken": "do-not-store",
                    },
                },
            )
            listed = client.get(
                "/api/creation/templates",
                params={"mode": "subtitle_job"},
            )
            deleted = client.delete("/api/creation/templates/secret-template-id")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert listed.status_code == 200
    assert deleted.status_code == 200

    rendered_logs = "\n".join(logger.messages)
    assert "Creation template route operation=save result=success" in rendered_logs
    assert "Creation template route operation=list result=success" in rendered_logs
    assert "templates=1" in rendered_logs
    assert "Creation template route operation=delete result=success" in rendered_logs
    assert "deleted=true" in rendered_logs
    assert "template-user@example.test" not in rendered_logs
    assert "secret-template-id" not in rendered_logs
    assert "Secret Dan Brown template" not in rendered_logs
    assert "subtitle_job" not in rendered_logs
    assert "/nas/secret/demo.srt" not in rendered_logs
    assert "do-not-store" not in rendered_logs

    assert _has_metric_count(metrics_response.text, operation="save", result="success")
    assert _has_metric_count(metrics_response.text, operation="list", result="success")
    assert _has_metric_count(metrics_response.text, operation="delete", result="success")


def test_creation_templates_record_unauthorized_telemetry(monkeypatch) -> None:
    app = create_app()
    logger = _ListLogger()
    app.dependency_overrides[get_creation_template_service] = lambda: CreationTemplateService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role="anonymous",
    )
    monkeypatch.setattr(creation_template_router, "logger", logger)

    try:
        with TestClient(app) as client:
            list_response = client.get("/api/creation/templates")
            save_response = client.post(
                "/api/creation/templates",
                json={"name": "Template", "mode": "generated_book", "payload": {}},
            )
            delete_response = client.delete("/api/creation/templates/private-template")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 401
    assert save_response.status_code == 401
    assert delete_response.status_code == 401
    rendered_logs = "\n".join(logger.messages)
    assert "operation=list result=unauthorized" in rendered_logs
    assert "operation=save result=unauthorized" in rendered_logs
    assert "operation=delete result=unauthorized" in rendered_logs
    assert "anonymous" not in rendered_logs
    assert "private-template" not in rendered_logs
    assert "Template" not in rendered_logs
    assert _has_metric_count(metrics_response.text, operation="list", result="unauthorized")
    assert _has_metric_count(metrics_response.text, operation="save", result="unauthorized")
    assert _has_metric_count(metrics_response.text, operation="delete", result="unauthorized")
