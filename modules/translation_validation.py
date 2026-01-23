"""Translation validation and quality checking utilities.

This module provides functions to validate translation quality, detect common
issues, and ensure translations meet expected standards.
"""

from __future__ import annotations

from typing import Optional

import regex

from modules import language_policies, text_normalization as text_norm
from modules.text import split_highlight_tokens

# Pattern matching
_LATIN_LETTER_PATTERN = regex.compile(r"\p{Latin}")
_NON_LATIN_LETTER_PATTERN = regex.compile(r"(?!\p{Latin})\p{L}")
_ZERO_WIDTH_SPACE_PATTERN = regex.compile(r"[\u200B\u200C\u200D\u2060]+")

# Diacritic patterns for languages that require them
_DIACRITIC_PATTERNS = {
    "arabic": {
        "aliases": ("arabic", "ar"),
        "pattern": regex.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]"),
        "label": "Arabic diacritics (tashkil)",
        "script_pattern": regex.compile(r"[\u0600-\u06FF]"),
    },
    "hebrew": {
        "aliases": ("hebrew", "he", "iw"),
        "pattern": regex.compile(r"[\u0591-\u05C7]"),
        "label": "Hebrew niqqud",
        "script_pattern": regex.compile(r"[\u0590-\u05FF]"),
    },
}

# Languages that require word segmentation
_SEGMENTATION_LANGS = {
    # Thai family
    "thai",
    "th",
    # Khmer / Cambodian
    "khmer",
    "km",
    "cambodian",
    # Burmese / Myanmar
    "burmese",
    "myanmar",
    "my",
    # Japanese
    "japanese",
    "ja",
    "日本語",
    # Korean (should already have spaces, but enforce retries if omitted)
    "korean",
    "ko",
    # Chinese (added cautiously; can be removed if character-level is preferred)
    "chinese",
    "zh",
    "zh-cn",
    "zh-tw",
}


def is_valid_translation(text: str) -> bool:
    """Check if translation text is valid (not a placeholder)."""
    return not text_norm.is_placeholder_translation(text)


def letter_count(value: str) -> int:
    """Count the number of letter characters in a string."""
    return sum(1 for char in value if char.isalpha())


def has_non_latin_letters(value: str) -> bool:
    """Check if string contains non-Latin letters."""
    return bool(_NON_LATIN_LETTER_PATTERN.search(value))


def latin_fraction(value: str) -> float:
    """Calculate the fraction of Latin letters vs total letters.

    Returns:
        Float between 0.0 and 1.0, where 1.0 means all letters are Latin.
        Returns 0.0 if there are no letters.
    """
    if not value:
        return 0.0
    latin = len(_LATIN_LETTER_PATTERN.findall(value))
    non_latin = len(_NON_LATIN_LETTER_PATTERN.findall(value))
    total = latin + non_latin
    if total == 0:
        return 0.0
    return latin / total


def is_probable_transliteration(
    original_sentence: str, translation_text: str, target_language: str
) -> bool:
    """Check if translation is likely a transliteration instead of translation.

    Returns True when the response likely contains only a Latin transliteration
    even though the target language expects non-Latin script output.

    Args:
        original_sentence: Original text in source language
        translation_text: Translated text to check
        target_language: Expected target language code

    Returns:
        True if translation appears to be transliteration
    """
    if not translation_text or not has_non_latin_letters(original_sentence):
        return False
    if not language_policies.is_non_latin_language_hint(target_language):
        return False
    return latin_fraction(translation_text) >= 0.6


def is_translation_too_short(
    original_sentence: str, translation_text: str
) -> bool:
    """Check if translation is suspiciously shorter than original.

    Heuristic for truncated translations. Skip very short inputs to avoid
    over-triggering on single words.

    Args:
        original_sentence: Original text
        translation_text: Translated text to check

    Returns:
        True if translation appears truncated
    """
    translation_text = translation_text or ""
    original_letters = letter_count(original_sentence)
    if original_letters <= 12:
        return False
    translation_letters = letter_count(translation_text)
    if translation_letters == 0:
        return True
    if original_letters >= 80 and translation_letters < 15:
        return True
    ratio = translation_letters / float(original_letters)
    return original_letters >= 30 and ratio < 0.28


def missing_required_diacritics(
    translation_text: str, target_language: str
) -> tuple[bool, Optional[str]]:
    """Check if translation is missing required diacritics.

    Returns (True, label) when the target language expects diacritics but none
    are present in the translation.

    Args:
        translation_text: Translated text to check
        target_language: Expected target language code

    Returns:
        Tuple of (is_missing, diacritic_label)
    """
    target_lower = (target_language or "").lower()
    for requirement in _DIACRITIC_PATTERNS.values():
        if any(alias in target_lower for alias in requirement["aliases"]):
            pattern = requirement["pattern"]
            script_pattern = requirement.get("script_pattern")
            if script_pattern and not script_pattern.search(translation_text or ""):
                # Skip if the translation doesn't use the expected script; avoids
                # misfiring when target_language is mismatched.
                return False, None
            if not pattern.search(translation_text or ""):
                return True, requirement["label"]
            return False, None
    return False, None


def script_counts(value: str) -> dict[str, int]:
    """Get counts of characters per script block.

    Returns:
        Dictionary mapping script names to character counts
    """
    return language_policies.script_counts(value)


def unexpected_script_used(
    translation_text: str, target_language: str
) -> tuple[bool, Optional[str]]:
    """Check if translation uses unexpected script for target language.

    Returns (True, label) when the translation contains non-Latin script but
    does not sufficiently include the expected script for the target language.

    Args:
        translation_text: Translated text to check
        target_language: Expected target language code

    Returns:
        Tuple of (is_unexpected, script_label)
    """
    candidate = translation_text or ""
    if not candidate:
        return False, None
    if not _NON_LATIN_LETTER_PATTERN.search(candidate):
        return False, None

    policy = language_policies.script_policy_for(target_language)
    if policy is None:
        return False, None

    script_distribution = script_counts(candidate)
    total_non_latin = len(_NON_LATIN_LETTER_PATTERN.findall(candidate))

    expected_pattern = policy.script_pattern
    expected_label = policy.script_label
    expected_matches = expected_pattern.findall(candidate)
    expected_count = len(expected_matches)
    if expected_count == 0:
        return True, expected_label
    if total_non_latin > 0:
        expected_ratio = expected_count / float(total_non_latin)
        other_count = total_non_latin - expected_count

        # Reject when other scripts meaningfully appear (e.g., Georgian/Tamil in Kannada)
        # or when the expected script is not clearly dominant.
        dominant_script = max(
            script_distribution.items(), key=lambda item: item[1], default=(None, 0)
        )
        dominant_label, dominant_count = dominant_script

        if expected_ratio < 0.85 or other_count > max(2, expected_count * 0.1):
            offenders = [
                label
                for label, count in script_distribution.items()
                if label != expected_label and count > 0
            ]
            offender_label = f" (found {', '.join(offenders)})" if offenders else ""
            return True, f"{expected_label}{offender_label}"

        if dominant_label and dominant_label != expected_label and dominant_count > expected_count:
            return True, f"{expected_label} (found {dominant_label})"
    return False, None


def is_segmentation_ok(
    original_sentence: str,
    translation: str,
    target_language: str,
    *,
    translation_text: Optional[str] = None,
) -> bool:
    """Check if translation has proper word segmentation for target language.

    Require word-like spacing for select languages; otherwise consider invalid.
    We bypass this check when the original sentence is a single word to avoid
    retry loops on very short content.

    Args:
        original_sentence: Original text
        translation: Translated text (may include transliteration)
        target_language: Expected target language code
        translation_text: Override for translation portion only

    Returns:
        True if segmentation is acceptable
    """
    def _segmentation_thresholds(lang: str, source_words: int) -> tuple[int, int]:
        if lang in {"khmer", "km", "cambodian"}:
            # Khmer: enforce closer parity to source word count.
            required_min = max(2, int(source_words * 0.6))
            max_reasonable = max(source_words * 2, required_min + 1)
            return required_min, max_reasonable
        return max(4, int(source_words * 0.6)), source_words * 4

    lang = (target_language or "").strip().lower()
    if lang not in _SEGMENTATION_LANGS:
        return True
    original_word_count = max(len(original_sentence.split()), 1)
    if original_word_count <= 1:
        return True
    candidate = translation_text or translation
    candidate = _ZERO_WIDTH_SPACE_PATTERN.sub(" ", candidate)
    tokens = split_highlight_tokens(candidate)
    token_count = len(tokens)
    if token_count <= 1:
        return False
    if lang in {"khmer", "km", "cambodian"} and token_count > 2:
        short_tokens = sum(1 for token in tokens if len(token) <= 2)
        if short_tokens / float(token_count) > 0.1:
            return False
    # Accept if segmentation yields enough tokens and isn't clearly over-split.
    required_min, max_reasonable = _segmentation_thresholds(lang, original_word_count)
    if token_count < required_min:
        return False
    if token_count > max_reasonable:
        return False
    return True
