"""Tests for `create_client` routing across the two LM Studio destinations."""

from __future__ import annotations

import pytest

from modules.llm_client import create_client


pytestmark = pytest.mark.services


def test_macstudio_identifier_routes_to_macstudio_url(monkeypatch):
    """``lmstudio_macstudio:foo`` must dispatch against the Mac Studio URL."""
    monkeypatch.setattr(
        "modules.llm_client.cfg.get_lmstudio_macstudio_url",
        lambda: "http://192.168.1.9:1234/v1/chat/completions",
    )
    monkeypatch.setattr(
        "modules.llm_client.cfg.get_lmstudio_macbook_url",
        lambda: "http://localhost:1234/v1/chat/completions",
    )

    client = create_client(model="lmstudio_macstudio:google/gemma-4-31b")
    assert client.settings.llm_source == "lmstudio"
    assert client.settings.api_url == "http://192.168.1.9:1234/v1/chat/completions"
    # Provider stripped from resolved model name.
    assert client.settings.model == "google/gemma-4-31b"


def test_macbook_identifier_routes_to_macbook_url(monkeypatch):
    """``lmstudio_macbook:foo`` must dispatch against the MacBook Pro URL."""
    monkeypatch.setattr(
        "modules.llm_client.cfg.get_lmstudio_macstudio_url",
        lambda: "http://192.168.1.9:1234/v1/chat/completions",
    )
    monkeypatch.setattr(
        "modules.llm_client.cfg.get_lmstudio_macbook_url",
        lambda: "http://localhost:1234/v1/chat/completions",
    )

    client = create_client(model="lmstudio_macbook:google/gemma-4-31b")
    assert client.settings.llm_source == "lmstudio"
    assert client.settings.api_url == "http://localhost:1234/v1/chat/completions"
    assert client.settings.model == "google/gemma-4-31b"


def test_legacy_lmstudio_local_identifier_routes_to_macstudio(monkeypatch):
    """``lmstudio_local:foo`` predates the split and must keep targeting the
    Mac Studio host (the historical single-LM-Studio default). This guards
    backward compat for any persisted job manifests using the legacy tag."""
    monkeypatch.setattr(
        "modules.llm_client.cfg.get_lmstudio_macstudio_url",
        lambda: "http://192.168.1.9:1234/v1/chat/completions",
    )
    monkeypatch.setattr(
        "modules.llm_client.cfg.get_lmstudio_macbook_url",
        lambda: "http://localhost:1234/v1/chat/completions",
    )

    client = create_client(model="lmstudio_local:google/gemma-4-31b")
    assert client.settings.llm_source == "lmstudio"
    assert client.settings.api_url == "http://192.168.1.9:1234/v1/chat/completions"
