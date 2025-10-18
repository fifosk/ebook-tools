"""Utilities for extracting and preparing text from EPUB sources."""

from __future__ import annotations

import re
import sys
import warnings
from typing import Iterable, List, Optional

from bs4 import BeautifulSoup
from ebooklib import epub

from . import config_manager as cfg
from . import logging_manager as log_mgr

warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib.epub")
warnings.filterwarnings("ignore", category=FutureWarning, module="ebooklib.epub")

logger = log_mgr.logger

DEFAULT_MAX_WORDS = 18
DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON = False


def remove_quotes(text: str) -> str:
    """Remove smart quotes from the provided text."""
    for quote in ["“", "”", "‘", "’"]:
        text = text.replace(quote, "")
    return text


def extract_text_from_epub(epub_file: str, books_dir: Optional[str] = None) -> str:
    """Read an EPUB file and return its textual content."""
    epub_path = cfg.resolve_file_path(epub_file, books_dir or cfg.BOOKS_DIR)
    if not epub_path or not epub_path.exists():
        raise FileNotFoundError(f"EPUB file '{epub_file}' could not be found.")

    try:
        book = epub.read_epub(str(epub_path))
    except Exception as exc:  # pragma: no cover - passthrough to main flow
        logger.error("Error reading EPUB file '%s': %s", epub_path, exc)
        sys.exit(1)

    text_content = ""
    for item in book.get_items():
        if isinstance(item, epub.EpubHtml):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text_content += soup.get_text(separator=" ", strip=True) + "\n"
    return text_content


def split_text_into_sentences_no_refine(
    text: str,
    *,
    extend_split_with_comma_semicolon: bool = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
) -> List[str]:
    """Split text into sentences without refinement or word limits."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.?!])[\"\']\s+", r"\1 ", text)
    pattern = re.compile(
        r"(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!Jr\.)(?<!Sr\.)"
        r"(?<!Prof\.)(?<!St\.)(?<!e\.g\.)(?<!i\.e\.)(?<!vs\.)(?<!etc\.)"
        r"(?<=[.?!])\s+(?=[A-Z“])"
    )
    sentences = [s.strip() for s in pattern.split(text) if s.strip()]
    if extend_split_with_comma_semicolon:
        new_sentences: List[str] = []
        for sentence in sentences:
            parts = re.split(r"[;,]\s*", sentence)
            new_sentences.extend([p.strip() for p in parts if p.strip()])
        return new_sentences
    return sentences


def _refine_and_split_sentence(
    sentence: str,
    *,
    max_words: int,
    extend_split_with_comma_semicolon: bool,
) -> List[str]:
    segments: List[str] = []
    pattern_brackets = re.compile(r"\([^)]*\)")
    pos = 0
    for match in pattern_brackets.finditer(sentence):
        before = sentence[pos : match.start()].strip()
        if before:
            segments.append(before)
        bracket_text = match.group().strip("()").strip()
        if bracket_text:
            segments.append(bracket_text)
        pos = match.end()
    remainder = sentence[pos:].strip()
    if remainder:
        segments.append(remainder)
    if not segments:
        segments = [sentence]

    refined_segments: List[str] = []
    pattern_quotes = re.compile(r'"([^"]+)"')
    for seg in segments:
        pos = 0
        parts: List[str] = []
        for match in pattern_quotes.finditer(seg):
            before = seg[pos : match.start()].strip()
            if before:
                parts.append(before)
            quote_text = match.group(1).strip()
            if quote_text:
                parts.append(quote_text)
            pos = match.end()
        remainder = seg[pos:].strip()
        if remainder:
            parts.append(remainder)
        if parts:
            refined_segments.extend(parts)
        else:
            refined_segments.append(seg)

    final_segments: List[str] = []
    for seg in refined_segments:
        if seg.startswith("- "):
            final_segments.append(seg[2:].strip())
        else:
            final_segments.append(seg)

    if extend_split_with_comma_semicolon:
        extended: List[str] = []
        for seg in final_segments:
            parts = re.split(r"[;,]\s*", seg)
            extended.extend([p.strip() for p in parts if p.strip()])
        final_segments = extended

    final_sentences: List[str] = []
    for seg in final_segments:
        words = seg.split()
        if len(words) > max_words:
            for index in range(0, len(words), max_words):
                final_sentences.append(" ".join(words[index : index + max_words]))
        else:
            final_sentences.append(seg)
    return final_sentences


def _merge_single_char_sentences(sentences: Iterable[str]) -> List[str]:
    sentences = list(sentences)
    if not sentences:
        return sentences
    merged = [sentences[0]]
    for sentence in sentences[1:]:
        if len(sentence.strip()) == 1:
            merged[-1] = merged[-1] + " " + sentence
        else:
            merged.append(sentence)
    return merged


def split_text_into_sentences(
    text: str,
    *,
    max_words: int = DEFAULT_MAX_WORDS,
    extend_split_with_comma_semicolon: bool = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
) -> List[str]:
    """Split text into refined sentences respecting punctuation and word limits."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([.?!])[\"\']\s+", r"\1 ", text)
    pattern = re.compile(
        r"(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!Jr\.)(?<!Sr\.)"
        r"(?<!Prof\.)(?<!St\.)(?<!e\.g\.)(?<!i\.e\.)(?<!vs\.)(?<!etc\.)"
        r"(?<=[.?!])\s+(?=[A-Z“])"
    )
    raw_segments = pattern.split(text)
    final: List[str] = []
    for sentence in raw_segments:
        sentence = sentence.replace("\n", " ").strip()
        if not sentence:
            continue
        if (sentence.startswith('"') and sentence.endswith('"')) or (
            sentence.startswith("“") and sentence.endswith("”")
        ):
            final.append(sentence)
        else:
            refined = _refine_and_split_sentence(
                sentence,
                max_words=max_words,
                extend_split_with_comma_semicolon=extend_split_with_comma_semicolon,
            )
            final.extend(refined)
    return _merge_single_char_sentences(final)


__all__ = [
    "DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON",
    "DEFAULT_MAX_WORDS",
    "extract_text_from_epub",
    "remove_quotes",
    "split_text_into_sentences",
    "split_text_into_sentences_no_refine",
]
