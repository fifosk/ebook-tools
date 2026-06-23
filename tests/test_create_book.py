from __future__ import annotations

import os
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
from modules.webapi.routes.books_routes import _list_ebook_files

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
    assert body["status"] == "prepared"
    assert body["metadata"]["book_title"] == "Drops"
    assert body["metadata"]["generated_sentences"] == ["One.", "Two."]
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
    assert body["generated_source_defaults"]["image_style_template"] == "wireframe"
    assert "English" in body["supported_input_languages"]
    assert "Hindi" in body["supported_input_languages"]
    assert "Chinese (Traditional)" in body["supported_output_languages"]
    assert "Persian" in body["supported_output_languages"]
    assert "DemoVoice" in body["supported_voices"]


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
