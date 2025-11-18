"""Tokenization helpers for highlight flows."""

from __future__ import annotations

import unicodedata
from typing import List

import regex

# Languages without whitespace boundaries (Chinese, Japanese, Thai, etc.)
_NO_SPACE_SCRIPT_PATTERN = regex.compile(
    r"[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}"
    r"\p{Script=Bopomofo}\p{Script=Nushu}\p{Script=Yi}\p{Script=Thai}"
    r"\p{Script=Lao}\p{Script=Khmer}\p{Script=Myanmar}\p{Script=Tibetan}]"
)

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

    Fallback to grapheme clusters when the payload mixes continuous scripts
    (Chinese, Japanese, Thai, etc.) so each character can be highlighted.
    """

    if not text:
        return []

    whitespace_tokens = [token for token in text.split() if token]
    if len(whitespace_tokens) > 1:
        return whitespace_tokens
    if whitespace_tokens and any(char.isspace() for char in text):
        return whitespace_tokens

    if _NO_SPACE_SCRIPT_PATTERN.search(text):
        grapheme_tokens = [
            match.group()
            for match in _GRAPHEME_PATTERN.finditer(text)
            if not _is_separator(match.group())
        ]
        if grapheme_tokens:
            return grapheme_tokens

    stripped = text.strip()
    if whitespace_tokens:
        return whitespace_tokens
    return [stripped] if stripped else []


__all__ = ["split_highlight_tokens"]
