"""Tokenization helpers for highlight flows."""

from __future__ import annotations

import unicodedata
from typing import List

try:
    # Optional Thai tokenizer; falls back to grapheme splitting when unavailable.
    from pythainlp.tokenize import word_tokenize as _thai_word_tokenize
except Exception:  # pragma: no cover - optional dependency
    _thai_word_tokenize = None

try:
    # Optional Japanese tokenizer via fugashi; falls back to graphemes when unavailable.
    import fugashi

    _jp_tagger = fugashi.Tagger()  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - optional dependency
    fugashi = None
    _jp_tagger = None

try:
    # Optional lightweight Japanese tokenizer.
    from tinysegmenter import TinySegmenter

    _tiny_segmenter = TinySegmenter()
except Exception:  # pragma: no cover - optional dependency
    _tiny_segmenter = None
import regex

# Languages without whitespace boundaries (Chinese, Japanese, Thai, etc.)
_NO_SPACE_SCRIPT_PATTERN = regex.compile(
    r"[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}"
    r"\p{Script=Bopomofo}\p{Script=Nushu}\p{Script=Yi}\p{Script=Thai}"
    r"\p{Script=Lao}\p{Script=Khmer}\p{Script=Myanmar}\p{Script=Tibetan}]"
)

_THAI_PATTERN = regex.compile(r"\p{Script=Thai}")
_MYANMAR_PATTERN = regex.compile(r"\p{Script=Myanmar}")
_JAPANESE_PATTERN = regex.compile(r"[\p{Hiragana}\p{Katakana}\p{Han}]")
_JAPANESE_RUN_PATTERN = regex.compile(
    r"[\p{Han}\p{Hiragana}\p{Katakana}ー]+|[A-Za-z0-9]+|[^\s]"
)
_LATIN_OR_MARKS_PATTERN = regex.compile(r"^[\p{Latin}\p{M}0-9'’-]+$")
_HYPHEN_NORMALIZATION = str.maketrans({"–": "-", "—": "-", "\u2011": "-"})
_GRAPHEME_PATTERN = regex.compile(r"\X")


def _is_separator(grapheme: str) -> bool:
    if not grapheme:
        return True
    if grapheme.isspace():
        return True
    category = unicodedata.category(grapheme[0])
    return category.startswith("Z")


def split_highlight_tokens(text: str) -> List[str]:
    """
    Return highlight tokens handling languages without whitespace boundaries.

    For CJK text with explicit spaces (from LLM translation), the spaces are
    treated as intentional word boundaries and preserved. Morphological
    re-tokenization is only applied when:
    - Text has no spaces (needs segmentation)
    - Text has per-character spacing (needs re-segmentation)

    Fallback to grapheme clusters when the payload mixes continuous scripts
    (Chinese, Japanese, Thai, etc.) so each character can be highlighted.
    """

    if not text:
        return []

    stripped = text.strip()
    whitespace_tokens = [token for token in text.split() if token]

    # Check if text has meaningful space segmentation (>= 2 tokens, avg length > 1 char)
    has_meaningful_spaces = (
        len(whitespace_tokens) >= 2
        and sum(len(tok) for tok in whitespace_tokens) / len(whitespace_tokens) > 1.5
    )

    # For CJK text with explicit meaningful spaces, respect them as word boundaries
    # This handles LLM-generated translations that already have proper segmentation
    if has_meaningful_spaces and _NO_SPACE_SCRIPT_PATTERN.search(stripped):
        # Check if it looks like per-CHARACTER spacing (most tokens are SINGLE char)
        # Chinese words are typically 2+ chars, so 1-char tokens indicate per-char spacing
        single_char_ratio = sum(1 for tok in whitespace_tokens if len(tok) == 1) / len(whitespace_tokens)
        if single_char_ratio < 0.5:
            # Meaningful word-level segmentation - return as-is
            return whitespace_tokens

    # Japanese often arrives with per-character spacing/newlines; re-segment before returning raw whitespace tokens.
    if _JAPANESE_PATTERN.search(stripped):
        # If whitespace tokens look like per-character segmentation, collapse and retokenize.
        looks_char_spaced = bool(
            whitespace_tokens
            and sum(len(tok) <= 2 for tok in whitespace_tokens)
            >= max(1, len(whitespace_tokens) // 2)
        )
        # Only collapse and re-tokenize if spacing looks wrong (per-char or no spaces)
        if looks_char_spaced or len(whitespace_tokens) <= 1:
            compact = "".join(whitespace_tokens) if whitespace_tokens else stripped
            if _jp_tagger is not None:
                try:
                    jp_tokens = [token.surface for token in _jp_tagger(compact) if token.surface.strip()]
                    if len(jp_tokens) > 1:
                        return jp_tokens
                except Exception:  # pragma: no cover - optional helper
                    pass
            if _tiny_segmenter is not None:
                try:
                    seg_tokens = [tok.strip() for tok in _tiny_segmenter.tokenize(compact) if tok.strip()]
                    if len(seg_tokens) > 1:
                        return seg_tokens
                except Exception:  # pragma: no cover - optional helper
                    pass
            jp_run_tokens = [
                match.group() for match in _JAPANESE_RUN_PATTERN.finditer(compact) if match.group().strip()
            ]
            if len(jp_run_tokens) > 1:
                return jp_run_tokens
        if not looks_char_spaced and len(whitespace_tokens) > 1:
            return whitespace_tokens

    if len(whitespace_tokens) > 1:
        return whitespace_tokens
    if whitespace_tokens and any(char.isspace() for char in text):
        return whitespace_tokens

    # Thai: prefer dictionary-based segmentation when available so highlights follow words.
    if _THAI_PATTERN.search(stripped) and _thai_word_tokenize:
        thai_tokens = [tok.strip() for tok in _thai_word_tokenize(stripped) if tok.strip()]
        if len(thai_tokens) > 1:
            return thai_tokens

    # Burmese/Myanmar: use syllable-based segmentation when available.
    if _MYANMAR_PATTERN.search(stripped) and _mm_syllable:
        _mm_splitter = None
        for attr in ("split", "split_syllables", "syllable_break", "sylbreak"):
            candidate = getattr(_mm_syllable, attr, None)
            if callable(candidate):
                _mm_splitter = candidate
                break
        if _mm_splitter:
            try:
                mm_tokens = [tok.strip() for tok in _mm_splitter(stripped) if tok.strip()]
                if len(mm_tokens) > 1:
                    return mm_tokens
            except Exception:  # pragma: no cover - optional helper
                pass

    # Japanese: use fugashi for word segmentation when available so highlights follow tokens.
    if _JAPANESE_PATTERN.search(stripped) and _jp_tagger is not None:
        try:
            jp_tokens = [token.surface for token in _jp_tagger(stripped) if token.surface.strip()]
            if len(jp_tokens) > 1:
                return jp_tokens
        except Exception:  # pragma: no cover - optional helper
            pass

    # Transliteration lines often arrive as hyphen-joined Latin strings; split to match words.
    normalized_hyphen_text = stripped.translate(_HYPHEN_NORMALIZATION)
    if "-" in normalized_hyphen_text and _LATIN_OR_MARKS_PATTERN.match(normalized_hyphen_text):
        hyphen_tokens = [tok for tok in normalized_hyphen_text.split("-") if tok]
        if len(hyphen_tokens) > 1:
            return hyphen_tokens

    if _NO_SPACE_SCRIPT_PATTERN.search(text):
        grapheme_tokens = [
            match.group()
            for match in _GRAPHEME_PATTERN.finditer(text)
            if not _is_separator(match.group())
        ]
        if grapheme_tokens:
            return grapheme_tokens

    if whitespace_tokens:
        return whitespace_tokens
    return [stripped] if stripped else []


__all__ = ["split_highlight_tokens"]
