import json
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

import modules.services.subtitle_service as subtitle_service_module
import modules.webapi.routers.subtitles as subtitles_router_module
from modules.webapi.dependencies import RequestUserContext
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_request_user, get_subtitle_service
from modules.webapi.routers.subtitles import (
    _subtitle_source_entry,
    _subtitle_source_sort_key,
    delete_subtitle_source,
    list_subtitle_sources,
    parse_end_time,
    parse_time_offset,
)
from modules.webapi.schemas import SubtitleDeleteRequest, SubtitleSourceEntry
from modules.services.subtitle_service import SubtitleService

pytestmark = pytest.mark.webapi


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


def test_parse_end_time_relative_minutes() -> None:
    start_seconds = parse_time_offset("00:01")
    end_seconds = parse_end_time("+5", start_seconds)
    assert end_seconds == pytest.approx(start_seconds + 300.0)


def test_parse_end_time_accepts_absolute() -> None:
    start_seconds = parse_time_offset("00:00")
    end_seconds = parse_end_time("03:00", start_seconds)
    assert end_seconds == pytest.approx(180.0)


def test_parse_end_time_relative_timecode() -> None:
    start_seconds = parse_time_offset("00:10")
    end_seconds = parse_end_time("+01:30", start_seconds)
    assert end_seconds == pytest.approx(start_seconds + 90.0)


def test_parse_end_time_blank_returns_none() -> None:
    assert parse_end_time("", 0.0) is None
    assert parse_end_time(None, 0.0) is None


def test_parse_end_time_requires_greater_than_start() -> None:
    with pytest.raises(HTTPException):
        parse_end_time("00:00", 5.0)


def test_parse_end_time_invalid_relative_raises() -> None:
    with pytest.raises(HTTPException):
        parse_end_time("+abc", 0.0)


def test_subtitle_source_sort_prefers_latest_srt_vtt_before_ass() -> None:
    entries = [
        SubtitleSourceEntry(
            name="newer.ass",
            path="/subs/newer.ass",
            format="ass",
            modified_at=datetime(2026, 6, 24, 10, 0, 0),
        ),
        SubtitleSourceEntry(
            name="older.srt",
            path="/subs/older.srt",
            format="srt",
            modified_at=datetime(2026, 1, 1, 10, 0, 0),
        ),
        SubtitleSourceEntry(
            name="newer.vtt",
            path="/subs/newer.vtt",
            format="vtt",
            modified_at=datetime(2026, 6, 24, 9, 0, 0),
        ),
        SubtitleSourceEntry(
            name="same-time-a.srt",
            path="/subs/a-same.srt",
            format="srt",
            modified_at=datetime(2026, 6, 24, 9, 0, 0),
        ),
    ]

    assert [entry.path for entry in sorted(entries, key=_subtitle_source_sort_key)] == [
        "/subs/a-same.srt",
        "/subs/newer.vtt",
        "/subs/older.srt",
        "/subs/newer.ass",
    ]


def test_subtitle_source_entry_skips_vanished_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "episode.en.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    original_stat = Path.stat

    def fake_stat(path: Path, *args, **kwargs):
        if path == source:
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    assert _subtitle_source_entry(source) is None


def test_list_subtitle_sources_skips_stale_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stable = tmp_path / "stable.en.srt"
    vanished = tmp_path / "vanished.en.srt"
    stable.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    vanished.write_text("1\n00:00:00,000 --> 00:00:01,000\nBye\n", encoding="utf-8")

    class _Service:
        def list_sources(self, base_path=None):
            return [vanished, stable]

    original_stat = Path.stat

    def fake_stat(path: Path, *args, **kwargs):
        if path == vanished:
            raise FileNotFoundError(path)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    response = list_subtitle_sources(
        service=_Service(),
        request_user=RequestUserContext(user_id="editor", user_role="editor"),
    )

    assert [entry.path for entry in response.sources] == [stable.as_posix()]


def test_subtitle_service_list_sources_tolerates_scan_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=tmp_path,
    )
    resolved = tmp_path.resolve()
    original_walk = os.walk

    def fake_walk(path: Path, *args, **kwargs):
        if Path(path) == resolved:
            onerror = kwargs.get("onerror")
            if onerror is not None:
                onerror(OSError("transient NAS remount"))
            if False:
                yield None
            return
        yield from original_walk(path, *args, **kwargs)

    monkeypatch.setattr("modules.services.source_discovery.os.walk", fake_walk)

    assert service.list_sources() == []


def test_subtitle_service_list_sources_uses_safe_root_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=tmp_path,
    )
    resolved = tmp_path.resolve()

    def fake_safe_stat(path: Path):
        if path == resolved:
            return None
        return path.stat()

    monkeypatch.setattr(subtitle_service_module, "safe_stat", fake_safe_stat)

    assert service.list_sources() == []


def test_subtitle_service_list_sources_recurses_visible_nas_folders(tmp_path: Path) -> None:
    nested = tmp_path / "Shows" / "Current"
    hidden = tmp_path / ".scratch"
    nested.mkdir(parents=True)
    hidden.mkdir()
    root_source = tmp_path / "older.en.srt"
    nested_source = nested / "latest.EN.VTT"
    hidden_source = hidden / "hidden.en.srt"
    ignored = nested / "notes.txt"
    root_source.write_text("1\n00:00:00,000 --> 00:00:01,000\nOlder\n", encoding="utf-8")
    nested_source.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nLatest\n", encoding="utf-8")
    hidden_source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHidden\n", encoding="utf-8")
    ignored.write_text("not subtitles", encoding="utf-8")
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=tmp_path,
    )

    assert set(service.list_sources()) == {root_source.resolve(), nested_source.resolve()}


def test_subtitle_service_explicit_source_root_stat_failure_reports_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=tmp_path / "default",
    )
    explicit_root = tmp_path / "Explicit"
    explicit_root.mkdir()
    resolved = explicit_root.resolve()

    def fake_safe_stat(path: Path):
        if path == resolved:
            return None
        return path.stat()

    monkeypatch.setattr(subtitle_service_module, "safe_stat", fake_safe_stat)

    with pytest.raises(FileNotFoundError):
        service.list_sources(explicit_root)


def test_list_subtitle_sources_returns_nested_sources_with_preferred_sort(tmp_path: Path) -> None:
    nested = tmp_path / "Series"
    nested.mkdir()
    newer_ass = nested / "newer.ass"
    older_srt = tmp_path / "older.srt"
    newer_vtt = nested / "newer.vtt"
    newer_ass.write_text("[Script Info]\n", encoding="utf-8")
    older_srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nOlder\n", encoding="utf-8")
    newer_vtt.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nNewer\n", encoding="utf-8")
    newer_time = 1_700_000_500
    older_time = 1_700_000_000
    newer_ass.touch()
    older_srt.touch()
    newer_vtt.touch()
    os.utime(newer_ass, (newer_time, newer_time))
    os.utime(newer_vtt, (newer_time, newer_time))
    os.utime(older_srt, (older_time, older_time))
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=tmp_path,
    )

    response = list_subtitle_sources(
        service=service,
        request_user=RequestUserContext(user_id="editor", user_role="editor"),
    )

    assert [entry.path for entry in response.sources] == [
        newer_vtt.resolve().as_posix(),
        older_srt.resolve().as_posix(),
        newer_ass.resolve().as_posix(),
    ]


def test_subtitle_source_picker_records_safe_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    secret_dir = tmp_path / "Secret Show"
    secret_dir.mkdir()
    source = secret_dir / "episode.en.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    logger = _RecordingLogger()

    class _Service:
        default_source_dir = tmp_path

        def list_sources(self, base_path=None):
            assert base_path == secret_dir
            return [source]

    app.dependency_overrides[get_subtitle_service] = lambda: _Service()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(subtitles_router_module, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/subtitles/sources",
                params={"directory": secret_dir.as_posix()},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["sources"][0]["path"] == source.as_posix()

    rendered_logs = "\n".join(logger.messages)
    assert "Subtitle source picker result=success sources=1 directory_override=true" in rendered_logs
    assert "Secret Show" not in rendered_logs
    assert "episode.en.srt" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs

    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="subtitle_sources",
        result="success",
    )


@pytest.mark.parametrize(
    ("exception", "status_code", "result", "detail"),
    [
        (
            PermissionError("forbidden /Volumes/Data/Secret Show"),
            403,
            "forbidden",
            subtitles_router_module.SUBTITLE_SOURCE_FORBIDDEN_MESSAGE,
        ),
        (
            FileNotFoundError("missing /Volumes/Data/Secret Show"),
            404,
            "not_found",
            subtitles_router_module.SUBTITLE_SOURCE_NOT_FOUND_MESSAGE,
        ),
        (
            RuntimeError("scan failed at /Volumes/Data/Secret Show/episode.srt"),
            503,
            "error",
            subtitles_router_module.SUBTITLE_SOURCE_UNAVAILABLE_MESSAGE,
        ),
    ],
)
def test_subtitle_source_picker_failures_use_generic_token_safe_responses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    status_code: int,
    result: str,
    detail: str,
) -> None:
    app = create_app()
    secret_dir = tmp_path / "Secret Show"
    logger = _RecordingLogger()

    class _Service:
        default_source_dir = tmp_path

        def list_sources(self, base_path=None):
            assert base_path == secret_dir
            raise exception

    app.dependency_overrides[get_subtitle_service] = lambda: _Service()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(subtitles_router_module, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/subtitles/sources",
                params={"directory": secret_dir.as_posix()},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert "Secret Show" not in response.text
    assert "/Volumes/Data" not in response.text
    assert "episode.srt" not in response.text
    rendered_logs = "\n".join(logger.messages)
    assert f"Subtitle source picker result={result}" in rendered_logs
    assert "result=success" not in rendered_logs
    assert "Secret Show" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs
    assert "episode.srt" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="subtitle_sources",
        result=result,
    )


def test_subtitle_source_picker_response_validation_uses_generic_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    secret_dir = tmp_path / "Secret Show"
    secret_dir.mkdir()
    source = secret_dir / "episode.en.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    logger = _RecordingLogger()

    class _Service:
        default_source_dir = tmp_path

        def list_sources(self, base_path=None):
            return [source]

    app.dependency_overrides[get_subtitle_service] = lambda: _Service()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(subtitles_router_module, "logger", logger)
    monkeypatch.setattr(
        subtitles_router_module,
        "_subtitle_source_entry",
        lambda _path: object(),
    )

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/subtitles/sources",
                params={"directory": secret_dir.as_posix()},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": subtitles_router_module.SUBTITLE_SOURCE_UNAVAILABLE_MESSAGE
    }
    assert "Secret Show" not in response.text
    assert "episode.en.srt" not in response.text
    rendered_logs = "\n".join(logger.messages)
    assert "Subtitle source picker result=error" in rendered_logs
    assert "result=success" not in rendered_logs
    assert "Secret Show" not in rendered_logs
    assert "episode.en.srt" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="subtitle_sources",
        result="error",
    )


def test_subtitle_models_records_token_safe_success_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(subtitles_router_module, "logger", logger)
    monkeypatch.setattr(
        subtitles_router_module,
        "list_available_llm_models",
        lambda: ["ollama_cloud:secret-model", "lmstudio_local:private-model"],
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/subtitles/models")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "models": ["ollama_cloud:secret-model", "lmstudio_local:private-model"]
    }
    rendered_logs = "\n".join(logger.messages)
    assert "Subtitle model inventory result=success" in rendered_logs
    assert "models=2" in rendered_logs
    assert "office-ipad-user" not in rendered_logs
    assert "secret-model" not in rendered_logs
    assert "private-model" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_llm_model_route_duration_seconds",
        operation="subtitle_models",
        result="success",
    )


def test_subtitle_models_records_token_safe_forbidden_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(subtitles_router_module, "logger", logger)
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="guest-user",
        user_role="viewer",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/subtitles/models")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    rendered_logs = "\n".join(logger.messages)
    assert "Subtitle model inventory result=forbidden" in rendered_logs
    assert "guest-user" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_llm_model_route_duration_seconds",
        operation="subtitle_models",
        result="forbidden",
    )


def test_subtitle_models_records_token_safe_error_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(subtitles_router_module, "logger", logger)

    def fail_model_listing() -> list[str]:
        raise RuntimeError("secret model backend at /Volumes/Data/private-models failed")

    monkeypatch.setattr(
        subtitles_router_module,
        "list_available_llm_models",
        fail_model_listing,
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="subtitle-editor",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/subtitles/models")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Unable to query LLM model list."}
    rendered_logs = "\n".join(logger.messages)
    assert "Subtitle model inventory result=error" in rendered_logs
    assert "subtitle-editor" not in rendered_logs
    assert "private-models" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_llm_model_route_duration_seconds",
        operation="subtitle_models",
        result="error",
    )


def test_subtitle_models_response_validation_records_token_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    logger = _RecordingLogger()
    monkeypatch.setattr(subtitles_router_module, "logger", logger)
    monkeypatch.setattr(
        subtitles_router_module,
        "list_available_llm_models",
        lambda: [{"id": "secret-model", "path": "/Volumes/Data/private-models"}],
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="subtitle-editor",
        user_role="admin",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/subtitles/models")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "detail": subtitles_router_module.SUBTITLE_MODEL_UNAVAILABLE_MESSAGE
    }
    assert "secret-model" not in response.text
    assert "/Volumes/Data" not in response.text
    rendered_logs = "\n".join(logger.messages)
    assert "Subtitle model inventory result=error" in rendered_logs
    assert "result=success" not in rendered_logs
    assert "subtitle-editor" not in rendered_logs
    assert "secret-model" not in rendered_logs
    assert "/Volumes/Data" not in rendered_logs
    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_llm_model_route_duration_seconds",
        operation="subtitle_models",
        result="error",
    )


def test_subtitle_job_submission_records_safe_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    secret_dir = tmp_path / "Secret Show"
    secret_dir.mkdir()
    source = secret_dir / "episode.en.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    logger = _RecordingLogger()

    class _Service:
        default_source_dir = tmp_path

        def __init__(self) -> None:
            self.submissions = []

        def enqueue(self, submission, *, user_id=None, user_role=None):
            self.submissions.append((submission, user_id, user_role))
            return SimpleNamespace(
                job_id="subtitle-job-1",
                status="pending",
                created_at=datetime(2026, 6, 24, 12, 0, 0),
                job_type="subtitle",
            )

    service = _Service()
    app.dependency_overrides[get_subtitle_service] = lambda: service
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(subtitles_router_module, "logger", logger)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/jobs",
                data={
                    "input_language": "English",
                    "target_language": "Spanish",
                    "source_path": source.as_posix(),
                    "output_format": "srt",
                    "media_metadata_json": json.dumps(
                        {
                            "title": "Private Title",
                            "source_kind": " Manual_Downloads ",
                            "source_provider": " Newznab_Torznab ",
                            "acquisition_provider": " Youtube_Search ",
                            "acquisition_candidate_id": "Youtube_Search:DemoVideo",
                            "media_metadata_lookup": {
                                "provider": " OpenLibrary ",
                                "candidate_id": "OpenLibrary:/works/OL45883W",
                            },
                        }
                    ),
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["job_id"] == "subtitle-job-1"
    assert service.submissions[0][1:] == ("office-ipad-user", "editor")
    assert service.submissions[0][0].media_metadata == {
        "title": "Private Title",
        "source_kind": "manual_downloads",
        "source_provider": "newznab_torznab",
        "acquisition_provider": "youtube_search",
        "acquisition_candidate_id": "Youtube_Search:DemoVideo",
        "media_metadata_lookup": {
            "provider": "openlibrary",
            "candidate_id": "OpenLibrary:/works/OL45883W",
        },
    }

    rendered_logs = "\n".join(logger.messages)
    assert "Create submission operation=subtitle_job result=success" in rendered_logs
    assert "upload=false source_path_present=true" in rendered_logs
    assert "Secret Show" not in rendered_logs
    assert "episode.en.srt" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs
    assert "English" not in rendered_logs
    assert "Spanish" not in rendered_logs
    assert "subtitle-job-1" not in rendered_logs

    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_create_submission_route_duration_seconds",
        operation="subtitle_job",
        result="success",
    )


def test_subtitle_job_submission_uses_safe_stat_for_selected_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    source = tmp_path / "episode.en.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    logger = _RecordingLogger()

    class _Service:
        default_source_dir = tmp_path

        def enqueue(self, submission, *, user_id=None, user_role=None):
            raise AssertionError("vanished selected sources must not enqueue")

    def fake_safe_stat(path: Path):
        if path == source:
            return None
        return path.stat()

    app.dependency_overrides[get_subtitle_service] = lambda: _Service()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="office-ipad-user",
        user_role="editor",
    )
    monkeypatch.setattr(subtitles_router_module, "logger", logger)
    monkeypatch.setattr(subtitles_router_module, "safe_stat", fake_safe_stat)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/subtitles/jobs",
                data={
                    "input_language": "English",
                    "target_language": "Spanish",
                    "source_path": source.as_posix(),
                    "output_format": "srt",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    rendered_logs = "\n".join(logger.messages)
    assert "Create submission operation=subtitle_job result=not_found" in rendered_logs
    assert "upload=false source_path_present=true" in rendered_logs
    assert "episode.en.srt" not in rendered_logs


def test_subtitle_service_delete_source_reports_missing_in_scope_file(tmp_path: Path) -> None:
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=tmp_path,
    )
    missing = tmp_path / "vanished.en.srt"

    result = service.delete_source(missing)

    assert result.removed == []
    assert result.missing == [missing.resolve()]


def test_subtitle_service_delete_source_rejects_missing_file_outside_base(tmp_path: Path) -> None:
    base = tmp_path / "base"
    outside = tmp_path / "outside"
    base.mkdir()
    outside.mkdir()
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=base,
    )

    with pytest.raises(PermissionError):
        service.delete_source(outside / "vanished.en.srt")


def test_delete_subtitle_source_reports_missing_in_scope_file(tmp_path: Path) -> None:
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=tmp_path,
    )
    missing = tmp_path / "vanished.en.srt"

    response = delete_subtitle_source(
        payload=SubtitleDeleteRequest(
            subtitle_path=missing.as_posix(),
            base_dir=tmp_path.as_posix(),
        ),
        service=service,
        request_user=RequestUserContext(user_id="editor", user_role="editor"),
    )

    assert response.subtitle_path == missing.as_posix()
    assert response.base_dir == tmp_path.as_posix()
    assert response.removed == []
    assert response.missing == [missing.resolve().as_posix()]


def test_delete_subtitle_source_rejects_missing_file_outside_base(tmp_path: Path) -> None:
    base = tmp_path / "base"
    outside = tmp_path / "outside"
    base.mkdir()
    outside.mkdir()
    service = SubtitleService(
        job_manager=object(),
        locator=object(),
        default_source_dir=base,
    )

    with pytest.raises(HTTPException) as exc_info:
        delete_subtitle_source(
            payload=SubtitleDeleteRequest(
                subtitle_path=(outside / "vanished.en.srt").as_posix(),
                base_dir=base.as_posix(),
            ),
            service=service,
            request_user=RequestUserContext(user_id="editor", user_role="editor"),
        )

    assert exc_info.value.status_code == 403


def test_delete_subtitle_source_unexpected_errors_do_not_log_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_dir = tmp_path / "Secret Show"
    secret_dir.mkdir()
    source = secret_dir / "episode.en.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
    logger = _RecordingLogger()

    class _Service:
        default_source_dir = tmp_path

        def delete_source(self, subtitle_path: Path, *, base_dir: Path | None = None):
            raise RuntimeError(f"cannot remove {subtitle_path}")

    monkeypatch.setattr(subtitles_router_module, "logger", logger)

    with pytest.raises(HTTPException) as exc_info:
        delete_subtitle_source(
            payload=SubtitleDeleteRequest(
                subtitle_path=source.as_posix(),
                base_dir=tmp_path.as_posix(),
            ),
            service=_Service(),
            request_user=RequestUserContext(user_id="office-ipad-user", user_role="editor"),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Unable to delete subtitle source."

    rendered_logs = "\n".join(logger.messages)
    assert "Subtitle source delete result=error" in rendered_logs
    assert "Secret Show" not in rendered_logs
    assert "episode.en.srt" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs
