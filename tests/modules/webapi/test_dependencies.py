"""Tests for media service configuration wiring in web API dependencies."""

from __future__ import annotations

import os

import pytest
from fastapi import HTTPException

from modules.audio.api import AudioService
from modules.user_management import AuthService, LocalUserStore, SessionManager
from modules.webapi.auth_utils import (
    extract_request_session_token,
    extract_session_token,
    require_admin_user,
)
from modules.webapi.dependencies import (
    configure_media_services,
    get_audio_service,
    get_request_user,
)

pytestmark = pytest.mark.webapi


@pytest.fixture(autouse=True)
def _reset_media_services(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test runs with a clean service cache and environment."""

    for key in (
        "EBOOK_AUDIO_BACKEND",
        "EBOOK_TTS_BACKEND",
        "EBOOK_AUDIO_EXECUTABLE",
        "EBOOK_TTS_EXECUTABLE",
        "EBOOK_SAY_PATH",
        "EBOOK_AUDIO_SAY_PATH",
        "EBOOK_AUDIO_API_BASE_URL",
        "EBOOK_AUDIO_API_TIMEOUT_SECONDS",
        "EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
    configure_media_services(config=None)


def test_configure_media_services_falls_back_to_defaults() -> None:
    """Services constructed without overrides should still be usable."""

    configure_media_services(config={})

    audio_service = get_audio_service()

    assert isinstance(audio_service, AudioService)
    assert audio_service._backend_name_override is None
    assert audio_service._executable_override is None


def test_audio_service_honours_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables take precedence over bootstrap configuration."""

    monkeypatch.setenv("EBOOK_AUDIO_BACKEND", "macos_say")
    monkeypatch.setenv("EBOOK_AUDIO_EXECUTABLE", "/usr/bin/say")

    configure_media_services(config={})

    audio_service = get_audio_service()

    assert audio_service._backend_name_override == "macos_say"
    assert audio_service._executable_override == "/usr/bin/say"


def test_configure_media_services_sets_audio_api_environment() -> None:
    """Audio API settings should be exported for downstream synthesizers."""

    configure_media_services(
        config={
            "audio_api_base_url": "https://audio.example",
            "audio_api_timeout_seconds": 42,
            "audio_api_poll_interval_seconds": 2.5,
        }
    )

    assert os.environ["EBOOK_AUDIO_API_BASE_URL"] == "https://audio.example"
    assert os.environ["EBOOK_AUDIO_API_TIMEOUT_SECONDS"] == "42.0"
    assert os.environ["EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS"] == "2.5"


@pytest.mark.parametrize(
    ("authorization", "expected"),
    [
        (None, None),
        ("", None),
        ("Bearer session-token", "session-token"),
        ("bearer session-token", "session-token"),
        ("  Bearer   session-token  ", "session-token"),
        ("legacy-session-token", "legacy-session-token"),
        ("Basic session-token", None),
        ("Token session-token", None),
    ],
)
def test_extract_session_token_accepts_only_bearer_or_bare_tokens(
    authorization: str | None,
    expected: str | None,
) -> None:
    assert extract_session_token(authorization) == expected


@pytest.mark.parametrize(
    ("authorization", "access_token", "expected"),
    [
        ("Bearer header-token", "query-token", "header-token"),
        (None, "Bearer query-token", "query-token"),
        (None, "query-token", "query-token"),
        (None, "Basic query-token", None),
        ("Basic header-token", "Bearer query-token", "query-token"),
    ],
)
def test_extract_request_session_token_supports_query_fallback(
    authorization: str | None,
    access_token: str | None,
    expected: str | None,
) -> None:
    assert extract_request_session_token(authorization, access_token) == expected


def test_get_request_user_accepts_bearer_and_query_tokens(tmp_path) -> None:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("alice", "secret", roles=["editor"])
    token = auth_service.session_manager.create_session("alice")

    header_user = get_request_user(
        authorization=f"Bearer {token}",
        header_user_id=None,
        header_user_role=None,
        access_token=None,
        auth_service=auth_service,
    )
    query_user = get_request_user(
        authorization=None,
        header_user_id=None,
        header_user_role=None,
        access_token=token,
        auth_service=auth_service,
    )
    query_bearer_user = get_request_user(
        authorization=None,
        header_user_id=None,
        header_user_role=None,
        access_token=f"Bearer {token}",
        auth_service=auth_service,
    )

    assert header_user.user_id == "alice"
    assert header_user.user_role == "editor"
    assert query_user.user_id == "alice"
    assert query_user.user_role == "editor"
    assert query_bearer_user.user_id == "alice"
    assert query_bearer_user.user_role == "editor"


def test_get_request_user_rejects_malformed_query_token_scheme(tmp_path) -> None:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("alice", "secret", roles=["editor"])
    token = auth_service.session_manager.create_session("alice")

    request_user = get_request_user(
        authorization=None,
        header_user_id=None,
        header_user_role=None,
        access_token=f"Basic {token}",
        auth_service=auth_service,
    )

    assert request_user.user_id is None
    assert request_user.user_role is None


def test_get_request_user_rejects_malformed_authorization_scheme(tmp_path) -> None:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("alice", "secret", roles=["editor"])
    token = auth_service.session_manager.create_session("alice")

    request_user = get_request_user(
        authorization=f"Basic {token}",
        header_user_id=None,
        header_user_role=None,
        access_token=None,
        auth_service=auth_service,
    )

    assert request_user.user_id is None
    assert request_user.user_role is None


def test_require_admin_user_returns_token_and_record(tmp_path) -> None:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("admin", "secret", roles=["admin"])
    token = auth_service.session_manager.create_session("admin")

    resolved_token, user = require_admin_user(f"Bearer {token}", auth_service)

    assert resolved_token == token
    assert user.username == "admin"


@pytest.mark.parametrize(
    ("authorization", "expected_detail"),
    [
        (None, "Missing session token"),
        ("Basic invalid", "Missing session token"),
        ("Bearer invalid", "Invalid session token"),
    ],
)
def test_require_admin_user_rejects_missing_or_invalid_tokens(
    tmp_path,
    authorization: str | None,
    expected_detail: str,
) -> None:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )

    with pytest.raises(HTTPException) as exc_info:
        require_admin_user(authorization, auth_service)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == expected_detail


def test_require_admin_user_rejects_non_admin_roles(tmp_path) -> None:
    auth_service = AuthService(
        LocalUserStore(storage_path=tmp_path / "users.json"),
        SessionManager(session_file=tmp_path / "sessions.json"),
    )
    auth_service.user_store.create_user("reader", "secret", roles=["viewer"])
    token = auth_service.session_manager.create_session("reader")

    with pytest.raises(HTTPException) as exc_info:
        require_admin_user(f"Bearer {token}", auth_service)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Administrator role required"
