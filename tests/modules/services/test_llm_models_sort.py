"""Tests for quality-based sorting of the LLM model picker."""

from __future__ import annotations

import pytest

from modules.services import llm_models


pytestmark = pytest.mark.services


def test_default_model_pinned_to_top():
    """Mistral-large-3 (configured default) should always sort first."""
    sample = [
        "ollama_cloud:gemma3:27b",
        "ollama_cloud:mistral-large-3:675b",
        "ollama_cloud:devstral-2:123b",
        "ollama_cloud:deepseek-v3.2",
    ]
    sorted_models = sorted(sample, key=llm_models._sort_key_for_model)
    assert sorted_models[0] == "ollama_cloud:mistral-large-3:675b"


def test_coding_specialised_models_sort_last():
    """devstral / qwen-coder should always sort below multilingual models."""
    sample = [
        "ollama_cloud:devstral-2:123b",
        "ollama_cloud:qwen3-coder:480b",
        "ollama_cloud:gemma3:27b",
        "ollama_cloud:deepseek-v3.2",
    ]
    sorted_models = sorted(sample, key=llm_models._sort_key_for_model)
    # Coding SKUs should be at the end.
    assert sorted_models[-2:] == [
        "ollama_cloud:devstral-2:123b",
        "ollama_cloud:qwen3-coder:480b",
    ]


def test_broken_models_sort_to_bottom():
    """Models that consistently fail probes (kimi-k2-thinking) or are
    coding-specialised should sort below working models."""
    sample = [
        "ollama_cloud:kimi-k2-thinking",  # tier 80 (HTTP 500 in probe)
        "ollama_cloud:deepseek-v3.1:671b",  # tier 20 (5/5)
        "ollama_cloud:devstral-2:123b",  # tier 90 (coding)
    ]
    sorted_models = sorted(sample, key=llm_models._sort_key_for_model)
    assert sorted_models[0] == "ollama_cloud:deepseek-v3.1:671b"
    # kimi-k2-thinking before devstral (80 < 90)
    assert sorted_models[1] == "ollama_cloud:kimi-k2-thinking"
    assert sorted_models[2] == "ollama_cloud:devstral-2:123b"


def test_measured_top_performers_beat_slow_models():
    """Re-ranking: gemma4:31b measured 5/5 at 1.1s outranks the GLM-4/5 family
    (slow and partial-pass) and qwen3.5:397b (1/5 timing out at 52s)."""
    sample = [
        "ollama_cloud:glm-4.7",
        "ollama_cloud:qwen3.5:397b",
        "ollama_cloud:gemma4:31b",
        "ollama_cloud:glm-5.1",
    ]
    sorted_models = sorted(sample, key=llm_models._sort_key_for_model)
    # gemma4:31b (tier 23) must outrank all three slow/broken ones.
    assert sorted_models[0] == "ollama_cloud:gemma4:31b"
    # glm-4.7 (tier 70) should outrank qwen3.5:397b (tier 72)
    glm_idx = sorted_models.index("ollama_cloud:glm-4.7")
    qwen_idx = sorted_models.index("ollama_cloud:qwen3.5:397b")
    assert glm_idx < qwen_idx


def test_unknown_model_placed_in_default_tier():
    """Newly-released models with no entry slot into tier 60 — below
    'slow but usable' (60s) and above 'poor' (70s)."""
    tier_known_small = llm_models._model_quality_tier("gpt-oss:20b")  # 50
    tier_slow_usable = llm_models._model_quality_tier("kimi-k2.6")  # 61
    tier_unknown = llm_models._model_quality_tier("some-new-model-v99:cloud")  # 60
    tier_poor = llm_models._model_quality_tier("glm-4.6")  # 71
    # Unknown should land at 60 — small (50) < unknown (60) < poor (71)
    assert tier_known_small < tier_unknown < tier_poor


def test_provider_prefix_stripped_for_tier_lookup():
    """Tier lookup must ignore the ollama_cloud:/ollama_local: prefix."""
    cloud_key = llm_models._sort_key_for_model("ollama_cloud:mistral-large-3:675b")
    local_key = llm_models._sort_key_for_model("ollama_local:mistral-large-3:675b")
    # Both are in the Ollama group (group 0), same tier 10.
    assert cloud_key[0] == local_key[0] == 0  # provider group
    assert cloud_key[1] == local_key[1] == 10  # tier
    # Cloud sorts before local within Ollama (sub-provider index).
    assert cloud_key[2] < local_key[2]


def test_lmstudio_models_sort_after_ollama():
    """LM Studio models appear after ALL Ollama models regardless of quality.

    Also verifies the two LM Studio hosts (Mac Studio and MacBook Pro) sit in
    the same group, with Mac Studio listed first within the group.
    """
    sample = [
        "ollama_cloud:mistral-large-3:675b",         # group 0, tier 10
        "ollama_cloud:qwen3-coder:480b",              # group 0, tier 93 (coding)
        "lmstudio_macstudio:google/gemma-4-31b",      # group 1, tier 23, Mac Studio
        "lmstudio_macbook:google/gemma-4-31b",        # group 1, tier 23, MacBook Pro
        "lmstudio_macstudio:translategemma-27b-it",   # group 1, tier 60, Mac Studio
    ]
    sorted_models = sorted(sample, key=llm_models._sort_key_for_model)
    # All Ollama entries must come before any LM Studio entry.
    lms_prefixes = ("lmstudio_macstudio:", "lmstudio_macbook:", "lmstudio_local:")
    lms_start = next(
        i for i, m in enumerate(sorted_models) if m.startswith(lms_prefixes)
    )
    for m in sorted_models[:lms_start]:
        assert m.startswith("ollama_"), f"{m} should be before LM Studio block"
    for m in sorted_models[lms_start:]:
        assert m.startswith(lms_prefixes), f"{m} should be in LM Studio block"
    # Within LM Studio, gemma-4-31b on Mac Studio (subprovider 0) beats
    # gemma-4-31b on MacBook Pro (subprovider 1) when the tier is identical.
    macstudio_idx = sorted_models.index("lmstudio_macstudio:google/gemma-4-31b")
    macbook_idx = sorted_models.index("lmstudio_macbook:google/gemma-4-31b")
    assert macstudio_idx < macbook_idx
    # And gemma-4-31b (tier 23) beats translategemma (unknown tier 60).
    translate_idx = sorted_models.index("lmstudio_macstudio:translategemma-27b-it")
    assert macstudio_idx < translate_idx


def test_lmstudio_legacy_tag_groups_with_macstudio():
    """`lmstudio_local:` (legacy tag) sorts in the LM Studio group at the
    Mac Studio sub-position, since that tag historically meant the Mac Studio
    host (the only LM Studio destination before the split)."""
    legacy = "lmstudio_local:google/gemma-4-31b"
    macstudio = "lmstudio_macstudio:google/gemma-4-31b"
    legacy_key = llm_models._sort_key_for_model(legacy)
    macstudio_key = llm_models._sort_key_for_model(macstudio)
    # Same group, same tier, same subprovider rank.
    assert legacy_key[0] == macstudio_key[0] == 1
    assert legacy_key[1] == macstudio_key[1]
    assert legacy_key[2] == macstudio_key[2] == 0


def test_macstudio_listed_before_macbook_within_lmstudio_group():
    """For identical models on both hosts, Mac Studio (workstation) sorts
    before MacBook Pro (laptop)."""
    sample = [
        "lmstudio_macbook:google/gemma-4-31b",
        "lmstudio_macstudio:google/gemma-4-31b",
    ]
    sorted_models = sorted(sample, key=llm_models._sort_key_for_model)
    assert sorted_models == [
        "lmstudio_macstudio:google/gemma-4-31b",
        "lmstudio_macbook:google/gemma-4-31b",
    ]


def test_legacy_cloud_suffix_handled():
    """`mistral-large-3:675b-cloud` (legacy tag form) lands adjacent to stripped."""
    tier_stripped = llm_models._model_quality_tier("mistral-large-3:675b")
    tier_legacy = llm_models._model_quality_tier("mistral-large-3:675b-cloud")
    # Within 5 tier points of each other — both pinned at top.
    assert abs(tier_stripped - tier_legacy) <= 5
    assert max(tier_stripped, tier_legacy) <= 15


def test_list_available_llm_models_includes_both_lmstudio_hosts(monkeypatch):
    """Mac Studio and MacBook Pro discovery results must both be labeled with
    their host-specific prefix and surface in the picker list."""
    monkeypatch.setattr(llm_models, "_list_ollama_models", lambda: [])
    monkeypatch.setattr(llm_models, "_list_ollama_cli_models", lambda: [])
    monkeypatch.setattr(llm_models, "_list_cloud_models", lambda: [])
    monkeypatch.setattr(
        llm_models,
        "_list_lmstudio_macstudio_models",
        lambda: ["google/gemma-4-31b", "qwen3-32b"],
    )
    monkeypatch.setattr(
        llm_models,
        "_list_lmstudio_macbook_models",
        lambda: ["google/gemma-4-31b", "tinyllama"],
    )

    result = llm_models.list_available_llm_models()

    assert "lmstudio_macstudio:google/gemma-4-31b" in result
    assert "lmstudio_macstudio:qwen3-32b" in result
    assert "lmstudio_macbook:google/gemma-4-31b" in result
    assert "lmstudio_macbook:tinyllama" in result
    # Mac Studio entries appear before MacBook entries within the LM Studio group.
    macstudio_first = next(i for i, m in enumerate(result) if m.startswith("lmstudio_macstudio:"))
    macbook_first = next(i for i, m in enumerate(result) if m.startswith("lmstudio_macbook:"))
    assert macstudio_first < macbook_first


def test_list_available_llm_models_returns_sorted(monkeypatch):
    """End-to-end: list_available_llm_models() must return tier-sorted output.

    After re-ranking from measured probe results, gemma3:27b (5/5, 0.9s,
    tier 24) now outranks deepseek-v3.2 (5/5 but 9.1s slow, tier 40).
    """
    mock_models = [
        "ollama_cloud:devstral-2:123b",  # tier 90 (coding)
        "ollama_cloud:gemma3:27b",  # tier 24 (promoted)
        "ollama_cloud:mistral-large-3:675b",  # tier 10 (pinned)
        "ollama_cloud:deepseek-v3.2",  # tier 40 (demoted for slowness)
        "ollama_cloud:deepseek-v3.1:671b",  # tier 20 (measured leader)
    ]

    monkeypatch.setattr(llm_models, "_list_ollama_models", lambda: [])
    monkeypatch.setattr(llm_models, "_list_ollama_cli_models", lambda: [])
    monkeypatch.setattr(llm_models, "_list_cloud_models", lambda: [m.split(":", 1)[1] for m in mock_models])
    monkeypatch.setattr(llm_models, "_list_lmstudio_macstudio_models", lambda: [])
    monkeypatch.setattr(llm_models, "_list_lmstudio_macbook_models", lambda: [])

    result = llm_models.list_available_llm_models()

    # Mistral stays at top (pinned default).
    assert result[0] == "ollama_cloud:mistral-large-3:675b"
    # deepseek-v3.1:671b (measured leader) beats gemma3:27b.
    ds31_idx = result.index("ollama_cloud:deepseek-v3.1:671b")
    gemma_idx = result.index("ollama_cloud:gemma3:27b")
    ds32_idx = result.index("ollama_cloud:deepseek-v3.2")
    devstral_idx = result.index("ollama_cloud:devstral-2:123b")
    assert ds31_idx < gemma_idx < ds32_idx < devstral_idx
