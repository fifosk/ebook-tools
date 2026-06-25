import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.webapi.dependencies import RequestUserContext
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_request_user, get_subtitle_service
import modules.webapi.routers.subtitles as subtitles_router_module
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
    assert "Subtitle source picker result=success sources=1 directory_override=True" in rendered_logs
    assert "Secret Show" not in rendered_logs
    assert "episode.en.srt" not in rendered_logs
    assert "office-ipad-user" not in rendered_logs

    assert _has_metric_count(
        metrics_response.text,
        "ebook_tools_source_picker_route_duration_seconds",
        operation="subtitle_sources",
        result="success",
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
                },
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["job_id"] == "subtitle-job-1"
    assert service.submissions[0][1:] == ("office-ipad-user", "editor")

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
