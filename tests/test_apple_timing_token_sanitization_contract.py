from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERACTIVE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Features" / "InteractivePlayer"
CONTEXT_BUILDER = INTERACTIVE / "InteractivePlayerContextBuilder.swift"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_context_builder_sanitizes_global_and_chunk_timing_tokens() -> None:
    source = _source(CONTEXT_BUILDER)

    assert "let tokens = sanitizeTimingTokens(" in source
    assert "timing?.tracks.translation.segments.compactMap { WordTimingToken(entry: $0) } ?? []" in source
    assert "return Dictionary(grouping: sanitizeTimingTokens(tokens))" in source
    assert "private static func sanitizeTimingTokens(_ tokens: [WordTimingToken]) -> [WordTimingToken]" in source
    assert "private static func sanitizeTimingTokenGroup(_ tokens: [WordTimingToken]) -> [WordTimingToken]" in source


def test_timing_token_sanitizer_rejects_invalid_windows_and_clamps_overlaps() -> None:
    source = _source(CONTEXT_BUILDER)

    assert "token.startTime.isFinite" in source
    assert "token.endTime.isFinite" in source
    assert "token.endTime > token.startTime" in source
    assert "let adjustedStart = max(token.startTime, previousEnd ?? token.startTime)" in source
    assert "let adjustedEnd = max(token.endTime, adjustedStart + 0.001)" in source
    assert "previousEnd = adjustedEnd" in source


def test_timing_token_sanitizer_preserves_sentence_and_file_boundaries() -> None:
    source = _source(CONTEXT_BUILDER)

    assert "private struct TimingTokenGroupKey: Hashable" in source
    assert "sentenceIndex: token.sentenceIndex" in source
    assert "fileIndex: token.fileIndex" in source
    assert "if left.key.fileSortValue != right.key.fileSortValue" in source
    assert "return left.key.fileSortValue < right.key.fileSortValue" in source
    assert "return left.key.sentenceSortValue < right.key.sentenceSortValue" in source
    assert "sentenceIndex: token.sentenceIndex" in source
    assert "fileIndex: token.fileIndex" in source
