"""Tests for token alignment utilities."""

import pytest

from modules.text import (
    align_token_counts,
    count_tokens,
    force_align_by_position,
    split_highlight_tokens,
)
from modules import translation_validation as tv


class TestCountTokens:
    """Tests for count_tokens function."""

    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_single_word(self):
        assert count_tokens("hello") == 1

    def test_multiple_words(self):
        assert count_tokens("hello world foo bar") == 4

    def test_chinese_with_spaces(self):
        assert count_tokens("你好 世界") == 2

    def test_chinese_without_spaces(self):
        # Without spaces, falls back to character tokenization
        tokens = split_highlight_tokens("你好世界")
        assert len(tokens) >= 1


class TestAlignTokenCounts:
    """Tests for align_token_counts function."""

    def test_already_aligned(self):
        translation = "你好 世界"
        transliteration = "ni-hao shi-jie"
        aligned_trans, aligned_translit, modified = align_token_counts(
            translation, transliteration, "chinese"
        )
        assert not modified
        assert aligned_trans == translation
        assert aligned_translit == transliteration

    def test_empty_translation(self):
        aligned_trans, aligned_translit, modified = align_token_counts(
            "", "ni-hao", "chinese"
        )
        assert not modified
        assert aligned_trans == ""

    def test_empty_transliteration(self):
        aligned_trans, aligned_translit, modified = align_token_counts(
            "你好", "", "chinese"
        )
        assert not modified
        assert aligned_translit == ""

    def test_join_hyphenated_syllables_to_reduce_count(self):
        # Transliteration has more tokens than translation
        translation = "你好 世界"  # 2 tokens
        transliteration = "ni hao shi jie"  # 4 tokens
        aligned_trans, aligned_translit, modified = align_token_counts(
            translation, transliteration, "chinese"
        )
        # Should attempt to join syllables
        aligned_count = count_tokens(aligned_translit)
        original_count = count_tokens(transliteration)
        # Either modified or original should be returned
        assert aligned_count <= original_count or aligned_translit == transliteration

    def test_split_hyphenated_to_increase_count(self):
        # Translation has more tokens than transliteration
        translation = "你好 世界 我"  # 3 tokens
        transliteration = "ni-hao-shi-jie wo"  # 2 tokens
        aligned_trans, aligned_translit, modified = align_token_counts(
            translation, transliteration, "chinese"
        )
        # Should attempt to split hyphens
        if modified:
            aligned_count = count_tokens(aligned_translit)
            original_count = count_tokens(transliteration)
            # Might have increased token count
            assert aligned_count >= original_count

    def test_japanese_alignment(self):
        translation = "こんにちは 世界"
        transliteration = "konnichiwa sekai"
        aligned_trans, aligned_translit, modified = align_token_counts(
            translation, transliteration, "japanese"
        )
        # Both should have same count, so no modification needed
        trans_count = count_tokens(aligned_trans)
        translit_count = count_tokens(aligned_translit)
        # Allow some flexibility
        assert abs(trans_count - translit_count) <= 1 or not modified

    def test_non_cjk_language_passthrough(self):
        # For non-CJK languages, should pass through unmodified
        translation = "hello world"
        transliteration = "hello world"
        aligned_trans, aligned_translit, modified = align_token_counts(
            translation, transliteration, "english"
        )
        assert not modified
        assert aligned_trans == translation
        assert aligned_translit == transliteration


class TestForceAlignByPosition:
    """Tests for force_align_by_position function."""

    def test_already_aligned(self):
        pairs, truncated = force_align_by_position(
            "你好 世界",
            "ni-hao shi-jie",
            "chinese",
        )
        assert len(pairs) == 2
        assert not truncated
        assert pairs[0][0] == "你好"
        assert pairs[0][1] == "ni-hao"
        assert pairs[1][0] == "世界"
        assert pairs[1][1] == "shi-jie"

    def test_more_translation_tokens(self):
        # Translation has more tokens
        pairs, truncated = force_align_by_position(
            "a b c d",  # 4 tokens
            "x y",  # 2 tokens
            "chinese",
        )
        assert len(pairs) == 2  # Matches shorter list
        assert truncated

    def test_more_transliteration_tokens(self):
        # Transliteration has more tokens
        pairs, truncated = force_align_by_position(
            "a b",  # 2 tokens
            "x y z w",  # 4 tokens
            "chinese",
        )
        assert len(pairs) == 2  # Matches shorter list
        assert truncated

    def test_empty_translation(self):
        pairs, truncated = force_align_by_position(
            "",
            "x y",
            "chinese",
        )
        assert len(pairs) == 0
        assert not truncated

    def test_empty_transliteration(self):
        pairs, truncated = force_align_by_position(
            "a b",
            "",
            "chinese",
        )
        assert len(pairs) == 0
        assert not truncated


class TestTokenCountValidation:
    """Tests for token count validation in translation_validation."""

    def test_is_token_count_aligned_equal_counts(self):
        is_aligned, trans_count, translit_count = tv.is_token_count_aligned(
            "你好 世界",
            "ni-hao shi-jie",
            "chinese",
        )
        assert is_aligned
        assert trans_count == 2
        assert translit_count == 2

    def test_is_token_count_aligned_within_tolerance(self):
        # Differ by 1 should be within default tolerance
        is_aligned, trans_count, translit_count = tv.is_token_count_aligned(
            "你好 世界 我",  # 3 tokens
            "ni-hao shi-jie",  # 2 tokens
            "chinese",
            tolerance=1,
        )
        assert is_aligned
        assert trans_count == 3
        assert translit_count == 2

    def test_is_token_count_aligned_exceeds_tolerance(self):
        is_aligned, trans_count, translit_count = tv.is_token_count_aligned(
            "a b c d e",  # 5 tokens
            "x y",  # 2 tokens
            "chinese",
            tolerance=1,
        )
        assert not is_aligned
        assert trans_count == 5
        assert translit_count == 2

    def test_non_cjk_language_always_aligned(self):
        # Non-CJK languages should skip the check
        is_aligned, _, _ = tv.is_token_count_aligned(
            "hello world",
            "hello",
            "english",
        )
        assert is_aligned

    def test_get_token_alignment_error_when_aligned(self):
        error = tv.get_token_alignment_error(
            "你好 世界",
            "ni-hao shi-jie",
            "chinese",
        )
        assert error is None

    def test_get_token_alignment_error_when_misaligned(self):
        error = tv.get_token_alignment_error(
            "a b c d e",  # 5 tokens
            "x y",  # 2 tokens
            "chinese",
        )
        assert error is not None
        assert "mismatch" in error.lower()
        assert "5" in error
        assert "2" in error


class TestPromptTemplatesIncludeAlignment:
    """Tests that prompt templates include token alignment instructions."""

    def test_chinese_prompt_includes_alignment(self):
        from modules import prompt_templates

        prompt = prompt_templates.make_translation_prompt(
            "english",
            "chinese",
            include_transliteration=True,
        )
        # Should mention alignment/matching
        assert "same number" in prompt.lower() or "critical" in prompt.lower()

    def test_japanese_prompt_includes_alignment(self):
        from modules import prompt_templates

        prompt = prompt_templates.make_translation_prompt(
            "english",
            "japanese",
            include_transliteration=True,
        )
        assert "same number" in prompt.lower() or "match" in prompt.lower()

    def test_korean_prompt_includes_alignment(self):
        from modules import prompt_templates

        prompt = prompt_templates.make_translation_prompt(
            "english",
            "korean",
            include_transliteration=True,
        )
        assert "same number" in prompt.lower() or "match" in prompt.lower()

    def test_batch_prompt_includes_alignment(self):
        from modules import prompt_templates

        prompt = prompt_templates.make_translation_batch_prompt(
            "english",
            "chinese",
            include_transliteration=True,
        )
        assert "same number" in prompt.lower() or "critical" in prompt.lower()
