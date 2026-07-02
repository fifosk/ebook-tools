from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules import config_manager as cfg
from modules import epub_parser
import modules.webapi.routes.books_routes as books_routes
from modules.services.job_manager.job import PipelineJob, PipelineJobStatus
from modules.services.file_locator import FileLocator
from modules.services.pipeline_service import PipelineRequest, PipelineResponse
from modules.services.source_discovery import DiscoveredSourceFile
from modules.user_management.user_store_base import UserRecord
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_auth_service,
    get_pipeline_job_manager,
    get_pipeline_service,
    get_request_user,
    get_runtime_context_provider,
)
from modules.webapi.routes.books_routes import _list_ebook_files, _list_output_entries
import modules.webapi.routers.create_book as create_book_router
from modules.webapi.routers.create_book import _parse_sentences, _source_book_context
from modules.webapi.schemas.create_book import BookGenerationJobSubmission

pytestmark = pytest.mark.pipeline


class _StubAuthService:
    def __init__(self, user: UserRecord) -> None:
        self._user = user

    def authenticate(self, token: str | None) -> UserRecord | None:
        if token == "valid-token":
            return self._user
        return None


class _StubPipelineService:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []
        self.sync_requests: list[PipelineRequest] = []

    def enqueue(
        self,
        request: PipelineRequest,
        *,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> SimpleNamespace:
        job_id = f"book-{len(self.submissions) + 1}"
        self.submissions.append(
            {
                "request": request,
                "user_id": user_id,
                "user_role": user_role,
                "job_id": job_id,
            }
        )
        return SimpleNamespace(job_id=job_id, status="pending", request=request)

    def run_sync(self, request: PipelineRequest) -> PipelineResponse:
        self.sync_requests.append(request)
        return PipelineResponse(success=True, generated_files={"chunks": [], "files": []})


class _StubRuntimeContextProvider:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._base_config = {
            "working_dir": str(root / "working"),
            "output_dir": str(root / "working" / "ebook"),
            "tmp_dir": str(root / "tmp"),
            "ebooks_dir": str(root / "books"),
            "audio_mode": "4",
            "written_mode": "4",
            "include_transliteration": False,
            "tempo": 1.0,
            "selected_voice": "DemoVoice",
            "generate_audio": True,
            "use_ramdisk": False,
        }

    def resolve_config(self, updates: dict[str, object] | None = None) -> dict[str, object]:
        config = dict(self._base_config)
        if updates:
            config.update(updates)
        return config

    def build_context(
        self,
        config: dict[str, object],
        overrides: dict[str, object] | None = None,
    ):
        return cfg.build_runtime_context(dict(config), overrides or {})

    @contextmanager
    def activation(
        self,
        updates: dict[str, object] | None = None,
        overrides: dict[str, object] | None = None,
    ):
        yield self.build_context(self.resolve_config(updates), overrides)


class _RecordingJobManager:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []

    def submit_background_job(self, **kwargs):
        self.submissions.append(kwargs)
        return PipelineJob(
            job_id="book-job-1",
            status=PipelineJobStatus.PENDING,
            created_at=datetime(2026, 6, 24, tzinfo=timezone.utc),
            request_payload=dict(kwargs.get("request_payload") or {}),
            user_id=kwargs.get("user_id"),
            user_role=kwargs.get("user_role"),
            job_type=str(kwargs.get("job_type") or "pipeline"),
        )


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def warning(self, message: str, *args: object, **kwargs: object) -> None:
        self.messages.append(message % args if args else message)


def _has_metric_count(
    metrics_text: str,
    family_name: str,
    *,
    operation: str,
    result: str,
) -> bool:
    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_text)
    }
    metric = families[family_name]
    return any(
        sample.labels.get("operation") == operation
        and sample.labels.get("result") == result
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )


def test_pipeline_ebook_listing_is_newest_first_with_metadata(tmp_path: Path) -> None:
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    older = books_dir / "z-older.epub"
    newer = books_dir / "a-newer.epub"
    older.write_bytes(b"older")
    newer.write_bytes(b"newer ebook")
    older_mtime = 1_700_000_000
    newer_mtime = 1_700_000_200
    older.touch()
    newer.touch()
    os.utime(older, (older_mtime, older_mtime))
    os.utime(newer, (newer_mtime, newer_mtime))

    entries = _list_ebook_files(books_dir)

    assert [entry.name for entry in entries] == ["a-newer.epub", "z-older.epub"]
    assert entries[0].size_bytes == len(b"newer ebook")
    assert entries[0].modified_at is not None


def test_pipeline_ebook_listing_can_limit_newest_entries(tmp_path: Path) -> None:
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    oldest = books_dir / "oldest.epub"
    middle = books_dir / "middle.epub"
    newest = books_dir / "newest.epub"
    oldest.write_bytes(b"oldest")
    middle.write_bytes(b"middle")
    newest.write_bytes(b"newest")
    os.utime(oldest, (1_700_000_000, 1_700_000_000))
    os.utime(middle, (1_700_000_100, 1_700_000_100))
    os.utime(newest, (1_700_000_200, 1_700_000_200))

    entries = _list_ebook_files(books_dir, limit=2)

    assert [entry.name for entry in entries] == ["newest.epub", "middle.epub"]


def test_pipeline_ebook_listing_uses_streaming_source_iterator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    older = books_dir / "older.epub"
    newer = books_dir / "newer.epub"
    older.write_bytes(b"older")
    newer.write_bytes(b"newer")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_700_000_300, 1_700_000_300))
    calls: list[dict[str, object]] = []

    def fake_iter_visible_source_files(root: Path, **kwargs):
        calls.append({"root": root, **kwargs})
        yield DiscoveredSourceFile(path=older, stat=older.stat())
        yield DiscoveredSourceFile(path=newer, stat=newer.stat())

    monkeypatch.setattr(books_routes, "iter_visible_source_files", fake_iter_visible_source_files)

    entries = _list_ebook_files(books_dir, limit=1)

    assert calls == [
        {
            "root": books_dir,
            "suffixes": {".epub"},
        }
    ]
    assert [entry.name for entry in entries] == ["newer.epub"]


def test_pipeline_ebook_listing_accepts_uppercase_epub_suffix(tmp_path: Path) -> None:
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    uppercase = books_dir / "NAS-LATEST.EPUB"
    lowercase = books_dir / "older.epub"
    hidden = books_dir / ".hidden.EPUB"
    not_epub = books_dir / "notes.txt"
    uppercase.write_bytes(b"uppercase ebook")
    lowercase.write_bytes(b"lowercase ebook")
    hidden.write_bytes(b"hidden ebook")
    not_epub.write_text("not an ebook", encoding="utf-8")
    older_mtime = 1_700_000_000
    newer_mtime = 1_700_000_300
    os.utime(lowercase, (older_mtime, older_mtime))
    os.utime(uppercase, (newer_mtime, newer_mtime))

    entries = _list_ebook_files(books_dir)

    assert [entry.name for entry in entries] == ["NAS-LATEST.EPUB", "older.epub"]
    assert entries[0].size_bytes == len(b"uppercase ebook")
    assert entries[0].modified_at is not None


def test_pipeline_ebook_listing_recurses_into_visible_nas_folders(tmp_path: Path) -> None:
    books_dir = tmp_path / "books"
    nested_dir = books_dir / "Dan Brown"
    hidden_dir = books_dir / ".imports"
    nested_dir.mkdir(parents=True)
    hidden_dir.mkdir(parents=True)
    root_book = books_dir / "older.epub"
    nested_book = nested_dir / "latest.EPUB"
    hidden_book = hidden_dir / "hidden.epub"
    root_book.write_bytes(b"older")
    nested_book.write_bytes(b"latest")
    hidden_book.write_bytes(b"hidden")
    older_mtime = 1_700_000_000
    newer_mtime = 1_700_000_400
    os.utime(root_book, (older_mtime, older_mtime))
    os.utime(nested_book, (newer_mtime, newer_mtime))

    entries = _list_ebook_files(books_dir)

    assert [entry.path for entry in entries] == ["Dan Brown/latest.EPUB", "older.epub"]
    assert entries[0].name == "latest.EPUB"
    assert entries[0].size_bytes == len(b"latest")


def test_pipeline_file_listing_skips_entries_that_disappear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    books_dir = tmp_path / "books"
    output_dir = tmp_path / "output"
    books_dir.mkdir()
    output_dir.mkdir()
    stable_book = books_dir / "stable.epub"
    vanished_book = books_dir / "vanished.epub"
    stable_output = output_dir / "stable-output"
    vanished_output = output_dir / "vanished-output"
    stable_book.write_bytes(b"stable")
    vanished_book.write_bytes(b"vanished")
    stable_output.mkdir()
    vanished_output.mkdir()

    original_stat = Path.stat

    def fake_stat(path: Path, *args, **kwargs):
        if path.name in {"vanished.epub", "vanished-output"}:
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    ebook_entries = _list_ebook_files(books_dir)
    output_entries = _list_output_entries(output_dir)

    assert [entry.name for entry in ebook_entries] == ["stable.epub"]
    assert [entry.name for entry in output_entries] == ["stable-output"]


def test_pipeline_file_listing_tolerates_root_scan_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    books_dir = tmp_path / "books"
    output_dir = tmp_path / "output"
    books_dir.mkdir()
    output_dir.mkdir()
    original_walk = os.walk
    original_iterdir = Path.iterdir

    def fake_walk(path: Path, *args, **kwargs):
        if Path(path) == books_dir:
            if False:
                yield None
            return
        yield from original_walk(path, *args, **kwargs)

    def fake_iterdir(path: Path, *args, **kwargs):
        if path in {books_dir, output_dir}:
            raise OSError(f"{path} is temporarily unavailable")
        return original_iterdir(path, *args, **kwargs)

    monkeypatch.setattr("modules.services.source_discovery.os.walk", fake_walk)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)

    assert _list_ebook_files(books_dir) == []
    assert _list_output_entries(output_dir) == []


def test_pipeline_output_listing_uses_safe_root_stat_instead_of_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "finished-job").mkdir()
    original_exists = Path.exists

    def fake_exists(path: Path, *args, **kwargs):
        if path == output_dir:
            raise OSError("transient NAS exists failure")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", fake_exists)

    entries = _list_output_entries(output_dir)

    assert [entry.name for entry in entries] == ["finished-job"]
    assert entries[0].type == "directory"


def test_reserve_destination_path_uses_safe_stat_instead_of_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = tmp_path / "latest.epub"
    existing.write_bytes(b"existing")
    original_exists = Path.exists

    def guarded_exists(path: Path, *args, **kwargs):
        if path == existing:
            raise AssertionError("destination reservation should use safe_stat instead of exists")
        return original_exists(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    reserved = books_routes._reserve_destination_path(tmp_path, "latest.epub")

    assert reserved == tmp_path / "latest-1.epub"


def test_pipeline_file_picker_records_safe_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    output_dir = tmp_path / "working" / "ebook"
    secret_dir = books_dir / "Secret Dan Brown Continuation"
    secret_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    (secret_dir / "latest.epub").write_bytes(b"latest")
    (output_dir / "finished-job").mkdir()
    logger = _RecordingLogger()

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(books_routes, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get("/api/pipelines/files")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["ebooks"][0]["path"] == "Secret Dan Brown Continuation/latest.epub"
    assert body["outputs"][0]["path"] == "finished-job"

    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline source picker result=success ebooks=1 outputs=1" in rendered_logs
    assert "Secret Dan Brown Continuation" not in rendered_logs
    assert "latest.epub" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs

    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="pipeline_files",
        result="success",
    )


def test_pipeline_file_picker_accepts_bounded_picker_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    newer_dir = books_dir / "Public"
    output_dir = tmp_path / "working" / "ebook"
    newer_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    older = books_dir / "older.epub"
    newer = newer_dir / "newer.epub"
    older.write_bytes(b"older")
    newer.write_bytes(b"newer")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_700_000_300, 1_700_000_300))
    older_output = output_dir / "zzz-older-output"
    newer_output = output_dir / "aaa-newer-output"
    older_output.mkdir()
    newer_output.mkdir()
    os.utime(older_output, (1_700_000_010, 1_700_000_010))
    os.utime(newer_output, (1_700_000_400, 1_700_000_400))
    logger = _RecordingLogger()

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(books_routes, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get("/api/pipelines/files", params={"limit": 1})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [entry["path"] for entry in body["ebooks"]] == ["Public/newer.epub"]
    assert [entry["path"] for entry in body["outputs"]] == ["aaa-newer-output"]
    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline source picker result=success ebooks=1 outputs=1 picker_limit=1" in rendered_logs
    assert "Public/newer.epub" not in rendered_logs
    assert "aaa-newer-output" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs


def test_pipeline_file_picker_rejects_invalid_picker_limit(tmp_path: Path) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )
    try:
        with TestClient(app) as client:
            response = client.get("/api/pipelines/files", params={"limit": 0})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_pipeline_content_index_uses_selected_epub(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books" / "Dan Brown"
    books_dir.mkdir(parents=True)
    selected = books_dir / "latest-continuation.epub"
    selected.write_bytes(b"epub bytes")
    calls: dict[str, object] = {}
    expected_index = {
        "total_sentences": 2,
        "chapters": [
            {
                "title": "Chapter 1",
                "start_sentence": 0,
                "end_sentence": 1,
            }
        ],
        "alignment": {"status": "aligned"},
    }
    logger = _RecordingLogger()

    def fake_get_refined_sentences(input_file: str, pipeline_config, **kwargs):
        calls["refined_input_file"] = input_file
        calls["refined_max_words"] = pipeline_config.max_words
        calls["refined_force_refresh"] = kwargs.get("force_refresh")
        calls["refined_metadata"] = kwargs.get("metadata")
        return ["One.", "Two."], False

    def fake_get_content_index(
        input_file: str,
        pipeline_config,
        refined_sentences,
        **kwargs,
    ):
        calls["content_input_file"] = input_file
        calls["content_max_words"] = pipeline_config.max_words
        calls["content_refined_sentences"] = list(refined_sentences)
        calls["content_force_refresh"] = kwargs.get("force_refresh")
        calls["content_metadata"] = kwargs.get("metadata")
        return expected_index

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(
        books_routes.ingestion,
        "get_refined_sentences",
        fake_get_refined_sentences,
    )
    monkeypatch.setattr(books_routes.ingestion, "get_content_index", fake_get_content_index)
    monkeypatch.setattr(books_routes, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/pipelines/files/content-index",
                params={"input_file": " Dan Brown/latest-continuation.epub "},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "input_file": "Dan Brown/latest-continuation.epub",
        "content_index": expected_index,
    }
    assert calls["refined_input_file"] == str(selected)
    assert calls["content_input_file"] == str(selected)
    assert calls["content_refined_sentences"] == ["One.", "Two."]
    assert calls["refined_force_refresh"] is False
    assert calls["content_force_refresh"] is False
    assert calls["refined_metadata"] == {
        "mode": "api",
        "max_words": calls["refined_max_words"],
    }
    assert calls["content_metadata"] == {
        "mode": "api",
        "max_words": calls["content_max_words"],
    }
    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline content index result=success chapters=1 sentences=2" in rendered_logs
    assert "latest-continuation.epub" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="pipeline_content_index",
        result="success",
    )


def test_pipeline_content_index_uses_safe_stat_for_selected_epub(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    books_dir.mkdir(parents=True)
    selected = books_dir / "latest-continuation.epub"
    selected.write_bytes(b"epub bytes")
    original_exists = Path.exists
    calls: dict[str, object] = {}

    def guarded_exists(path: Path, *args, **kwargs):
        if path == selected:
            raise AssertionError("content-index route should use safe_stat instead of exists")
        return original_exists(path, *args, **kwargs)

    def fake_get_refined_sentences(input_file: str, *_args, **_kwargs):
        calls["refined_input_file"] = input_file
        return ["One."], False

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(books_routes.cfg, "resolve_file_path", lambda *_args, **_kwargs: selected)
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(books_routes.ingestion, "get_refined_sentences", fake_get_refined_sentences)
    monkeypatch.setattr(
        books_routes.ingestion,
        "get_content_index",
        lambda *_args, **_kwargs: {"total_sentences": 1, "chapters": []},
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/pipelines/files/content-index",
                params={"input_file": "latest-continuation.epub"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls["refined_input_file"] == str(selected)


def test_epub_parser_raises_instead_of_exiting_for_unreadable_epub(tmp_path: Path) -> None:
    selected = tmp_path / "broken.epub"
    selected.write_bytes(b"not an epub")

    with pytest.raises(RuntimeError, match="EPUB file could not be read"):
        epub_parser.extract_text_from_epub(str(selected))


def test_pipeline_content_index_returns_422_when_epub_cannot_be_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    books_dir.mkdir(parents=True)
    selected = books_dir / "broken.epub"
    selected.write_bytes(b"not an epub")
    logger = _RecordingLogger()

    def fake_get_refined_sentences(*_args, **_kwargs):
        raise RuntimeError(f"EPUB file could not be read: {selected}")

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(
        books_routes.ingestion,
        "get_refined_sentences",
        fake_get_refined_sentences,
    )
    monkeypatch.setattr(books_routes, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/pipelines/files/content-index",
                params={"input_file": "broken.epub"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Unable to load chapters for this EPUB. The file may be corrupt or unsupported."
    }
    rendered_logs = "\n".join(logger.messages)
    assert "Pipeline content index result=error chapters=0 sentences=0" in rendered_logs
    assert "broken.epub" not in rendered_logs
    assert str(tmp_path) not in rendered_logs
    assert "EPUB file could not be read" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="pipeline_content_index",
        result="error",
    )


@pytest.mark.parametrize(
    ("params", "expected_status", "expected_detail", "expected_result"),
    [
        ({"input_file": "   "}, 400, "input_file is required", "bad_request"),
        ({"input_file": "missing.epub"}, 404, "EPUB file not found", "not_found"),
    ],
)
def test_pipeline_content_index_records_validation_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    params: dict[str, str],
    expected_status: int,
    expected_detail: str,
    expected_result: str,
) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    books_dir.mkdir(parents=True)
    logger = _RecordingLogger()

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(books_routes, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get("/api/pipelines/files/content-index", params=params)
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    rendered_logs = "\n".join(logger.messages)
    assert f"Pipeline content index result={expected_result}" in rendered_logs
    assert "missing.epub" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="pipeline_content_index",
        result=expected_result,
    )


def test_delete_pipeline_ebook_is_idempotent_for_missing_in_scope_file(tmp_path: Path) -> None:
    app = create_app()
    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    books_dir.mkdir()

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider

    try:
        with TestClient(app) as client:
            response = client.request(
                "DELETE",
                "/api/pipelines/files",
                json={"path": "vanished.epub"},
                headers={"Authorization": "Bearer valid-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204


def test_delete_pipeline_ebook_rejects_missing_file_outside_books_root(tmp_path: Path) -> None:
    app = create_app()
    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    (tmp_path / "books").mkdir()

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider

    try:
        with TestClient(app) as client:
            response = client.request(
                "DELETE",
                "/api/pipelines/files",
                json={"path": "../outside.epub"},
                headers={"Authorization": "Bearer valid-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid ebook path"


def test_delete_pipeline_ebook_uses_generic_error_when_unlink_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    secret_dir = books_dir / "Secret Dan Brown Continuation"
    secret_dir.mkdir(parents=True)
    selected = secret_dir / "latest.epub"
    selected.write_bytes(b"ebook")
    selected_resolved = selected.resolve()
    original_unlink = Path.unlink

    def fake_unlink(path: Path, *args, **kwargs):
        if path == selected_resolved:
            raise OSError(f"permission denied for {selected_resolved}")
        return original_unlink(path, *args, **kwargs)

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    monkeypatch.setattr(Path, "unlink", fake_unlink)

    try:
        with TestClient(app) as client:
            response = client.request(
                "DELETE",
                "/api/pipelines/files",
                json={"path": "Secret Dan Brown Continuation/latest.epub"},
                headers={"Authorization": "Bearer valid-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to delete ebook."
    assert "Secret Dan Brown Continuation" not in response.text
    assert "latest.epub" not in response.text
    assert str(tmp_path) not in response.text


def test_delete_pipeline_ebook_uses_safe_stat_for_target_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    selected = books_dir / "latest.epub"
    selected.write_bytes(b"ebook")
    selected_resolved = selected.resolve()
    original_exists = Path.exists
    original_is_file = Path.is_file

    def guarded_exists(path: Path, *args, **kwargs):
        if path == selected_resolved:
            raise AssertionError("ebook deletion should use safe_stat instead of exists")
        return original_exists(path, *args, **kwargs)

    def guarded_is_file(path: Path, *args, **kwargs):
        if path == selected_resolved:
            raise AssertionError("ebook deletion should use safe_stat instead of is_file")
        return original_is_file(path, *args, **kwargs)

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    monkeypatch.setattr(Path, "exists", guarded_exists)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)

    try:
        with TestClient(app) as client:
            response = client.request(
                "DELETE",
                "/api/pipelines/files",
                json={"path": "latest.epub"},
                headers={"Authorization": "Bearer valid-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert not original_exists(selected)


def test_upload_pipeline_ebook_persists_file_in_books_root(tmp_path: Path) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    (books_dir / "latest.epub").write_bytes(b"existing")

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(
        user_id="office-ipad-user",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/pipelines/files/upload",
                files={
                    "file": (
                        "../latest.epub",
                        b"uploaded epub bytes",
                        "application/epub+zip",
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "latest-1.epub"
    assert body["path"] == "latest-1.epub"
    assert body["type"] == "file"
    assert body["size_bytes"] == len(b"uploaded epub bytes")
    assert (books_dir / "latest.epub").read_bytes() == b"existing"
    assert (books_dir / "latest-1.epub").read_bytes() == b"uploaded epub bytes"
    assert not (tmp_path / "latest.epub").exists()


def test_upload_cover_file_uses_generic_error_when_decode_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    def fake_open(*_args, **_kwargs):
        raise ValueError(f"corrupt cover at {tmp_path / 'Secret Dan Brown cover.png'}")

    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    monkeypatch.setattr(books_routes.Image, "open", fake_open)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/pipelines/covers/upload",
                files={
                    "file": (
                        "Secret Dan Brown cover.png",
                        b"not really an image",
                        "image/png",
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415
    assert response.json()["detail"] == "Unable to process cover image."
    assert "Secret Dan Brown" not in response.text
    assert str(tmp_path) not in response.text


def test_book_generation_job_schema_accepts_source_context() -> None:
    payload = BookGenerationJobSubmission.model_validate(
        {
            "generator": {
                "input_language": "English",
                "output_language": "French",
                "voice": "DemoVoice",
                "num_sentences": 2,
                "topic": "A new symbol trail",
                "book_name": "The Marble Cipher",
                "genre": "Mystery thriller",
                "author": "Me",
                "source_book_title": " Inferno ",
                "source_book_author": " Dan Brown ",
                "source_book_genre": " Conspiracy thriller ",
                "source_book_summary": " A symbologist follows clues across Europe. ",
            },
            "pipeline": {
                "config": {
                    "acquisition_provider": " LOCAL_EPUB ",
                    "source_kind": " Local_Epub ",
                    "media_metadata_lookup": {
                        "provider": " OpenLibrary ",
                        "candidate_id": "OpenLibrary:/works/OL45883W",
                    },
                },
                "inputs": {
                    "input_file": "generated.epub",
                    "base_output_file": "generated",
                    "input_language": "English",
                    "target_languages": ["French"],
                    "book_metadata": {
                        "source_kind": " GUTENBERG ",
                        "source_provider": " Internet_Archive ",
                        "acquisition_provider": " OpenLibrary ",
                        "acquisition_candidate_id": "OpenLibrary:/works/OL45883W",
                        "source_url": "HTTPS://Example.test/Book.EPUB",
                        "media_metadata_lookup": {
                            "provider": " OpenLibrary ",
                            "book": {"title": "Inferno"},
                        },
                    },
                }
            },
        }
    )

    assert payload.generator.source_book_title == "Inferno"
    assert payload.generator.source_book_author == "Dan Brown"
    assert payload.generator.source_book_genre == "Conspiracy thriller"
    assert payload.generator.source_book_summary == "A symbologist follows clues across Europe."
    assert payload.pipeline.config["acquisition_provider"] == "local_epub"
    assert payload.pipeline.config["source_kind"] == "local_epub"
    assert payload.pipeline.config["media_metadata_lookup"]["provider"] == "openlibrary"
    assert payload.pipeline.config["media_metadata_lookup"]["candidate_id"] == "OpenLibrary:/works/OL45883W"
    metadata = payload.pipeline.inputs.media_metadata
    assert metadata["source_kind"] == "gutenberg"
    assert metadata["source_provider"] == "internet_archive"
    assert metadata["acquisition_provider"] == "openlibrary"
    assert metadata["media_metadata_lookup"]["provider"] == "openlibrary"
    assert metadata["acquisition_candidate_id"] == "OpenLibrary:/works/OL45883W"
    assert metadata["source_url"] == "HTTPS://Example.test/Book.EPUB"


def test_source_book_context_normalizes_optional_continuation_fields() -> None:
    context = _source_book_context(
        SimpleNamespace(
            source_book_title=" Inferno ",
            source_book_author=" Dan Brown ",
            source_book_genre=" ",
            source_book_summary=None,
        )
    )

    assert context == {
        "source_book_title": "Inferno",
        "source_book_author": "Dan Brown",
    }


def test_parse_sentences_rejects_json_string_payload() -> None:
    with pytest.raises(ValueError, match="sentence list"):
        _parse_sentences('"One sentence only."', 1)


def test_parse_sentences_accepts_named_sentence_list_and_dedupes() -> None:
    payload = {
        "sentences": [
            "First generated sentence.",
            "First generated sentence.",
            "This is a sample sentence",
            "Second generated sentence.",
        ]
    }

    assert _parse_sentences(json.dumps(payload), 2) == [
        "First generated sentence.",
        "Second generated sentence.",
    ]


def test_parse_sentences_ignores_non_string_items() -> None:
    payload = {
        "sentences": [
            {"text": "Object payload should not be coerced."},
            123,
            "Actual sentence.",
        ]
    }

    assert _parse_sentences(json.dumps(payload), 1) == ["Actual sentence."]


def test_create_book_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_pipeline = _StubPipelineService()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_pipeline_service] = lambda: stub_pipeline
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider

    captured_generation: dict[str, object] = {}

    def fake_generate_sentences(**kwargs):
        captured_generation.update(kwargs)
        return ["One.", "Two."][: kwargs["count"]]

    monkeypatch.setattr(
        "modules.webapi.routers.create_book._generate_sentences",
        fake_generate_sentences,
    )

    client = TestClient(app)

    payload = {
        "input_language": "English",
        "output_language": "French",
        "voice": "DemoVoice",
        "num_sentences": 2,
        "topic": "Rain",
        "book_name": "Drops",
        "genre": "Poetry",
        "author": "Me",
        "source_book_title": "Inferno",
        "source_book_author": "Dan Brown",
        "source_book_genre": "Conspiracy thriller",
        "source_book_summary": "A symbologist follows clues across Europe.",
    }

    response = client.post(
        "/api/books/create",
        json=payload,
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "prepared"
    assert body["metadata"]["book_title"] == "Drops"
    assert body["metadata"]["source_book_title"] == "Inferno"
    assert body["metadata"]["source_book_author"] == "Dan Brown"
    assert body["metadata"]["source_book_genre"] == "Conspiracy thriller"
    assert body["metadata"]["source_book_summary"] == "A symbologist follows clues across Europe."
    assert body["metadata"]["generated_sentences"] == ["One.", "Two."]
    assert captured_generation["source_book_title"] == "Inferno"
    assert captured_generation["source_book_author"] == "Dan Brown"
    assert captured_generation["source_book_genre"] == "Conspiracy thriller"
    assert captured_generation["source_book_summary"] == "A symbologist follows clues across Europe."
    assert body["messages"]
    assert any("Seed EPUB prepared" in message for message in body["messages"])
    assert body["warnings"] == []
    assert isinstance(body["epub_path"], str) and body["epub_path"].endswith(".epub")
    assert body["sentences_preview"] == ["One.", "Two."]

    # The /create endpoint no longer submits a pipeline job; it returns a
    # prepared payload for the client to review and then submit separately
    # via /api/books/jobs.
    assert not stub_pipeline.submissions

    # Verify the returned metadata contains creation summary
    creation_summary = body["metadata"].get("creation_summary")
    assert isinstance(creation_summary, dict)
    assert creation_summary.get("epub_path", "").endswith(".epub")
    assert creation_summary.get("messages")
    assert creation_summary.get("sentences_preview") == ["One.", "Two."]

    # Verify the input_file path exists (for potential submission)
    input_file = Path(body["input_file"])
    assert input_file.exists()
    assert input_file.suffix == ".epub"


def test_create_book_endpoint_uses_generic_error_when_sentence_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    def fake_generate_sentences(**_kwargs):
        raise RuntimeError("LLM prompt leaked Secret Dan Brown continuation")

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    monkeypatch.setattr(create_book_router, "_generate_sentences", fake_generate_sentences)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/books/create",
                json={
                    "input_language": "English",
                    "output_language": "French",
                    "voice": "DemoVoice",
                    "num_sentences": 2,
                    "topic": "Secret Dan Brown continuation",
                    "book_name": "Private Draft",
                    "genre": "Mystery",
                    "author": "Me",
                },
                headers={"Authorization": "Bearer valid-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Sentence generation failed."
    assert "Secret Dan Brown" not in response.text
    assert "Private Draft" not in response.text


def test_create_book_endpoint_uses_generic_error_when_epub_preparation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    def fake_generate_sentences(**kwargs):
        return ["One.", "Two."][: kwargs["count"]]

    def fake_create_epub(*_args, **_kwargs):
        raise OSError(f"cannot write {tmp_path / 'books' / 'Private Draft.epub'}")

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    monkeypatch.setattr(create_book_router, "_generate_sentences", fake_generate_sentences)
    monkeypatch.setattr(create_book_router, "create_epub_from_sentences", fake_create_epub)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/books/create",
                json={
                    "input_language": "English",
                    "output_language": "French",
                    "voice": "DemoVoice",
                    "num_sentences": 2,
                    "topic": "Rain",
                    "book_name": "Private Draft",
                    "genre": "Poetry",
                    "author": "Me",
                },
                headers={"Authorization": "Bearer valid-token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to prepare EPUB."
    assert "Private Draft" not in response.text
    assert str(tmp_path) not in response.text


def test_submit_book_job_preserves_source_context_at_enqueue_boundary(tmp_path: Path) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    stub_pipeline = _StubPipelineService()
    job_manager = _RecordingJobManager()

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    app.dependency_overrides[get_pipeline_service] = lambda: stub_pipeline
    app.dependency_overrides[get_pipeline_job_manager] = lambda: job_manager

    client = TestClient(app)

    response = client.post(
        "/api/books/jobs",
        json={
            "generator": {
                "input_language": "English",
                "output_language": "French",
                "voice": "DemoVoice",
                "num_sentences": 2,
                "topic": "A new symbol trail",
                "book_name": "The Marble Cipher",
                "genre": "Mystery thriller",
                "author": "Me",
                "source_book_title": " Inferno ",
                "source_book_author": " Dan Brown ",
                "source_book_genre": " Conspiracy thriller ",
                "source_book_summary": " ",
            },
            "pipeline": {
                "config": {
                    "acquisition_provider": " LOCAL_EPUB ",
                    "source_kind": " Local_Epub ",
                },
                "inputs": {
                    "input_file": "generated.epub",
                    "base_output_file": "generated",
                    "input_language": "English",
                    "target_languages": ["French"],
                    "book_metadata": {
                        "acquisition_provider": " OpenLibrary ",
                        "acquisition_candidate_id": "OpenLibrary:/works/OL45883W",
                        "source_kind": " OpenLibrary ",
                    },
                }
            },
        },
        headers={"X-User-Id": "editor", "X-User-Role": "editor"},
    )

    assert response.status_code == 202
    assert response.json()["job_type"] == "book"
    assert len(job_manager.submissions) == 1
    submission = job_manager.submissions[0]
    assert submission["job_type"] == "book"
    assert submission["user_id"] == "editor"
    assert submission["user_role"] == "editor"
    request_payload = submission["request_payload"]
    assert isinstance(request_payload, dict)
    book_generation = request_payload["book_generation"]
    assert book_generation["source_book_title"] == "Inferno"
    assert book_generation["source_book_author"] == "Dan Brown"
    assert book_generation["source_book_genre"] == "Conspiracy thriller"
    assert "source_book_summary" not in book_generation
    pipeline_config = request_payload["config"]
    assert pipeline_config["acquisition_provider"] == "local_epub"
    assert pipeline_config["source_kind"] == "local_epub"
    media_metadata = request_payload["inputs"]["media_metadata"]
    assert media_metadata["acquisition_provider"] == "openlibrary"
    assert media_metadata["source_kind"] == "openlibrary"
    assert media_metadata["acquisition_candidate_id"] == "OpenLibrary:/works/OL45883W"


def test_execute_book_job_uses_generic_warning_when_metadata_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    stub_pipeline = _StubPipelineService()
    logger = _RecordingLogger()
    job = PipelineJob(
        job_id="secret-dan-brown-job",
        status=PipelineJobStatus.RUNNING,
        created_at=datetime(2026, 6, 26, tzinfo=timezone.utc),
        job_type="book",
    )
    payload = BookGenerationJobSubmission.model_validate(
        {
            "generator": {
                "input_language": "English",
                "output_language": "French",
                "voice": "DemoVoice",
                "num_sentences": 1,
                "topic": "Secret Dan Brown continuation",
                "book_name": "Private Draft",
                "genre": "Mystery",
                "author": "Me",
            },
            "pipeline": {
                "inputs": {
                    "input_file": "generated.epub",
                    "base_output_file": "generated",
                    "input_language": "English",
                    "target_languages": ["French"],
                }
            },
        }
    )

    def fake_generate_sentences(**_kwargs):
        return ["One generated sentence."]

    def fake_generate_metadata(**_kwargs):
        raise RuntimeError("metadata prompt leaked /Volumes/Data/Secret Dan Brown.epub")

    monkeypatch.setattr(create_book_router, "logger", logger)
    monkeypatch.setattr(create_book_router, "_generate_sentences", fake_generate_sentences)
    monkeypatch.setattr(create_book_router, "_generate_llm_metadata", fake_generate_metadata)

    create_book_router._execute_book_job(
        job,
        generator=payload,
        context_provider=stub_context_provider,
        pipeline_service=stub_pipeline,
        file_locator=FileLocator(storage_dir=tmp_path / "storage"),
    )

    assert job.status == PipelineJobStatus.COMPLETED
    assert len(stub_pipeline.sync_requests) == 1
    metadata = stub_pipeline.sync_requests[0].inputs.media_metadata.as_dict()
    warnings = metadata["creation_warnings"]
    assert warnings == ["Metadata generation failed."]
    rendered_logs = "\n".join(logger.messages)
    assert "Generated book metadata generation failed" in rendered_logs
    assert "secret-dan-brown-job" not in rendered_logs
    assert "Secret Dan Brown" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs


def test_execute_book_job_uses_generic_warning_when_cover_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    stub_pipeline = _StubPipelineService()
    logger = _RecordingLogger()
    job = PipelineJob(
        job_id="secret-cover-job",
        status=PipelineJobStatus.RUNNING,
        created_at=datetime(2026, 6, 26, tzinfo=timezone.utc),
        job_type="book",
    )
    payload = BookGenerationJobSubmission.model_validate(
        {
            "generator": {
                "input_language": "English",
                "output_language": "French",
                "voice": "DemoVoice",
                "num_sentences": 1,
                "topic": "Rain",
                "book_name": "Private Draft",
                "genre": "Mystery",
                "author": "Me",
            },
            "pipeline": {
                "inputs": {
                    "input_file": "generated.epub",
                    "base_output_file": "generated",
                    "input_language": "English",
                    "target_languages": ["French"],
                }
            },
        }
    )

    def fake_generate_sentences(**_kwargs):
        return ["One generated sentence."]

    def fake_generate_metadata(**_kwargs):
        return {
            "summary": "A short summary.",
            "genre": "Mystery",
            "cover_prompt": "A rain-soaked book cover.",
        }

    def fake_generate_cover_image(**_kwargs):
        raise RuntimeError("DrawThings endpoint leaked http://secret-node.local")

    monkeypatch.setattr(create_book_router, "logger", logger)
    monkeypatch.setattr(create_book_router, "_generate_sentences", fake_generate_sentences)
    monkeypatch.setattr(create_book_router, "_generate_llm_metadata", fake_generate_metadata)
    monkeypatch.setattr(create_book_router, "_generate_cover_image", fake_generate_cover_image)

    create_book_router._execute_book_job(
        job,
        generator=payload,
        context_provider=stub_context_provider,
        pipeline_service=stub_pipeline,
        file_locator=FileLocator(storage_dir=tmp_path / "storage"),
    )

    assert job.status == PipelineJobStatus.COMPLETED
    assert len(stub_pipeline.sync_requests) == 1
    metadata = stub_pipeline.sync_requests[0].inputs.media_metadata.as_dict()
    warnings = metadata["creation_warnings"]
    assert warnings == ["Cover generation failed."]
    rendered_logs = "\n".join(logger.messages)
    assert "Generated book cover generation failed" in rendered_logs
    assert "secret-cover-job" not in rendered_logs
    assert "secret-node" not in rendered_logs


def test_book_creation_options_endpoint_returns_non_secret_defaults(tmp_path: Path) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider

    client = TestClient(app)

    response = client.get(
        "/api/books/options",
        headers={"X-User-Id": "editor", "X-User-Role": "editor"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sentence_bounds"] == {"min": 1, "max": 500, "default": 30}
    assert body["defaults"]["author"] == "Me"
    assert body["defaults"]["input_language"] == "English"
    assert body["defaults"]["output_language"] == "Arabic"
    assert body["defaults"]["voice"] == "DemoVoice"
    assert body["pipeline_defaults"]["audio_mode"] == "4"
    assert body["pipeline_defaults"]["stitch_full"] is False
    assert body["pipeline_defaults"]["written_mode"] == "4"
    assert body["pipeline_defaults"]["selected_voice"] == "DemoVoice"
    assert body["pipeline_defaults"]["sentence_splitter_mode"] == "regex"
    assert body["sentence_splitter_capabilities"] == {
        "default_mode": "regex",
        "supported_modes": [
            {
                "id": "regex",
                "label": "Regex (stable)",
                "cache_version": "regex-v9",
                "stable": True,
            },
            {
                "id": "modern",
                "label": "Modern (opt-in)",
                "cache_version": "modern-syntok-v2+regex-v9-fallback",
                "stable": False,
            },
        ],
        "comparison_metric_fields": [
            "normalized_text_preserved",
            "contiguous_text_preserved",
            "matched_sentence_count",
            "unmatched_sentence_count",
            "unmatched_sentence_indices",
            "skipped_text_character_count",
            "trailing_text_character_count",
            "tiny_fragment_count",
            "max_words_per_segment",
        ],
    }
    assert body["generated_source_defaults"]["image_style_template"] == "wireframe"
    assert body["subtitle_defaults"] == {
        "worker_count": 10,
        "batch_size": 20,
        "translation_batch_size": 10,
        "ass_font_size": 56,
        "ass_emphasis_scale": 1.3,
    }
    assert body["youtube_dub_defaults"] == {
        "original_mix_percent": 5.0,
        "flush_sentences": 10,
        "translation_batch_size": 10,
        "split_batches": True,
        "stitch_batches": True,
        "target_height": 480,
        "preserve_aspect_ratio": True,
    }
    assert "English" in body["supported_input_languages"]
    assert "Hindi" in body["supported_input_languages"]
    assert "Chinese (Traditional)" in body["supported_output_languages"]
    assert "Persian" in body["supported_output_languages"]
    assert "DemoVoice" in body["supported_voices"]


def test_book_creation_options_records_token_safe_telemetry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    stub_context_provider._base_config.update(
        {
            "input_language": "Secret Source Language",
            "target_languages": ["Private Target", "Another Target"],
            "selected_voice": "PrivateVoice",
        }
    )
    logger = _RecordingLogger()

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    monkeypatch.setattr(create_book_router, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/books/options",
                headers={"X-User-Id": "office-ipad-user", "X-User-Role": "editor"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    rendered_logs = "\n".join(logger.messages)
    assert "Book creation options result=success" in rendered_logs
    assert "input_languages=" in rendered_logs
    assert "output_languages=" in rendered_logs
    assert "voices=" in rendered_logs
    assert "target_languages=2" in rendered_logs
    assert "office-ipad-user" not in rendered_logs
    assert "Secret Source Language" not in rendered_logs
    assert "Private Target" not in rendered_logs
    assert "PrivateVoice" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_book_options_route_duration_seconds",
        operation="get",
        result="success",
    )


def test_book_creation_options_exposes_cross_surface_job_default_overrides(tmp_path: Path) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    stub_context_provider._base_config.update(
        {
            "subtitle_worker_count": "12",
            "subtitle_batch_size": "22",
            "subtitle_translation_batch_size": "8",
            "subtitle_ass_font_size": "64",
            "subtitle_ass_emphasis_scale": "1.6",
            "youtube_dub_original_mix_percent": "25",
            "youtube_dub_flush_sentences": "18",
            "youtube_dub_translation_batch_size": "6",
            "youtube_dub_split_batches": False,
            "youtube_dub_stitch_batches": False,
            "youtube_dub_target_height": "720",
            "youtube_dub_preserve_aspect_ratio": "0",
            "add_images": "true",
            "image_prompt_pipeline": "visual-canon",
            "image_style_template": "comic panel",
            "image_prompt_context_sentences": "99",
            "image_width": "32",
            "image_height": "768",
            "target_languages": ["French", "Spanish", "french", "", 42],
        }
    )

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider

    client = TestClient(app)

    response = client.get(
        "/api/books/options",
        headers={"X-User-Id": "editor", "X-User-Role": "editor"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["defaults"]["output_language"] == "French"
    assert body["defaults"]["target_languages"] == ["French", "Spanish"]
    assert body["defaults"]["output_languages"] == ["French", "Spanish"]
    assert body["subtitle_defaults"] == {
        "worker_count": 12,
        "batch_size": 22,
        "translation_batch_size": 8,
        "ass_font_size": 64,
        "ass_emphasis_scale": 1.6,
    }
    assert body["youtube_dub_defaults"] == {
        "original_mix_percent": 25.0,
        "flush_sentences": 18,
        "translation_batch_size": 6,
        "split_batches": False,
        "stitch_batches": False,
        "target_height": 720,
        "preserve_aspect_ratio": False,
    }
    assert body["generated_source_defaults"] == {
        "add_images": True,
        "image_prompt_pipeline": "visual_canon",
        "image_style_template": "comics",
        "image_prompt_context_sentences": 50,
        "image_width": "64",
        "image_height": "768",
    }


def test_book_creation_options_requires_editor_role(tmp_path: Path) -> None:
    app = create_app()

    user = UserRecord(username="viewer", password_hash="", roles=["viewer"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider

    client = TestClient(app)

    response = client.get(
        "/api/books/options",
        headers={"X-User-Id": "viewer", "X-User-Role": "viewer"},
    )

    assert response.status_code == 403


def test_book_creation_options_records_forbidden_telemetry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    user = UserRecord(username="viewer", password_hash="", roles=["viewer"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)
    logger = _RecordingLogger()

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider
    monkeypatch.setattr(create_book_router, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/books/options",
                headers={"X-User-Id": "viewer-user", "X-User-Role": "viewer"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    rendered_logs = "\n".join(logger.messages)
    assert "Book creation options result=forbidden" in rendered_logs
    assert "viewer-user" not in rendered_logs
    assert "viewer" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_book_options_route_duration_seconds",
        operation="get",
        result="forbidden",
    )
