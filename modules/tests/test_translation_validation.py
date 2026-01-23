"""Unit tests for translation_validation module."""

import pytest

from modules import translation_validation as tv


class TestLetterCount:
    def test_empty_string(self):
        assert tv.letter_count("") == 0

    def test_only_letters(self):
        assert tv.letter_count("hello") == 5

    def test_mixed_with_numbers(self):
        assert tv.letter_count("hello123") == 5

    def test_mixed_with_punctuation(self):
        assert tv.letter_count("Hello, world!") == 10

    def test_only_numbers(self):
        assert tv.letter_count("12345") == 0

    def test_only_punctuation(self):
        assert tv.letter_count("!@#$%") == 0

    def test_unicode_letters(self):
        assert tv.letter_count("こんにちは") == 5
        assert tv.letter_count("مرحبا") == 5


class TestHasNonLatinLetters:
    def test_only_latin(self):
        assert not tv.has_non_latin_letters("hello")

    def test_with_japanese(self):
        assert tv.has_non_latin_letters("こんにちは")

    def test_with_arabic(self):
        assert tv.has_non_latin_letters("مرحبا")

    def test_mixed_latin_and_non_latin(self):
        assert tv.has_non_latin_letters("hello こんにちは")

    def test_empty_string(self):
        assert not tv.has_non_latin_letters("")

    def test_only_numbers(self):
        assert not tv.has_non_latin_letters("12345")


class TestLatinFraction:
    def test_empty_string(self):
        assert tv.latin_fraction("") == 0.0

    def test_all_latin(self):
        assert tv.latin_fraction("hello") == 1.0

    def test_all_non_latin(self):
        assert tv.latin_fraction("こんにちは") == 0.0

    def test_half_latin_half_non_latin(self):
        # "helloこんにちは" - 5 Latin, 5 Japanese
        result = tv.latin_fraction("helloこんにちは")
        assert 0.49 < result < 0.51  # Should be ~0.5

    def test_mostly_latin(self):
        # "helloこ" - 5 Latin, 1 Japanese
        result = tv.latin_fraction("helloこ")
        assert result > 0.8

    def test_mostly_non_latin(self):
        # "hこんにちは" - 1 Latin, 5 Japanese
        result = tv.latin_fraction("hこんにちは")
        assert result < 0.2

    def test_no_letters(self):
        assert tv.latin_fraction("12345!@#") == 0.0


class TestIsProbableTransliteration:
    def test_non_latin_original_latin_translation_non_latin_target(self):
        # Arabic original, Latin translation, Arabic target
        assert tv.is_probable_transliteration("مرحبا", "marhaba", "arabic")

    def test_non_latin_original_non_latin_translation(self):
        # Arabic original, Arabic translation
        assert not tv.is_probable_transliteration("مرحبا", "أهلا", "arabic")

    def test_latin_original(self):
        # Latin original should not trigger
        assert not tv.is_probable_transliteration("hello", "hola", "spanish")

    def test_latin_target_language(self):
        # Latin target language should not trigger
        assert not tv.is_probable_transliteration("こんにちは", "hello", "english")

    def test_mixed_translation(self):
        # Some Latin, some non-Latin (need < 60% Latin to not trigger)
        # "こんにちはhello" has 5 Japanese, 5 Latin = 50% Latin
        assert not tv.is_probable_transliteration("こんにちは", "こんにちはhello", "japanese")

    def test_empty_translation(self):
        assert not tv.is_probable_transliteration("こんにちは", "", "japanese")


class TestIsTranslationTooShort:
    def test_very_short_original(self):
        # Short originals (<=12 letters) never trigger
        assert not tv.is_translation_too_short("hello", "")

    def test_empty_translation(self):
        # Long original, empty translation
        assert tv.is_translation_too_short("This is a long sentence with many letters", "")

    def test_very_short_translation_for_long_original(self):
        # 80+ letters original, <15 letters translation
        original = "a" * 85
        translation = "b" * 14
        assert tv.is_translation_too_short(original, translation)

    def test_ratio_based_truncation(self):
        # 30+ letters, ratio < 0.28
        original = "a" * 40
        translation = "b" * 10  # 10/40 = 0.25 < 0.28
        assert tv.is_translation_too_short(original, translation)

    def test_acceptable_ratio(self):
        # 30+ letters, ratio >= 0.28
        original = "a" * 40
        translation = "b" * 12  # 12/40 = 0.30 >= 0.28
        assert not tv.is_translation_too_short(original, translation)

    def test_similar_length(self):
        assert not tv.is_translation_too_short("hello world", "hola mundo")


class TestMissingRequiredDiacritics:
    def test_arabic_with_diacritics(self):
        # Arabic with tashkil
        is_missing, label = tv.missing_required_diacritics("مَرْحَبًا", "arabic")
        assert not is_missing
        assert label is None

    def test_arabic_without_diacritics(self):
        # Arabic without tashkil
        is_missing, label = tv.missing_required_diacritics("مرحبا", "arabic")
        assert is_missing
        assert "Arabic diacritics" in label

    def test_hebrew_with_niqqud(self):
        # Hebrew with niqqud
        is_missing, label = tv.missing_required_diacritics("שָׁלוֹם", "hebrew")
        assert not is_missing

    def test_hebrew_without_niqqud(self):
        # Hebrew without niqqud
        is_missing, label = tv.missing_required_diacritics("שלום", "hebrew")
        assert is_missing
        assert "niqqud" in label

    def test_non_diacritic_language(self):
        # English doesn't require diacritics
        is_missing, label = tv.missing_required_diacritics("hello", "english")
        assert not is_missing
        assert label is None

    def test_wrong_script_for_target(self):
        # Latin text for Arabic target (wrong script, should skip)
        is_missing, label = tv.missing_required_diacritics("hello", "arabic")
        assert not is_missing
        assert label is None


class TestScriptCounts:
    def test_delegates_to_language_policies(self):
        # This is a thin wrapper, just verify it calls through
        result = tv.script_counts("helloこんにちは")
        assert isinstance(result, dict)


class TestUnexpectedScriptUsed:
    # This function has complex logic that depends on language_policies.
    # We'll test basic cases; comprehensive tests would need mocking.

    def test_all_latin_text(self):
        # Latin text shouldn't trigger
        is_unexpected, label = tv.unexpected_script_used("hello", "japanese")
        assert not is_unexpected

    def test_empty_text(self):
        is_unexpected, label = tv.unexpected_script_used("", "japanese")
        assert not is_unexpected

    def test_no_policy_for_language(self):
        # Language without policy should not trigger
        is_unexpected, label = tv.unexpected_script_used("hello", "unknown-lang")
        assert not is_unexpected


class TestIsSegmentationOk:
    def test_non_segmentation_language(self):
        # English doesn't need segmentation checks
        assert tv.is_segmentation_ok("hello world", "hola mundo", "english")

    def test_single_word_original(self):
        # Single word originals bypass check
        assert tv.is_segmentation_ok("hello", "こんにちは", "japanese")

    def test_thai_with_no_spaces(self):
        # Thai with no segmentation (1 token)
        result = tv.is_segmentation_ok(
            "hello world test",
            "สวัสดีโลกทดสอบ",  # No spaces
            "thai"
        )
        assert not result

    def test_thai_with_good_segmentation(self):
        # Thai with proper word breaks
        result = tv.is_segmentation_ok(
            "hello world test more words",
            "สวัสดี โลก ทดสอบ เพิ่มเติม คำ",  # 5 tokens
            "thai"
        )
        assert result

    def test_japanese_with_spaces(self):
        # Japanese with word-like tokens
        result = tv.is_segmentation_ok(
            "this is a test sentence",
            "これ は テスト 文 です",  # 5 tokens
            "japanese"
        )
        assert result

    def test_khmer_short_tokens(self):
        # Khmer with too many short tokens
        result = tv.is_segmentation_ok(
            "hello world test",
            "a b c d e",  # >10% short tokens
            "khmer"
        )
        assert not result

    def test_over_segmentation(self):
        # Too many tokens relative to original
        original = "hello world"  # 2 words
        translation = "a b c d e f g h i j k"  # Way too many tokens
        result = tv.is_segmentation_ok(original, translation, "thai")
        assert not result

    def test_under_segmentation(self):
        # Too few tokens relative to original
        original = "this is a long sentence with many words"  # 8 words
        translation = "ab"  # Only 1 token
        result = tv.is_segmentation_ok(original, translation, "thai")
        assert not result


class TestIsValidTranslation:
    def test_valid_translation(self):
        assert tv.is_valid_translation("Hello, world!")

    def test_calls_text_normalization(self):
        # This is a thin wrapper around text_norm.is_placeholder_translation
        # We trust that module is tested separately
        assert isinstance(tv.is_valid_translation("test"), bool)
