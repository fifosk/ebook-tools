from __future__ import annotations

from typing import Any, Dict, List, Tuple

from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.dependencies import get_library_sync


class _StubLibrarySync:
    def __init__(self, payload: Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]) -> None:
        self._payload = payload

    def get_media(
        self,
        job_id: str,
        summary: bool = False,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], bool]:
        assert job_id == "library-job"
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
    assert first_chunk["metadata_path"] == "metadata/chunk_0000.json"
    assert first_chunk["metadata_url"].startswith("/api/library/media/library-job/file/")
    assert first_chunk["sentence_count"] == 1
    sentence = first_chunk["sentences"][0]
    assert sentence["original"]["tokens"] == ["Hello", "world"]
    assert sentence["timeline"][0]["duration"] == 1.0
