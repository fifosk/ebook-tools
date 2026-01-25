"""Token alignment utilities for CJK translation/transliteration tracks.

This module provides post-processing functions to align token counts between
translation and transliteration tracks when the LLM output doesn't match perfectly.
"""

from __future__ import annotations

import regex
from typing import List, Optional, Tuple

from modules.text.tokenization import split_highlight_tokens

# Pattern for detecting hyphen-joined syllables in transliteration
_HYPHEN_SYLLABLE_PATTERN = regex.compile(r"(\w+(?:-\w+)+)")

# Pattern for detecting CJK characters
_CJK_PATTERN = regex.compile(
    r"[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}"
    r"\p{Script=Thai}\p{Script=Lao}\p{Script=Khmer}\p{Script=Myanmar}]"
)

# Pattern for splitting by spaces while preserving structure
_SPACE_SPLIT_PATTERN = regex.compile(r"\s+")


def count_tokens(text: str) -> int:
    """Count the number of tokens in text using the standard tokenizer."""
    if not text:
        return 0
    return len(split_highlight_tokens(text))


def align_token_counts(
    translation: str,
    transliteration: str,
    target_language: str,
    *,
    max_adjustments: int = 50,
) -> Tuple[str, str, bool]:
    """Attempt to align token counts between translation and transliteration.

    This function tries various strategies to make the token counts match:
    1. Smart syllable grouping based on translation character counts (best for CJK)
    2. Join hyphenated syllables in transliteration to reduce token count
    3. Split compound transliterations to increase token count
    4. Merge adjacent short translation tokens to reduce count

    Args:
        translation: The translated text (in target script)
        transliteration: The transliteration (in Latin script)
        target_language: Target language code
        max_adjustments: Maximum number of adjustment iterations

    Returns:
        Tuple of (aligned_translation, aligned_transliteration, was_modified)
    """
    if not translation or not transliteration:
        return translation, transliteration, False

    trans_tokens = split_highlight_tokens(translation)
    translit_tokens = split_highlight_tokens(transliteration)

    trans_count = len(trans_tokens)
    translit_count = len(translit_tokens)

    # Already aligned
    if trans_count == translit_count:
        return translation, transliteration, False

    # For CJK languages with more transliteration than translation tokens,
    # try smart syllable grouping first (best approach for pinyin, romaji, etc.)
    if translit_count > trans_count and _CJK_PATTERN.search(translation):
        aligned_translit = _smart_syllable_grouping(
            trans_tokens, translit_tokens, target_language
        )
        if aligned_translit and count_tokens(aligned_translit) == trans_count:
            return translation, aligned_translit, True

    # Try to align by adjusting transliteration (usually more flexible)
    aligned_translit, translit_modified = _align_transliteration(
        transliteration,
        trans_count,
        target_language,
        max_adjustments=max_adjustments,
    )

    if translit_modified:
        new_translit_count = count_tokens(aligned_translit)
        if new_translit_count == trans_count:
            return translation, aligned_translit, True

    # Try to align by adjusting translation (CJK grouping)
    aligned_trans, trans_modified = _align_translation(
        translation,
        translit_count,
        target_language,
        max_adjustments=max_adjustments,
    )

    if trans_modified:
        new_trans_count = count_tokens(aligned_trans)
        if new_trans_count == translit_count:
            return aligned_trans, transliteration, True

    # Both modified but still not aligned - try combined approach
    if translit_modified and trans_modified:
        aligned_translit2, _ = _align_transliteration(
            transliteration,
            count_tokens(aligned_trans),
            target_language,
            max_adjustments=max_adjustments,
        )
        if count_tokens(aligned_trans) == count_tokens(aligned_translit2):
            return aligned_trans, aligned_translit2, True

    # Return best effort - prefer modified transliteration if closer
    trans_diff = abs(trans_count - translit_count)
    if translit_modified:
        new_translit_count = count_tokens(aligned_translit)
        new_diff = abs(trans_count - new_translit_count)
        if new_diff < trans_diff:
            return translation, aligned_translit, True

    if trans_modified:
        new_trans_count = count_tokens(aligned_trans)
        new_diff = abs(new_trans_count - translit_count)
        if new_diff < trans_diff:
            return aligned_trans, transliteration, True

    return translation, transliteration, False


def _smart_syllable_grouping(
    trans_tokens: List[str],
    translit_tokens: List[str],
    target_language: str,
) -> Optional[str]:
    """Group transliteration syllables based on translation word character counts.

    For CJK languages, each character typically maps to one syllable in pinyin/romaji.
    We use the character count of each translation token to determine how many
    syllables to group together.

    Example:
        trans_tokens = ["罗谢", "带领", "科勒"]  (2, 2, 2 chars)
        translit_tokens = ["luo", "xie", "dai", "ling", "ke", "le"]
        Result: "luo-xie dai-ling ke-le"

    Args:
        trans_tokens: Translation tokens (CJK text)
        translit_tokens: Transliteration tokens (syllables)
        target_language: Target language code

    Returns:
        Aligned transliteration string, or None if alignment not possible
    """
    # Count CJK characters in each translation token
    char_counts = []
    for token in trans_tokens:
        cjk_count = len(_CJK_PATTERN.findall(token))
        # Use at least 1 for non-CJK tokens (punctuation, etc.)
        char_counts.append(max(1, cjk_count))

    total_expected = sum(char_counts)

    # If syllable count doesn't match character count, this method won't work
    if len(translit_tokens) != total_expected:
        # Try partial matching - round up/down as needed
        if len(translit_tokens) < total_expected:
            return None

    # Group syllables based on character counts
    grouped_translit = []
    syllable_idx = 0
    for count in char_counts:
        end_idx = min(syllable_idx + count, len(translit_tokens))
        syllables = translit_tokens[syllable_idx:end_idx]
        if syllables:
            grouped_translit.append("-".join(syllables))
        syllable_idx = end_idx

    # Handle any remaining syllables
    if syllable_idx < len(translit_tokens):
        remaining = translit_tokens[syllable_idx:]
        if grouped_translit:
            # Append to last group
            grouped_translit[-1] = grouped_translit[-1] + "-" + "-".join(remaining)
        else:
            grouped_translit.append("-".join(remaining))

    return " ".join(grouped_translit) if grouped_translit else None


def _align_transliteration(
    transliteration: str,
    target_count: int,
    target_language: str,
    *,
    max_adjustments: int = 50,
) -> Tuple[str, bool]:
    """Adjust transliteration to match target token count.

    Strategies:
    - If too many tokens: join adjacent syllables with hyphens
    - If too few tokens: split at hyphens

    Args:
        transliteration: The transliteration text
        target_count: Desired token count
        target_language: Target language code
        max_adjustments: Maximum adjustment iterations

    Returns:
        Tuple of (adjusted_transliteration, was_modified)
    """
    current = transliteration
    current_tokens = split_highlight_tokens(current)
    current_count = len(current_tokens)

    if current_count == target_count:
        return current, False

    modified = False

    # Too many tokens - join adjacent syllables with hyphens
    if current_count > target_count:
        tokens = list(current_tokens)
        adjustments_needed = current_count - target_count

        for _ in range(min(max_adjustments, adjustments_needed)):
            if len(tokens) <= target_count:
                break

            # Find best pair to join (prefer short adjacent tokens that look like syllables)
            best_join_idx = -1
            best_score = float("inf")

            for i in range(len(tokens) - 1):
                tok1 = tokens[i]
                tok2 = tokens[i + 1]

                # Skip if already hyphenated at this position
                if tok1.endswith("-") or tok2.startswith("-"):
                    continue

                # Prefer joining short tokens that look like pinyin syllables
                # (2-4 chars each, all lowercase alpha)
                is_syllable_like = (
                    len(tok1) <= 6
                    and len(tok2) <= 6
                    and tok1.replace("-", "").isalpha()
                    and tok2.replace("-", "").isalpha()
                )

                if is_syllable_like:
                    # Score: prefer shorter combinations
                    combined_len = len(tok1) + len(tok2)
                    if combined_len < best_score:
                        best_score = combined_len
                        best_join_idx = i

            if best_join_idx >= 0:
                tokens[best_join_idx] = f"{tokens[best_join_idx]}-{tokens[best_join_idx + 1]}"
                del tokens[best_join_idx + 1]
                modified = True
            else:
                # No good syllable-like pairs found - just join the first pair
                if len(tokens) > target_count:
                    tokens[0] = f"{tokens[0]}-{tokens[1]}"
                    del tokens[1]
                    modified = True
                else:
                    break

        if modified:
            current = " ".join(tokens)

    # Too few tokens - try splitting at hyphens
    elif current_count < target_count:
        for _ in range(min(max_adjustments, target_count - current_count)):
            tokens = split_highlight_tokens(current)
            if len(tokens) >= target_count:
                break

            # Find hyphenated token to split
            split_done = False
            new_tokens = []
            for token in tokens:
                if "-" in token and not split_done and len(new_tokens) < target_count:
                    parts = token.split("-", 1)
                    new_tokens.extend(parts)
                    split_done = True
                    modified = True
                else:
                    new_tokens.append(token)

            if split_done:
                current = " ".join(new_tokens)
            else:
                break

    return current, modified


def _align_translation(
    translation: str,
    target_count: int,
    target_language: str,
    *,
    max_adjustments: int = 5,
) -> Tuple[str, bool]:
    """Adjust translation to match target token count.

    For CJK languages, this attempts to re-segment by grouping characters.

    Args:
        translation: The translated text
        target_count: Desired token count
        target_language: Target language code
        max_adjustments: Maximum adjustment iterations

    Returns:
        Tuple of (adjusted_translation, was_modified)
    """
    # Only apply to CJK languages
    lang = (target_language or "").strip().lower()
    if not _CJK_PATTERN.search(translation):
        return translation, False

    current_tokens = split_highlight_tokens(translation)
    current_count = len(current_tokens)

    if current_count == target_count:
        return translation, False

    modified = False

    # Too many tokens - try merging adjacent short tokens
    if current_count > target_count:
        tokens = list(current_tokens)
        for _ in range(min(max_adjustments, current_count - target_count)):
            if len(tokens) <= target_count:
                break

            # Find best pair of short adjacent tokens to merge
            best_merge_idx = -1
            best_combined_len = float("inf")

            for i in range(len(tokens) - 1):
                # Prefer merging very short tokens (1-2 chars)
                if len(tokens[i]) <= 2 and len(tokens[i + 1]) <= 2:
                    combined_len = len(tokens[i]) + len(tokens[i + 1])
                    if combined_len < best_combined_len:
                        best_combined_len = combined_len
                        best_merge_idx = i

            if best_merge_idx >= 0:
                tokens[best_merge_idx] = f"{tokens[best_merge_idx]}{tokens[best_merge_idx + 1]}"
                del tokens[best_merge_idx + 1]
                modified = True
            else:
                break

        if modified:
            return " ".join(tokens), True

    # Too few tokens - harder to split CJK without linguistic knowledge
    # This would require morphological analysis, so we don't attempt it here
    return translation, False


def force_align_by_position(
    translation: str,
    transliteration: str,
    target_language: str,
) -> Tuple[List[Tuple[str, str]], bool]:
    """Force align tokens by position, distributing extras as needed.

    When token counts don't match, this creates a mapping by:
    - Pairing tokens by position
    - Distributing extra tokens from the longer list across the shorter

    Args:
        translation: The translated text
        transliteration: The transliteration text
        target_language: Target language code

    Returns:
        Tuple of (list of (trans_token, translit_token) pairs, was_truncated)
    """
    trans_tokens = split_highlight_tokens(translation)
    translit_tokens = split_highlight_tokens(transliteration)

    if not trans_tokens or not translit_tokens:
        return [], False

    trans_count = len(trans_tokens)
    translit_count = len(translit_tokens)

    # Already aligned
    if trans_count == translit_count:
        return list(zip(trans_tokens, translit_tokens)), False

    pairs: List[Tuple[str, str]] = []

    if trans_count > translit_count:
        # More translation tokens - group translation tokens per transliteration
        ratio = trans_count / translit_count
        trans_idx = 0
        for i, translit_token in enumerate(translit_tokens):
            # Calculate how many translation tokens to group
            next_trans_idx = min(int((i + 1) * ratio + 0.5), trans_count)
            grouped_trans = " ".join(trans_tokens[trans_idx:next_trans_idx])
            pairs.append((grouped_trans, translit_token))
            trans_idx = next_trans_idx
    else:
        # More transliteration tokens - group transliteration per translation
        ratio = translit_count / trans_count
        translit_idx = 0
        for i, trans_token in enumerate(trans_tokens):
            next_translit_idx = min(int((i + 1) * ratio + 0.5), translit_count)
            grouped_translit = "-".join(translit_tokens[translit_idx:next_translit_idx])
            pairs.append((trans_token, grouped_translit))
            translit_idx = next_translit_idx

    return pairs, True


__all__ = [
    "align_token_counts",
    "count_tokens",
    "force_align_by_position",
]
