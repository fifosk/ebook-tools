from __future__ import annotations

from typing import Any, Dict, List, Tuple

from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_library_sync,
    get_request_user,
)

import pytest

pytestmark = pytest.mark.webapi


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)


class _StubLibrarySync:
    def __init__(
        self,
        payload: Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool],
        *,
        expected_job_id: str = "library-job",
    ) -> None:
        self._payload = payload
        self._expected_job_id = expected_job_id

    def get_item(self, job_id: str):
        return None  # Bypass access control check

    def get_media(
        self,
        job_id: str,
        summary: bool = False,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]:
        assert job_id == self._expected_job_id
        assert summary is False
        return self._payload


def test_get_library_media_includes_sentence_metadata() -> None:
    chunk_file = {
        "name": "chunk.html",
        "url": "https://example.invalid/chunk.html",
        "source": "completed",
    }
    media_map = {"text": [dict(chunk_file)]}
    chunk_records = [
        {
            "chunk_id": "chunk-001",
            "range_fragment": "0-50",
            "start_sentence": 1,
            "end_sentence": 2,
            "files": [dict(chunk_file)],
            "sentences": [
                {
                    "sentence_number": 1,
                    "original": {"text": "Hello world", "tokens": ["Hello", "world"]},
                    "translation": {"text": "Hola mundo", "tokens": ["Hola", "mundo"]},
                    "transliteration": {"text": "Hello world", "tokens": ["Hello", "world"]},
                    "timeline": [
                        {
                            "duration": 1.0,
                            "original_index": 2,
                            "translation_index": 2,
                            "transliteration_index": 2,
                        }
                    ],
                    "total_duration": 1.0,
                    "highlight_granularity": "word",
                    "counts": {"tokens": 2},
                }
            ],
            "metadata_path": "metadata/chunk_0000.json",
            "metadata_url": "/api/library/media/library-job/file/metadata/chunk_0000.json",
            "sentence_count": 1,
        }
    ]
    payload = (media_map, chunk_records, True)

    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync(payload)
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="test", user_role="admin"
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/library/media/library-job")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["chunks"], "Expected chunks to be returned"
    first_chunk = data["chunks"][0]
    assert first_chunk["sentences"], "Expected sentence metadata for Text Player"
    # Fields are serialized with camelCase aliases
    assert first_chunk["metadataPath"] == "metadata/chunk_0000.json"
    assert first_chunk["metadataUrl"].startswith("/api/library/media/library-job/file/")
    assert first_chunk["sentenceCount"] == 1
    sentence = first_chunk["sentences"][0]
    assert sentence["original"]["tokens"] == ["Hello", "world"]
    assert sentence["timeline"][0]["duration"] == 1.0


def test_get_library_media_records_token_safe_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = "sensitive-library-job"
    user_id = "sensitive-user-id"
    logger = _RecordingLogger()
    media_map = {
        "audio": [
            {
                "name": "secret-audio.mp3",
                "url": f"/api/library/media/{job_id}/file/media/secret-audio.mp3",
                "source": "completed",
            }
        ]
    }
    chunk_records = [
        {
            "chunk_id": "chunk-001",
            "files": [dict(media_map["audio"][0])],
            "sentence_count": 1,
        }
    ]
    payload = (media_map, chunk_records, True)

    app = create_app()
    app.dependency_overrides[get_library_sync] = lambda: _StubLibrarySync(
        payload,
        expected_job_id=job_id,
    )
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id=user_id,
        user_role="editor",
    )
    monkeypatch.setattr("modules.webapi.routers.library.LOGGER", logger)

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/library/media/{job_id}")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    rendered_logs = "\n".join(logger.messages)
    assert "Library media lookup" in rendered_logs
    assert "operation=media" in rendered_logs
    assert "result=success" in rendered_logs
    assert "summary=False" in rendered_logs
    assert "categories=1" in rendered_logs
    assert "chunks=1" in rendered_logs
    assert "files=1" in rendered_logs
    assert "complete=True" in rendered_logs
    assert job_id not in rendered_logs
    assert user_id not in rendered_logs
    assert "secret-audio.mp3" not in rendered_logs

    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_response.text)
    }
    metric = families["ebook_tools_library_route_duration_seconds"]
    assert any(
        sample.labels.get("operation") == "media"
        and sample.labels.get("result") == "success"
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )
