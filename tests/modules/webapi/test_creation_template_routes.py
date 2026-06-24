from __future__ import annotations

from fastapi.testclient import TestClient

from modules.services.creation_template_service import CreationTemplateService
from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_creation_template_service,
    get_request_user,
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
