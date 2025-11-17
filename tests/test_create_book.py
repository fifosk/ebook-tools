from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from modules import config_manager as cfg
from modules.services.pipeline_service import PipelineRequest
from modules.user_management.user_store_base import UserRecord
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_auth_service,
    get_pipeline_service,
    get_runtime_context_provider,
)


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
            "generate_video": False,
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


def test_create_book_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()

    user = UserRecord(username="editor", password_hash="", roles=["editor"], metadata={})
    stub_auth = _StubAuthService(user)
    stub_pipeline = _StubPipelineService()
    stub_context_provider = _StubRuntimeContextProvider(tmp_path)

    app.dependency_overrides[get_auth_service] = lambda: stub_auth
    app.dependency_overrides[get_pipeline_service] = lambda: stub_pipeline
    app.dependency_overrides[get_runtime_context_provider] = lambda: stub_context_provider

    monkeypatch.setattr(
        "modules.webapi.routers.create_book._generate_sentences",
        lambda *, count, input_language, topic, target_language: ["One.", "Two."][:count],
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
    }

    response = client.post(
        "/api/books/create",
        json=payload,
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["metadata"]["book_title"] == "Drops"
    assert body["metadata"]["generated_sentences"] == ["One.", "Two."]
    assert body["messages"]
    assert any("Seed EPUB created" in message for message in body["messages"])
    assert body["warnings"] == []
    assert isinstance(body["epub_path"], str) and body["epub_path"].endswith(".epub")
    assert body["sentences_preview"] == ["One.", "Two."]

    assert stub_pipeline.submissions
    submission = stub_pipeline.submissions[0]
    request = submission["request"]
    assert isinstance(request, PipelineRequest)
    assert submission["user_id"] == "editor"
    assert submission["user_role"] == "editor"

    input_file = Path(request.inputs.input_file)
    assert input_file.exists()
    assert input_file.suffix == ".epub"
    assert request.inputs.target_languages == ["French"]
    metadata_snapshot = request.inputs.book_metadata.as_dict()
    creation_summary = metadata_snapshot.get("creation_summary")
    assert isinstance(creation_summary, dict)
    assert creation_summary.get("epub_path", "").endswith(".epub")
    assert creation_summary.get("messages")
    assert creation_summary.get("sentences_preview") == ["One.", "Two."]
