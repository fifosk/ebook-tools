from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services.file_locator import FileLocator
from modules.services.resume_service import ResumeEntry, ResumeService
from modules.webapi.application import create_app
from modules.webapi.dependencies import RequestUserContext, get_request_user, get_resume_service
from modules.webapi.routers import resume as resume_router

pytestmark = pytest.mark.webapi


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


class _StubResumeService:
    def __init__(
        self,
        *,
        invalid_entry: bool = False,
        invalid_delete: bool = False,
    ) -> None:
        self.list_calls: list[dict[str, object]] = []
        self.get_calls: list[dict[str, str]] = []
        self.save_calls: list[dict[str, object]] = []
        self.clear_calls: list[dict[str, str]] = []
        self.invalid_entry = invalid_entry
        self.invalid_delete = invalid_delete
        self.entries = [
            ResumeEntry(
                job_id="job-1",
                kind="secret-kind" if invalid_entry else "time",
                updated_at=1_800_000_000.0,
                position=120.0,
                sentence=None,
                chunk_id=None,
                media_type="audio",
                base_id="chunk-1",
            ),
            ResumeEntry(
                job_id="job-2",
                kind="sentence",
                updated_at=1_800_000_100.0,
                position=None,
                sentence=42,
                chunk_id="chunk-2",
                media_type="text",
                base_id=None,
            ),
        ]

    def list(self, user_id: str, *, job_ids=None, limit: int = 200):
        self.list_calls.append({"user_id": user_id, "job_ids": list(job_ids or []), "limit": limit})
        if job_ids:
            allowed = set(job_ids)
            return [entry for entry in self.entries if entry.job_id in allowed]
        return list(self.entries)

    def get(self, job_id: str, user_id: str):
        self.get_calls.append({"job_id": job_id, "user_id": user_id})
        for entry in self.entries:
            if entry.job_id == job_id:
                return entry
        return None

    def save(self, job_id: str, user_id: str, data: dict[str, object]):
        self.save_calls.append({"job_id": job_id, "user_id": user_id, "data": data})
        return ResumeEntry(
            job_id=job_id,
            kind="secret-kind" if self.invalid_entry else str(data.get("kind") or "time"),
            updated_at=1_800_000_200.0,
            position=data.get("position") if isinstance(data.get("position"), float) else None,
            sentence=data.get("sentence") if isinstance(data.get("sentence"), int) else None,
            chunk_id=data.get("chunk_id") if isinstance(data.get("chunk_id"), str) else None,
            media_type=data.get("media_type") if isinstance(data.get("media_type"), str) else None,
            base_id=data.get("base_id") if isinstance(data.get("base_id"), str) else None,
        )

    def clear(self, job_id: str, user_id: str) -> bool:
        self.clear_calls.append({"job_id": job_id, "user_id": user_id})
        if self.invalid_delete:
            return object()  # type: ignore[return-value]
        return job_id == "job-1"


def _has_resume_metric_count(
    metrics_text: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {family.name: family for family in text_string_to_metric_families(metrics_text)}
    metric = families["ebook_tools_resume_route_duration_seconds"]
    return any(
        sample.name.endswith("_count")
        and sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.value >= 1
        for sample in metric.samples
    )


def test_resume_routes_scope_calls_and_record_token_safe_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    service = _StubResumeService()
    capture_logger = _ListLogger()
    monkeypatch.setattr(resume_router, "logger", capture_logger)
    app.dependency_overrides[get_resume_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/resume",
                params=[
                    ("job_id", " job-2 "),
                    ("job_id", ""),
                    ("job_id", "job-2"),
                    ("job_id", "   "),
                ],
            )
            get_response = client.get("/api/resume/%20%20job-1%20%20")
            save_response = client.put(
                "/api/resume/%20%20job-1%20%20",
                json={
                    "kind": "sentence",
                    "sentence": 44,
                    "chunk_id": "chunk-44",
                    "media_type": "text",
                },
            )
            delete_response = client.delete("/api/resume/%20%20job-1%20%20")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert service.list_calls == [{"user_id": "alice", "job_ids": ["job-2"], "limit": 200}]
    assert response.json() == {
        "entries": [
            {
                key: value
                for key, value in asdict(service.entries[1]).items()
                if key in {"job_id", "kind", "updated_at", "position", "sentence", "chunk_id", "media_type", "base_id"}
            }
        ]
    }
    rendered = response.text
    assert "alice" not in rendered
    assert "/storage" not in rendered
    assert get_response.status_code == 200
    assert get_response.json()["job_id"] == "job-1"
    assert save_response.status_code == 200
    assert save_response.json()["job_id"] == "job-1"
    assert save_response.json()["entry"]["sentence"] == 44
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True}
    assert service.get_calls == [{"job_id": "job-1", "user_id": "alice"}]
    assert service.save_calls[0]["job_id"] == "job-1"
    assert service.save_calls[0]["user_id"] == "alice"
    assert service.clear_calls == [{"job_id": "job-1", "user_id": "alice"}]

    assert _has_resume_metric_count(metrics_response.text, operation="list", result="success")
    assert _has_resume_metric_count(metrics_response.text, operation="get", result="success")
    assert _has_resume_metric_count(metrics_response.text, operation="save", result="success")
    assert _has_resume_metric_count(metrics_response.text, operation="delete", result="success")

    logs = "\n".join(capture_logger.messages)
    assert "Resume route operation=list result=success" in logs
    assert "Resume route operation=get result=success" in logs
    assert "Resume route operation=save result=success" in logs
    assert "Resume route operation=delete result=success" in logs
    assert "entries=1" in logs
    assert "deleted=true" in logs
    assert "alice" not in logs
    assert "job-1" not in logs
    assert "job-2" not in logs


def test_resume_routes_require_authenticated_user(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(resume_router, "logger", capture_logger)
    app.dependency_overrides[get_resume_service] = lambda: _StubResumeService()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=None,
        user_role="anonymous",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/resume")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert _has_resume_metric_count(
        metrics_response.text,
        operation="list",
        result="unauthorized",
    )
    logs = "\n".join(capture_logger.messages)
    assert "Resume route operation=list result=unauthorized" in logs
    assert "anonymous" not in logs


def test_list_resume_positions_with_only_blank_filters_skips_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    service = _StubResumeService()
    capture_logger = _ListLogger()
    monkeypatch.setattr(resume_router, "logger", capture_logger)
    app.dependency_overrides[get_resume_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/resume",
                params=[("job_id", ""), ("job_id", "   ")],
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"entries": []}
    assert service.list_calls == []
    assert _has_resume_metric_count(metrics_response.text, operation="list", result="success")
    logs = "\n".join(capture_logger.messages)
    assert "Resume route operation=list result=success" in logs
    assert "entries=0" in logs
    assert "alice" not in logs


def test_resume_service_uses_safe_stat_for_playback_state_file(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ResumeService(file_locator=FileLocator(storage_dir=tmp_path))
    user_id = "alice.secret@example.test"
    job_id = "secret-job-1"
    storage_path = service._job_path(job_id, user_id)  # noqa: SLF001 - pins storage behavior.
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(
        """
        {
          "version": 1,
          "job_id": "secret-job-1",
          "user_id": "alice.secret@example.test",
          "updated_at": 1800000000.0,
          "entry": {
            "job_id": "secret-job-1",
            "kind": "time",
            "updated_at": 1800000000.0,
            "position": 42.5,
            "media_type": "audio",
            "base_id": "chunk-1"
          }
        }
        """,
        encoding="utf-8",
    )
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs) -> bool:
        if path == storage_path:
            raise AssertionError("resume service should stat playback state files via safe_stat")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    loaded = service.get(job_id, user_id)
    listed = service.list(user_id, job_ids=[job_id])
    deleted = service.clear(job_id, user_id)

    assert loaded is not None
    assert loaded.position == 42.5
    assert [entry.job_id for entry in listed] == [job_id]
    assert deleted is True
    assert not original_exists(storage_path)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/resume/%20%20%20"),
        ("put", "/api/resume/%20%20%20"),
        ("delete", "/api/resume/%20%20%20"),
    ],
)
def test_resume_routes_reject_blank_job_id_without_service_lookup(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
) -> None:
    app = create_app()
    service = _StubResumeService()
    capture_logger = _ListLogger()
    monkeypatch.setattr(resume_router, "logger", capture_logger)
    app.dependency_overrides[get_resume_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            if method == "put":
                response = client.put(path, json={"kind": "time", "position": 1.5})
            else:
                response = getattr(client, method)(path)
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": resume_router.RESUME_JOB_NOT_FOUND_MESSAGE}
    assert service.get_calls == []
    assert service.save_calls == []
    assert service.clear_calls == []
    operation = "save" if method == "put" else method
    assert _has_resume_metric_count(metrics_response.text, operation=operation, result="not_found")
    logs = "\n".join(capture_logger.messages)
    assert f"Resume route operation={operation} result=not_found" in logs
    assert "alice" not in logs


@pytest.mark.parametrize(
    ("method", "path", "operation"),
    [
        ("get", "/api/resume?job_id=secret-job-id", "list"),
        ("get", "/api/resume/secret-job-id", "get"),
        ("put", "/api/resume/secret-job-id", "save"),
        ("delete", "/api/resume/secret-job-id", "delete"),
    ],
)
def test_resume_route_storage_errors_use_token_safe_response(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    operation: str,
) -> None:
    app = create_app()
    service = _StubResumeService()
    capture_logger = _ListLogger()
    monkeypatch.setattr(resume_router, "logger", capture_logger)

    def fail(*args, **kwargs):
        raise RuntimeError(
            "resume storage failed for secret-job-id and alice at "
            "/Volumes/Data/private/resume/alice/secret-job-id.json"
        )

    if operation == "list":
        service.list = fail
    elif operation == "get":
        service.get = fail
    elif operation == "save":
        service.save = fail
    else:
        service.clear = fail

    app.dependency_overrides[get_resume_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            if method == "put":
                response = client.put(path, json={"kind": "time", "position": 1.5})
            else:
                response = getattr(client, method)(path)
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": resume_router.RESUME_STORAGE_UNAVAILABLE_MESSAGE}
    assert "secret-job-id" not in response.text
    assert "alice" not in response.text
    assert "/Volumes/Data" not in response.text
    assert _has_resume_metric_count(metrics_response.text, operation=operation, result="error")
    logs = "\n".join(capture_logger.messages)
    assert f"Resume route operation={operation} result=error" in logs
    assert "secret-job-id" not in logs
    assert "alice" not in logs
    assert "/Volumes/Data" not in logs


@pytest.mark.parametrize(
    ("method", "path", "operation", "service"),
    [
        ("get", "/api/resume?job_id=job-1", "list", _StubResumeService(invalid_entry=True)),
        ("get", "/api/resume/job-1", "get", _StubResumeService(invalid_entry=True)),
        ("put", "/api/resume/job-1", "save", _StubResumeService(invalid_entry=True)),
        ("delete", "/api/resume/job-1", "delete", _StubResumeService(invalid_delete=True)),
    ],
)
def test_resume_response_validation_errors_use_token_safe_response(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    operation: str,
    service: _StubResumeService,
) -> None:
    app = create_app()
    capture_logger = _ListLogger()
    monkeypatch.setattr(resume_router, "logger", capture_logger)
    app.dependency_overrides[get_resume_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="alice",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            if method == "put":
                response = client.put(path, json={"kind": "time", "position": 1.5})
            else:
                response = getattr(client, method)(path)
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": resume_router.RESUME_STORAGE_UNAVAILABLE_MESSAGE}
    assert "secret-kind" not in response.text
    assert "alice" not in response.text
    assert "job-1" not in response.text
    assert _has_resume_metric_count(metrics_response.text, operation=operation, result="error")
    logs = "\n".join(capture_logger.messages)
    assert f"Resume route operation={operation} result=error" in logs
    assert f"Resume route operation={operation} result=success" not in logs
    assert "secret-kind" not in logs
    assert "alice" not in logs
    assert "job-1" not in logs
