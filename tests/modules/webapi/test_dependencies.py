"""Tests for media service configuration wiring in web API dependencies."""

from __future__ import annotations

import os

import pytest

from modules.audio.api import AudioService
from modules.webapi.dependencies import (
    configure_media_services,
    get_audio_service,
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
