from __future__ import annotations

import pytest

from modules.services import subtitle_metadata_service
from modules.services.subtitle_metadata_service import SubtitleMetadataService
from modules.services import youtube_video_metadata_service
from modules.services.youtube_video_metadata_service import YoutubeVideoMetadataService
from modules.services import media_metadata_service
from modules.services.media_metadata_service import MediaMetadataService


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)


class _FailingPipelineFactory:
    def __call__(self, *, cache_enabled: bool = True):
        raise RuntimeError("backend cache failure for /Volumes/Data/NAS923/private-source")


def _assert_logs_token_safe(logs: str, *secrets: str) -> None:
    assert "metadata cache could not be cleared" in logs
    assert "backend cache failure" not in logs
    assert "/Volumes/Data" not in logs
    assert "NAS923" not in logs
    for secret in secrets:
        assert secret not in logs


def test_tv_metadata_cache_clear_logs_token_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_logger = _ListLogger()
    monkeypatch.setattr(subtitle_metadata_service, "logger", capture_logger)
    monkeypatch.setattr(subtitle_metadata_service, "create_pipeline", _FailingPipelineFactory())

    service = SubtitleMetadataService(job_manager=None)
    result = service.clear_metadata_cache_for_query(
        "/Volumes/Data/NAS923/Shows/Secret.Show.S01E02.srt"
    )

    assert result["cleared"] == 0
    assert result["query"]["source_name"] == "Secret.Show.S01E02.srt"
    logs = "\n".join(capture_logger.messages)
    _assert_logs_token_safe(logs, "Secret.Show.S01E02.srt")


def test_youtube_metadata_cache_clear_logs_token_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_logger = _ListLogger()
    monkeypatch.setattr(youtube_video_metadata_service, "logger", capture_logger)
    monkeypatch.setattr(youtube_video_metadata_service, "create_pipeline", _FailingPipelineFactory())

    service = YoutubeVideoMetadataService(job_manager=None)
    result = service.clear_metadata_cache_for_query(
        "/Volumes/Data/NAS923/Videos/private-video-[abcDEF12345].mkv"
    )

    assert result["cleared"] == 0
    assert result["query"]["source_name"] == "private-video-[abcDEF12345].mkv"
    logs = "\n".join(capture_logger.messages)
    _assert_logs_token_safe(logs, "private-video", "abcDEF12345")


def test_book_metadata_cache_clear_logs_token_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_logger = _ListLogger()
    monkeypatch.setattr(media_metadata_service, "logger", capture_logger)
    monkeypatch.setattr(MediaMetadataService, "_get_google_books_api_key", staticmethod(lambda: None))
    monkeypatch.setattr(media_metadata_service, "create_pipeline", _FailingPipelineFactory())

    service = MediaMetadataService(job_manager=None, google_books_api_key="")
    result = service.clear_metadata_cache_for_query(
        "/Volumes/Data/NAS923/Books/Secret Dan Brown.epub"
    )

    assert result["cleared"] == 0
    assert result["query"]["title"] == "Secret Dan Brown"
    logs = "\n".join(capture_logger.messages)
    _assert_logs_token_safe(logs, "Secret Dan Brown.epub", "Secret Dan Brown")


def test_book_metadata_lookup_fallback_logs_token_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture_logger = _ListLogger()
    monkeypatch.setattr(media_metadata_service, "logger", capture_logger)
    monkeypatch.setattr(MediaMetadataService, "_get_google_books_api_key", staticmethod(lambda: None))
    monkeypatch.setattr(media_metadata_service, "create_pipeline", _FailingPipelineFactory())

    service = MediaMetadataService(job_manager=None, google_books_api_key="")
    result = service.lookup_openlibrary_metadata_for_query(
        "/Volumes/Data/NAS923/Books/Secret Dan Brown.epub"
    )

    assert result["source_name"] == "Secret Dan Brown.epub"
    assert result["media_metadata_lookup"]["error"] == "No metadata found from any source"
    logs = "\n".join(capture_logger.messages)
    assert "Book metadata pipeline lookup failed" in logs
    assert "backend cache failure" not in logs
    assert "/Volumes/Data" not in logs
    assert "NAS923" not in logs
    assert "Secret Dan Brown" not in logs
