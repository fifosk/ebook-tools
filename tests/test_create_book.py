from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from modules import config_manager as cfg
from modules.services.job_manager.job import PipelineJob, PipelineJobStatus
from modules.services.pipeline_service import PipelineRequest
from modules.user_management.user_store_base import UserRecord
from modules.webapi.application import create_app
from modules.webapi.dependencies import (
    get_auth_service,
    get_pipeline_job_manager,
    get_pipeline_service,
    get_runtime_context_provider,
)
from modules.webapi.routes.books_routes import _list_ebook_files
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
                "inputs": {
                    "input_file": "generated.epub",
                    "base_output_file": "generated",
                    "input_language": "English",
                    "target_languages": ["French"],
                }
            },
        }
    )

    assert payload.generator.source_book_title == "Inferno"
    assert payload.generator.source_book_author == "Dan Brown"
    assert payload.generator.source_book_genre == "Conspiracy thriller"
    assert payload.generator.source_book_summary == "A symbologist follows clues across Europe."


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
                "inputs": {
                    "input_file": "generated.epub",
                    "base_output_file": "generated",
                    "input_language": "English",
                    "target_languages": ["French"],
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
