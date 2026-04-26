"""Tests for the LM Studio host split (Mac Studio vs MacBook Pro)."""

from __future__ import annotations

import pytest

from modules.llm_providers import (
    LMSTUDIO_LOCAL,
    LMSTUDIO_MACBOOK,
    LMSTUDIO_MACSTUDIO,
    is_local_llm_provider,
    is_lmstudio_provider,
    normalize_llm_provider,
    split_llm_model_identifier,
)


pytestmark = pytest.mark.services


def test_macstudio_provider_normalizes():
    """Canonical and aliased forms all collapse to ``lmstudio_macstudio``."""
    assert normalize_llm_provider("lmstudio_macstudio") == LMSTUDIO_MACSTUDIO
    assert normalize_llm_provider("lmstudio-macstudio") == LMSTUDIO_MACSTUDIO
    assert normalize_llm_provider("LMSTUDIO_MAC_STUDIO") == LMSTUDIO_MACSTUDIO


def test_macbook_provider_normalizes():
    """All MacBook spellings (with/without ``pro`` suffix, hyphen vs. underscore)."""
    assert normalize_llm_provider("lmstudio_macbook") == LMSTUDIO_MACBOOK
    assert normalize_llm_provider("lmstudio-macbook") == LMSTUDIO_MACBOOK
    assert normalize_llm_provider("lmstudio_macbookpro") == LMSTUDIO_MACBOOK
    assert normalize_llm_provider("lmstudio-macbook-pro") == LMSTUDIO_MACBOOK


def test_legacy_lmstudio_tag_aliases_to_macstudio():
    """``lmstudio_local`` and the bare ``lmstudio`` tag predate the host split
    and continue to mean the Mac Studio host (the historical default)."""
    assert normalize_llm_provider("lmstudio") == LMSTUDIO_MACSTUDIO
    assert normalize_llm_provider("lmstudio_local") == LMSTUDIO_MACSTUDIO
    # The constant for the legacy tag is preserved for back-compat callers,
    # but it MUST resolve to the same canonical provider as Mac Studio.
    assert normalize_llm_provider(LMSTUDIO_LOCAL) == LMSTUDIO_MACSTUDIO


def test_split_identifier_with_macbook_prefix():
    """Identifiers like ``lmstudio_macbook:google/gemma-4-31b`` split cleanly."""
    provider, model = split_llm_model_identifier("lmstudio_macbook:google/gemma-4-31b")
    assert provider == LMSTUDIO_MACBOOK
    assert model == "google/gemma-4-31b"


def test_split_identifier_with_macstudio_prefix_and_colon_in_model_name():
    """Mac Studio identifiers preserve colons inside the model name."""
    provider, model = split_llm_model_identifier(
        "lmstudio_macstudio:qwen3-vl:235b-instruct"
    )
    assert provider == LMSTUDIO_MACSTUDIO
    assert model == "qwen3-vl:235b-instruct"


def test_is_lmstudio_provider_recognizes_all_three_tags():
    """``is_lmstudio_provider`` must return True for legacy + both new tags."""
    assert is_lmstudio_provider(LMSTUDIO_LOCAL)
    assert is_lmstudio_provider(LMSTUDIO_MACSTUDIO)
    assert is_lmstudio_provider(LMSTUDIO_MACBOOK)
    assert not is_lmstudio_provider("ollama_cloud")
    assert not is_lmstudio_provider(None)


def test_lmstudio_hosts_classified_as_local():
    """Both LM Studio hosts are local (laptop/workstation), not cloud."""
    assert is_local_llm_provider(LMSTUDIO_MACSTUDIO) is True
    assert is_local_llm_provider(LMSTUDIO_MACBOOK) is True
    assert is_local_llm_provider("ollama_cloud") is False
