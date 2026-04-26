"""Tests for LLM endpoint fallback routing.

Guards the fix for the cloud→local fallback regression: Ollama's cloud catalog
returns bare model names but locally-pulled cloud models carry a ``:cloud``
suffix, so the bare name 404s on local and masks the real cloud error.
"""

from __future__ import annotations

import pytest

from modules.llm_client import ClientSettings
from modules.llm_endpoints import LLMSource, _iter_sources, resolve_endpoints


pytestmark = pytest.mark.services


def test_local_primary_falls_back_to_cloud():
    """Default fallback: local primary → cloud secondary (model available in both)."""
    sources = list(_iter_sources(LLMSource.LOCAL, fallbacks=[], allow_fallback=True))
    assert sources == [LLMSource.LOCAL, LLMSource.CLOUD]


def test_cloud_primary_no_automatic_local_fallback():
    """Cloud primary must NOT auto-fallback to local.

    Cloud-catalog model names are bare (e.g. `deepseek-v4-flash`) but locally-
    pulled cloud models keep the `:cloud` suffix. Falling back to local with
    the bare name causes 404s that mask the real cloud error.
    """
    sources = list(_iter_sources(LLMSource.CLOUD, fallbacks=[], allow_fallback=True))
    assert sources == [LLMSource.CLOUD]


def test_explicit_fallback_honored_for_cloud():
    """If a caller explicitly requests local as fallback, honor it."""
    sources = list(
        _iter_sources(LLMSource.CLOUD, fallbacks=["local"], allow_fallback=True)
    )
    assert sources == [LLMSource.CLOUD, LLMSource.LOCAL]


def test_allow_fallback_false_returns_primary_only():
    """allow_fallback=False disables all fallback regardless of primary."""
    for primary in (LLMSource.LOCAL, LLMSource.CLOUD):
        sources = list(_iter_sources(primary, fallbacks=[], allow_fallback=False))
        assert sources == [primary]


def test_resolve_endpoints_cloud_does_not_include_local(monkeypatch):
    """End-to-end: resolve_endpoints(cloud) must not include a local endpoint."""
    settings = ClientSettings(
        llm_source="cloud",
        cloud_api_key="test-key",
        cloud_api_url="https://ollama.example/v1/chat/completions",
        local_api_url="http://127.0.0.1:11434/api/chat",
    )
    endpoints = resolve_endpoints(settings)
    sources = [e.source for e in endpoints]
    assert sources == [LLMSource.CLOUD]


def test_resolve_endpoints_local_still_falls_back_to_cloud():
    """resolve_endpoints(local) should still try cloud as secondary."""
    settings = ClientSettings(
        llm_source="local",
        cloud_api_key="test-key",
        cloud_api_url="https://ollama.example/v1/chat/completions",
        local_api_url="http://127.0.0.1:11434/api/chat",
    )
    endpoints = resolve_endpoints(settings)
    sources = [e.source for e in endpoints]
    assert sources == [LLMSource.LOCAL, LLMSource.CLOUD]
