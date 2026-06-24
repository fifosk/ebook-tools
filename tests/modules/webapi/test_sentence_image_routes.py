from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    RequestUserContext,
    get_file_locator,
    get_library_repository,
    get_pipeline_job_manager,
    get_request_user,
)
from modules.webapi.routes.media import images

pytestmark = pytest.mark.webapi


class _RecordingLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args: object, **_kwargs: object) -> None:
        self.messages.append(message % args if args else message)


class _FakeMetadataLoader:
    def __init__(self, _job_root: Path) -> None:
        pass

    def iter_chunks(self) -> list[dict[str, Any]]:
        return [
            {
                "chunk_id": "chunk-001",
                "range_fragment": "1-2",
                "start_sentence": 1,
                "end_sentence": 3,
                "metadata_path": "metadata/chunk_0001.json",
            }
        ]


async def _fake_load_sentence_image_info(
    *,
    sentence_number: int,
    job_root: Path,
) -> tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]:
    return (
        {
            "chunk_id": "chunk-001",
            "range_fragment": "1-2",
            "metadata_path": "metadata/chunk_0001.json",
        },
        {"sentences": []},
        {
            "sentence_number": sentence_number,
            "original": {"text": "A sentence with an image."},
            "image": {
                "path": "media/images/1-2/sentence_00001.png",
                "prompt": "safe prompt",
                "negative_prompt": "safe negative",
            },
        },
    )


def _build_app(tmp_path: Path):
    app = create_app()
    app.dependency_overrides[get_pipeline_job_manager] = lambda: object()
    app.dependency_overrides[get_file_locator] = lambda: FileLocator(storage_dir=tmp_path / "jobs")
    app.dependency_overrides[get_library_repository] = lambda: object()
    app.dependency_overrides[get_request_user] = lambda: RequestUserContext(
        user_id="sensitive-user-id",
        user_role="editor",
    )
    return app


def _assert_sentence_image_metric(metrics_text: str, operation: str) -> None:
    families = {
        family.name: family
        for family in text_string_to_metric_families(metrics_text)
    }
    metric = families["ebook_tools_media_route_duration_seconds"]
    assert any(
        sample.labels.get("operation") == operation
        and sample.labels.get("result") == "success"
        and sample.name.endswith("_count")
        and sample.value >= 1
        for sample in metric.samples
    )


def test_sentence_image_lookup_logs_token_safe_aggregate_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "sensitive-image-job"
    logger = _RecordingLogger()
    monkeypatch.setattr(images, "LOGGER", logger)
    monkeypatch.setattr(images, "_resolve_job_root", lambda **_kwargs: tmp_path)
    monkeypatch.setattr(images, "_load_sentence_image_info", _fake_load_sentence_image_info)
    monkeypatch.setattr(images, "_load_image_manifest", lambda _job_root: {})

    app = _build_app(tmp_path)
    try:
        with TestClient(app) as client:
            response = client.get(f"/pipelines/jobs/{job_id}/media/images/sentences/1")
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    rendered_logs = "\n".join(logger.messages)
    assert "Sentence image lookup" in rendered_logs
    assert "operation=sentence_image" in rendered_logs
    assert "result=success" in rendered_logs
    assert "count=1" in rendered_logs
    assert "missing=0" in rendered_logs
    assert job_id not in rendered_logs
    assert "sensitive-user-id" not in rendered_logs
    assert "sentence_00001.png" not in rendered_logs
    _assert_sentence_image_metric(metrics_response.text, "sentence_image")


def test_sentence_image_batch_lookup_logs_token_safe_aggregate_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "sensitive-image-batch-job"
    logger = _RecordingLogger()
    chunk_payload = {
        "sentences": [
            {
                "sentence_number": 1,
                "original": {"text": "First sentence."},
                "image": {"path": "media/images/1-2/sentence_00001.png"},
            }
        ]
    }
    monkeypatch.setattr(images, "LOGGER", logger)
    monkeypatch.setattr(images, "MetadataLoader", _FakeMetadataLoader)
    monkeypatch.setattr(images, "_resolve_job_root", lambda **_kwargs: tmp_path)
    monkeypatch.setattr(images, "_read_chunk_payload", lambda **_kwargs: chunk_payload)
    monkeypatch.setattr(images, "_load_image_manifest", lambda _job_root: {})

    app = _build_app(tmp_path)
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/pipelines/jobs/{job_id}/media/images/sentences/batch",
                params={"sentence_numbers": "1,2"},
            )
            metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job_id
    assert payload["missing"] == [2]
    rendered_logs = "\n".join(logger.messages)
    assert "Sentence image lookup" in rendered_logs
    assert "operation=sentence_image_batch" in rendered_logs
    assert "result=success" in rendered_logs
    assert "count=2" in rendered_logs
    assert "missing=1" in rendered_logs
    assert job_id not in rendered_logs
    assert "sensitive-user-id" not in rendered_logs
    assert "sentence_00001.png" not in rendered_logs
    _assert_sentence_image_metric(metrics_response.text, "sentence_image_batch")
