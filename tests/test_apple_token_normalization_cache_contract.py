from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERACTIVE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "InteractivePlayer"
)
CONTEXT_BUILDER = INTERACTIVE / "InteractivePlayerContextBuilder.swift"
VIEW_MODEL = INTERACTIVE / "InteractivePlayerViewModel.swift"
LOADING = INTERACTIVE / "InteractivePlayerViewModel+Loading.swift"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_token_normalization_cache_is_bounded_and_source_keyed() -> None:
    source = _source(CONTEXT_BUILDER)

    assert "final class TokenNormalizationCache: @unchecked Sendable" in source
    assert "private struct Key: Hashable" in source
    assert "let text: String" in source
    assert "let explicitTokens: [String]" in source
    assert "private let lock = NSLock()" in source
    assert "private var values: [Key: [String]] = [:]" in source
    assert "private var insertionOrder: [Key] = []" in source
    assert "init(limit: Int = 4096)" in source
    assert "self.limit = max(1, limit)" in source
    assert "func removeAll()" in source
    assert "while values.count > limit, !insertionOrder.isEmpty" in source


def test_context_builder_uses_token_cache_for_all_metadata_text_variants() -> None:
    source = _source(CONTEXT_BUILDER)

    assert "tokenCache: TokenNormalizationCache? = nil" in source
    assert "tokenCache: tokenCache" in source
    assert "private static func normaliseTokens(text: String, tokens: [String]?, cache: TokenNormalizationCache?) -> [String]" in source
    assert "cache?.tokens(text: text, explicitTokens: tokens)" in source
    assert "normaliseTokensUncached(text: text, tokens: tokens)" in source
    assert "let originalTokens = normaliseTokens(text: originalText, tokens: sentence.original.tokens, cache: tokenCache)" in source
    assert "let translationTokens = normaliseTokens(text: translationText, tokens: sentence.translation?.tokens, cache: tokenCache)" in source
    assert "let transliterationTokens = normaliseTokens(text: transliterationText ?? \"\", tokens: sentence.transliteration?.tokens, cache: tokenCache)" in source


def test_interactive_player_reuses_cache_across_context_rebuilds_and_resets_per_job() -> None:
    view_model = _source(VIEW_MODEL)
    loading = _source(LOADING)

    assert "let tokenNormalizationCache = TokenNormalizationCache()" in view_model
    assert "tokenNormalizationCache.removeAll()" in loading
    assert loading.count("tokenCache: tokenNormalizationCache") >= 4
    assert "tokenCache: tokenCache" in loading
    assert "Task.detached(priority: .userInitiated)" in loading
