"""Tests for LLM endpoint fallback routing.

Guards the fix for the cloud→local fallback regression: Ollama's cloud catalog
returns bare model names but locally-pulled cloud models carry a ``:cloud``
suffix, so the bare name 404s on local and masks the real cloud error.
"""

from __future__ import annotations

import pytest
import requests

from modules.llm_client import ClientSettings, LLMClient, create_client
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


@pytest.fixture
def recording_session(monkeypatch):
    session = requests.Session()
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs['json']))
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"message":{"content":"translated"}}'
        return response

    monkeypatch.setattr(session, 'post', post)
    yield session, calls
    session.close()


def test_default_translation_client_uses_fast_deepseek(recording_session):
    session, calls = recording_session
    with create_client(api_key='test-key', cloud_api_key='test-key', session=session) as client:
        payload = {'model': client.model, 'messages': [], 'stream': False}
        response = client.send_chat_request(payload, max_attempts=1)

    assert response.status_code == 200
    assert response.source == 'cloud'
    assert calls[0][1]['model'] == 'deepseek-v4-flash:0731'
    assert calls[0][1]['reasoning_effort'] == 'none'
    assert 'reasoning_effort' not in payload


@pytest.mark.parametrize('model,source,expected', [
    ('deepseek-v4-flash:0731', 'cloud', 'none'),
    ('deepseek-v4-flash:0731-cloud', 'cloud', 'none'),
    ('ollama_cloud:deepseek-v4-flash:0731', 'cloud', 'none'),
    ('gemma4:31b', 'cloud', None),
    ('qwen3.5:397b', 'cloud', None),
    ('deepseek-v4-flash:0731', 'local', None),
    ('deepseek-v4-flash:0731', 'lmstudio', None),
])
def test_fast_reasoning_default_is_scoped_to_cloud_deepseek(recording_session, model, source, expected):
    session, calls = recording_session
    client = LLMClient(ClientSettings(
        model=model, llm_source=source, api_key='test-key', cloud_api_key='test-key',
        local_api_url='http://local.example/api/chat',
        cloud_api_url='http://cloud.example/v1/chat/completions',
        lmstudio_api_url='http://lmstudio.example/v1/chat/completions',
        allow_fallback=False,
    ), session=session)
    payload = {'model': model, 'messages': [], 'stream': False}
    client.send_chat_request(payload, max_attempts=1)
    assert calls[0][1].get('reasoning_effort') == expected
    assert calls[0][1]['model'] == model
    assert 'reasoning_effort' not in payload


@pytest.mark.parametrize('override', [
    {'reasoning_effort': 'high'},
    {'reasoning': {'effort': 'high'}},
])
def test_explicit_reasoning_setting_is_preserved(recording_session, override):
    session, calls = recording_session
    with create_client(model='ollama_cloud:deepseek-v4-flash:0731',
                       api_key='test-key', cloud_api_key='test-key', session=session) as client:
        payload = {'model': client.model, 'messages': [], 'stream': False, **override}
        client.send_chat_request(payload, max_attempts=1)
    assert calls[0][1] == payload


def test_fast_reasoning_default_does_not_apply_to_completion_api(recording_session):
    session, calls = recording_session
    with create_client(model='ollama_cloud:deepseek-v4-flash:0731',
                       api_key='test-key', cloud_api_key='test-key', session=session) as client:
        client.send_completion_request({'model': client.model, 'prompt': 'Hello'}, max_attempts=1)
    assert 'reasoning_effort' not in calls[0][1]
