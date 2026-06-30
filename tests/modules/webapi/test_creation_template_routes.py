from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services import creation_template_service
from modules.services.creation_template_service import CreationTemplateEntry, CreationTemplateService
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


class _StubCreationTemplateService:
    def __init__(
        self,
        *,
        fail_operation: str | None = None,
        invalid_entry: bool = False,
        invalid_delete: bool = False,
    ) -> None:
        self.fail_operation = fail_operation
        self.invalid_entry = invalid_entry
        self.invalid_delete = invalid_delete
        self.entry = CreationTemplateEntry(
            id="secret-template-id",
            name="Secret Dan Brown template",
            mode="secret-mode" if invalid_entry else "generated_book",
            created_at=1_800_000_000.0,
            updated_at=1_800_000_100.0,
            payload={"source_path": "/Volumes/Data/private/book.epub"},
        )

    @staticmethod
    def canonical_template_id(template_id: str) -> str:
        return CreationTemplateService.canonical_template_id(template_id)

    def _maybe_fail(self, operation: str) -> None:
        if self.fail_operation == operation:
            raise RuntimeError(
                "creation template storage failed for secret-template-id and "
                "alice@example.test at /Volumes/Data/private/creation_templates/alice.json"
            )

    def list_templates(self, user_id: str, *, mode=None):  # noqa: ANN001
        self._maybe_fail("list")
        return [self.entry]

    def save_template(self, user_id: str, entry: dict[str, object]) -> CreationTemplateEntry:
        self._maybe_fail("save")
        return self.entry

    def get_template(self, user_id: str, template_id: str) -> CreationTemplateEntry | None:
        self._maybe_fail("get")
        return self.entry

    def delete_template(self, user_id: str, template_id: str) -> bool:
        self._maybe_fail("delete")
        if self.invalid_delete:
            return object()  # type: ignore[return-value]
        return True


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
                        "acquisition_provider": " OpenLibrary ",
                        "source_kind": " LOCAL_EPUB ",
                        "acquisition_candidate_id": "OpenLibrary:/works/OL45883W",
                        "source_url": "HTTPS://Example.test/Book.EPUB",
                        "authToken": "do-not-store",
                        "nested": {
                            "api_key": "do-not-store",
                            "language": "Slovak",
                            "discovery_state": {
                                "provider": "indexer",
                                "review_url": (
                                    "https://user:secret-indexer-key@indexer.example.invalid"
                                    "/download/7?title=Demo&apikey=secret-indexer-key"
                                    "#name=Demo&access_token=secret-indexer-key"
                                ),
                            },
                            "media_metadata_lookup": {
                                "provider": " OpenLibrary ",
                                "candidate_id": "OpenLibrary:/works/OL45883W",
                            },
                        },
                        "profiles": [
                            {
                                "voice": "alloy",
                                "selected_provider": " Manual_Downloads ",
                                "selected_path": "/Volumes/Data/Download/DStation/MixedCase",
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
            fetched = client.get("/api/creation/templates/dan-brown-continuation")
            missing = client.get("/api/creation/templates/missing-template")
            deleted = client.delete("/api/creation/templates/subtitle-defaults")
            listed_after_delete = client.get("/api/creation/templates")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["mode"] == "generated_book"
    assert first.json()["payload"] == {
        "topic": "Dan Brown continuation",
        "book_title": "The next chapter",
        "acquisition_provider": "openlibrary",
        "source_kind": "local_epub",
        "acquisition_candidate_id": "OpenLibrary:/works/OL45883W",
        "source_url": "HTTPS://Example.test/Book.EPUB",
        "nested": {
            "language": "Slovak",
            "discovery_state": {
                "provider": "indexer",
                "review_url": "https://indexer.example.invalid/download/7?title=Demo#name=Demo",
            },
            "media_metadata_lookup": {
                "provider": "openlibrary",
                "candidate_id": "OpenLibrary:/works/OL45883W",
            },
        },
        "profiles": [
            {
                "voice": "alloy",
                "selected_provider": "manual_downloads",
                "selected_path": "/Volumes/Data/Download/DStation/MixedCase",
            },
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
    assert fetched.status_code == 200
    assert fetched.json()["id"] == "dan-brown-continuation"
    assert fetched.json()["payload"] == first.json()["payload"]
    assert "do-not-store" not in fetched.text
    assert missing.status_code == 404
    assert deleted.json() == {"deleted": True, "template_id": "subtitle-defaults"}
    assert [entry["id"] for entry in listed_after_delete.json()["templates"]] == [
        "dan-brown-continuation"
    ]


def test_creation_templates_unknown_mode_filter_returns_empty_without_storage_read() -> None:
    class RaisingService(CreationTemplateService):
        def _load_entries(self, user_id: str):  # type: ignore[override]
            raise AssertionError("invalid mode filters should skip template storage reads")

    service = RaisingService()

    assert service.list_templates("alice@example.test", mode="unsupported-mode") == []


def test_creation_templates_unknown_mode_route_skips_service_storage() -> None:
    class RaisingService:
        def list_templates(self, user_id: str, *, mode=None):  # noqa: ANN001
            raise AssertionError("invalid route mode filters should skip template storage reads")

    app = create_app()
    app.dependency_overrides[get_creation_template_service] = lambda: RaisingService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice@example.test",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/creation/templates",
                params={"mode": " unsupported-mode "},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"templates": []}


def test_creation_templates_unknown_mode_filter_does_not_fall_back_to_generated(tmp_path) -> None:
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
            saved = client.post(
                "/api/creation/templates",
                json={
                    "id": "generated-template",
                    "name": "Generated template",
                    "mode": "generatedBook",
                    "payload": {"topic": "Mystery"},
                },
            )
            unknown_mode = client.get(
                "/api/creation/templates",
                params={"mode": "unsupported-mode"},
            )
            alias_mode = client.get(
                "/api/creation/templates",
                params={"mode": "generatedBook"},
            )
            blank_mode = client.get(
                "/api/creation/templates",
                params={"mode": "   "},
            )
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert unknown_mode.status_code == 200
    assert unknown_mode.json() == {"templates": []}
    assert alias_mode.status_code == 200
    assert [entry["id"] for entry in alias_mode.json()["templates"]] == [
        "generated-template"
    ]
    assert blank_mode.status_code == 200
    assert [entry["id"] for entry in blank_mode.json()["templates"]] == [
        "generated-template"
    ]


def test_creation_template_get_is_user_scoped_and_sanitizes_template_id(tmp_path) -> None:
    app = create_app()
    service = CreationTemplateService(
        file_locator=FileLocator(storage_dir=tmp_path),
    )
    current_user = {"user_id": "alice@example.test"}
    app.dependency_overrides[get_creation_template_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=current_user["user_id"],
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            saved = client.post(
                "/api/creation/templates",
                json={
                    "id": "draft/template?secret",
                    "name": "Reusable draft",
                    "mode": "narrate_ebook",
                    "payload": {
                        "form_state": {
                            "input_file": "/nas/book.epub",
                            "authToken": "do-not-store",
                        },
                    },
                },
            )
            fetched = client.get("/api/creation/templates/draft_template_secret")
            current_user["user_id"] = "bob@example.test"
            other_user = client.get("/api/creation/templates/draft_template_secret")
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert saved.json()["id"] == "draft_template_secret"
    assert fetched.status_code == 200
    assert fetched.json()["id"] == "draft_template_secret"
    assert fetched.json()["mode"] == "narrate_ebook"
    assert fetched.json()["payload"] == {
        "form_state": {
            "input_file": "/nas/book.epub",
        },
    }
    assert "do-not-store" not in fetched.text
    assert other_user.status_code == 404


def test_creation_template_get_normalizes_only_matching_entry(tmp_path) -> None:
    sanitized_payloads: list[object] = []

    class CountingService(CreationTemplateService):
        @classmethod
        def _sanitize_payload(cls, value):  # type: ignore[override]  # noqa: ANN001
            sanitized_payloads.append(value)
            return super()._sanitize_payload(value)

    service = CountingService(file_locator=FileLocator(storage_dir=tmp_path))
    user_id = "alice@example.test"
    storage_path = service._user_path(user_id)  # noqa: SLF001 - pins storage scan behavior.
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(
        """
        {
          "version": 1,
          "user_id": "alice@example.test",
          "templates": [
            {
              "id": "unrelated-template",
              "name": "Private unrelated template",
              "mode": "generated_book",
              "created_at": 1,
              "updated_at": 2,
              "payload": {"authToken": "do-not-touch", "source_path": "/secret/book.epub"}
            },
            {
              "id": "draft/template?secret",
              "name": "Reusable draft",
              "mode": "narrate_ebook",
              "created_at": 3,
              "updated_at": 4,
              "payload": {"form_state": {"input_file": "/nas/book.epub"}}
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    entry = service.get_template(user_id, "draft_template_secret")

    assert entry is not None
    assert entry.id == "draft_template_secret"
    assert entry.payload == {"form_state": {"input_file": "/nas/book.epub"}}
    assert sanitized_payloads == [
        {"form_state": {"input_file": "/nas/book.epub"}}
    ]


def test_creation_template_delete_returns_canonical_template_id(tmp_path) -> None:
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
            saved = client.post(
                "/api/creation/templates",
                json={
                    "id": "draft template?secret",
                    "name": "Reusable draft",
                    "mode": "narrate_ebook",
                    "payload": {
                        "form_state": {
                            "input_file": "/nas/book.epub",
                        },
                    },
                },
            )
            deleted = client.delete("/api/creation/templates/draft%20template%3Fsecret")
            listed = client.get("/api/creation/templates")
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert saved.json()["id"] == "draft_template_secret"
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "template_id": "draft_template_secret"}
    assert listed.json() == {"templates": []}


def test_creation_template_delete_skips_storage_for_empty_canonical_id() -> None:
    class RaisingService(CreationTemplateService):
        def _load_entries(self, user_id: str):  # type: ignore[override]
            raise AssertionError("empty canonical template ids should not read storage")

    service = RaisingService()

    assert service.delete_template("alice@example.test", "...") is False


def test_creation_template_get_route_skips_service_for_empty_canonical_id() -> None:
    class RaisingService(CreationTemplateService):
        def get_template(self, user_id: str, template_id: str):  # type: ignore[override]
            raise AssertionError("empty canonical template ids should not call get_template")

    app = create_app()
    app.dependency_overrides[get_creation_template_service] = lambda: RaisingService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice@example.test",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/creation/templates/...")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_creation_template_delete_route_skips_service_for_empty_canonical_id() -> None:
    class RaisingService(CreationTemplateService):
        def delete_template(self, user_id: str, template_id: str):  # type: ignore[override]
            raise AssertionError("empty canonical template ids should not call delete_template")

    app = create_app()
    app.dependency_overrides[get_creation_template_service] = lambda: RaisingService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice@example.test",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.delete("/api/creation/templates/...")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"deleted": False, "template_id": ""}


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
            get_response = client.get("/api/creation/templates/template")
            delete_response = client.delete("/api/creation/templates/template")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 401
    assert save_response.status_code == 401
    assert get_response.status_code == 401
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
            fetched = client.get("/api/creation/templates/secret-template-id")
            missing = client.get("/api/creation/templates/missing-secret-template")
            deleted = client.delete("/api/creation/templates/secret-template-id")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    assert listed.status_code == 200
    assert fetched.status_code == 200
    assert missing.status_code == 404
    assert deleted.status_code == 200

    rendered_logs = "\n".join(logger.messages)
    assert "Creation template route operation=save result=success" in rendered_logs
    assert "Creation template route operation=list result=success" in rendered_logs
    assert "templates=1" in rendered_logs
    assert "Creation template route operation=get result=success" in rendered_logs
    assert "Creation template route operation=get result=not_found" in rendered_logs
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
    assert _has_metric_count(metrics_response.text, operation="get", result="success")
    assert _has_metric_count(metrics_response.text, operation="get", result="not_found")
    assert _has_metric_count(metrics_response.text, operation="delete", result="success")


@pytest.mark.parametrize(
    ("method", "path", "operation", "service"),
    [
        (
            "get",
            "/api/creation/templates",
            "list",
            _StubCreationTemplateService(invalid_entry=True),
        ),
        (
            "post",
            "/api/creation/templates",
            "save",
            _StubCreationTemplateService(invalid_entry=True),
        ),
        (
            "get",
            "/api/creation/templates/secret-template-id",
            "get",
            _StubCreationTemplateService(invalid_entry=True),
        ),
        (
            "delete",
            "/api/creation/templates/secret-template-id",
            "delete",
            _StubCreationTemplateService(invalid_delete=True),
        ),
    ],
)
def test_creation_template_response_validation_errors_use_token_safe_response(
    monkeypatch,
    method: str,
    path: str,
    operation: str,
    service: _StubCreationTemplateService,
) -> None:
    app = create_app()
    logger = _ListLogger()
    app.dependency_overrides[get_creation_template_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice@example.test",
        user_role="editor",
    )
    monkeypatch.setattr(creation_template_router, "logger", logger)

    try:
        with TestClient(app) as client:
            if method == "post":
                response = client.post(
                    path,
                    json={
                        "id": "secret-template-id",
                        "name": "Secret Dan Brown template",
                        "mode": "generated_book",
                        "payload": {"source_path": "/Volumes/Data/private/book.epub"},
                    },
                )
            else:
                response = getattr(client, method)(path)
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": creation_template_router.CREATION_TEMPLATE_UNAVAILABLE_MESSAGE
    }
    rendered = response.text
    assert "secret-mode" not in rendered
    assert "secret-template-id" not in rendered
    assert "Secret Dan Brown template" not in rendered
    assert "alice@example.test" not in rendered
    assert "/Volumes/Data" not in rendered
    assert _has_metric_count(metrics_response.text, operation=operation, result="error")
    rendered_logs = "\n".join(logger.messages)
    assert f"Creation template route operation={operation} result=error" in rendered_logs
    assert f"Creation template route operation={operation} result=success" not in rendered_logs
    assert "secret-mode" not in rendered_logs
    assert "secret-template-id" not in rendered_logs
    assert "Secret Dan Brown template" not in rendered_logs
    assert "alice@example.test" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs


@pytest.mark.parametrize(
    ("method", "path", "operation", "service"),
    [
        (
            "get",
            "/api/creation/templates",
            "list",
            _StubCreationTemplateService(fail_operation="list"),
        ),
        (
            "post",
            "/api/creation/templates",
            "save",
            _StubCreationTemplateService(fail_operation="save"),
        ),
        (
            "get",
            "/api/creation/templates/secret-template-id",
            "get",
            _StubCreationTemplateService(fail_operation="get"),
        ),
        (
            "delete",
            "/api/creation/templates/secret-template-id",
            "delete",
            _StubCreationTemplateService(fail_operation="delete"),
        ),
    ],
)
def test_creation_template_storage_errors_use_token_safe_response(
    monkeypatch,
    method: str,
    path: str,
    operation: str,
    service: _StubCreationTemplateService,
) -> None:
    app = create_app()
    logger = _ListLogger()
    app.dependency_overrides[get_creation_template_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice@example.test",
        user_role="editor",
    )
    monkeypatch.setattr(creation_template_router, "logger", logger)

    try:
        with TestClient(app) as client:
            if method == "post":
                response = client.post(
                    path,
                    json={
                        "id": "secret-template-id",
                        "name": "Secret Dan Brown template",
                        "mode": "generated_book",
                        "payload": {"source_path": "/Volumes/Data/private/book.epub"},
                    },
                )
            else:
                response = getattr(client, method)(path)
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": creation_template_router.CREATION_TEMPLATE_UNAVAILABLE_MESSAGE
    }
    rendered = response.text
    assert "secret-template-id" not in rendered
    assert "Secret Dan Brown template" not in rendered
    assert "alice@example.test" not in rendered
    assert "/Volumes/Data" not in rendered
    assert _has_metric_count(metrics_response.text, operation=operation, result="error")
    rendered_logs = "\n".join(logger.messages)
    assert f"Creation template route operation={operation} result=error" in rendered_logs
    assert "secret-template-id" not in rendered_logs
    assert "Secret Dan Brown template" not in rendered_logs
    assert "alice@example.test" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs


def test_creation_templates_corrupt_storage_logs_token_safe_recovery(
    tmp_path,
    monkeypatch,
) -> None:
    app = create_app()
    service = CreationTemplateService(
        file_locator=FileLocator(storage_dir=tmp_path),
    )
    logger = _ListLogger()
    user_id = "alice.secret@example.test"
    storage_path = service._user_path(user_id)  # noqa: SLF001 - pins storage recovery behavior.
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{not-json: /nas/private/book.epub", encoding="utf-8")
    app.dependency_overrides[get_creation_template_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=user_id,
        user_role="editor",
    )
    monkeypatch.setattr(creation_template_service, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get("/api/creation/templates")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"templates": []}
    rendered_logs = "\n".join(logger.messages)
    assert "Creation templates storage could not be loaded" in rendered_logs
    assert "alice.secret@example.test" not in rendered_logs
    assert "alice_secret_example_test" not in rendered_logs
    assert str(storage_path) not in rendered_logs
    assert "creation_templates" not in rendered_logs
    assert "/nas/private/book.epub" not in rendered_logs
    assert "not-json" not in rendered_logs


@pytest.mark.parametrize(
    "stored_payload",
    [
        '["secret-template-id", "/nas/private/book.epub"]',
        '{"templates": "secret-template-payload"}',
    ],
)
def test_creation_templates_structurally_corrupt_storage_logs_token_safe_recovery(
    tmp_path,
    monkeypatch,
    stored_payload: str,
) -> None:
    app = create_app()
    service = CreationTemplateService(
        file_locator=FileLocator(storage_dir=tmp_path),
    )
    logger = _ListLogger()
    user_id = "alice.secret@example.test"
    storage_path = service._user_path(user_id)  # noqa: SLF001 - pins storage recovery behavior.
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(stored_payload, encoding="utf-8")
    app.dependency_overrides[get_creation_template_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=user_id,
        user_role="editor",
    )
    monkeypatch.setattr(creation_template_service, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get("/api/creation/templates")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"templates": []}
    rendered_logs = "\n".join(logger.messages)
    assert "Creation templates storage could not be loaded" in rendered_logs
    assert "alice.secret@example.test" not in rendered_logs
    assert "alice_secret_example_test" not in rendered_logs
    assert "secret-template-id" not in rendered_logs
    assert str(storage_path) not in rendered_logs
    assert "creation_templates" not in rendered_logs
    assert "/nas/private/book.epub" not in rendered_logs
    assert "secret-template-payload" not in rendered_logs


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
            get_response = client.get("/api/creation/templates/private-template")
            delete_response = client.delete("/api/creation/templates/private-template")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 401
    assert save_response.status_code == 401
    assert get_response.status_code == 401
    assert delete_response.status_code == 401
    rendered_logs = "\n".join(logger.messages)
    assert "operation=list result=unauthorized" in rendered_logs
    assert "operation=save result=unauthorized" in rendered_logs
    assert "operation=get result=unauthorized" in rendered_logs
    assert "operation=delete result=unauthorized" in rendered_logs
    assert "anonymous" not in rendered_logs
    assert "private-template" not in rendered_logs
    assert "Template" not in rendered_logs
    assert _has_metric_count(metrics_response.text, operation="list", result="unauthorized")
    assert _has_metric_count(metrics_response.text, operation="save", result="unauthorized")
    assert _has_metric_count(metrics_response.text, operation="get", result="unauthorized")
    assert _has_metric_count(metrics_response.text, operation="delete", result="unauthorized")
