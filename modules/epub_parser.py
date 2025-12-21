"""Utilities for extracting and preparing text from EPUB sources."""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path
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
SENTENCE_LENGTH_OVERFLOW_RATIO = 1.25


_SMART_QUOTE_TRANSLATION = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }
)


def remove_quotes(text: str) -> str:
    """Normalize smart quotes to their ASCII equivalents instead of stripping."""
    return text.translate(_SMART_QUOTE_TRANSLATION)


def _normalize_href(href: str) -> str:
    cleaned = href.split("#", 1)[0].strip()
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned.lstrip("/")


def _collect_toc_labels(toc: object) -> dict[str, str]:
    labels: dict[str, str] = {}

    def walk(entry: object) -> None:
        if entry is None:
            return
        if isinstance(entry, (list, tuple)):
            if (
                len(entry) == 2
                and not isinstance(entry[0], (str, bytes))
                and not isinstance(entry[1], (str, bytes))
            ):
                walk(entry[0])
                walk(entry[1])
                return
            for item in entry:
                walk(item)
            return

        href = getattr(entry, "href", None)
        title = getattr(entry, "title", None) or getattr(entry, "label", None)
        if isinstance(href, str) and isinstance(title, str):
            key = _normalize_href(href)
            if key and key not in labels:
                labels[key] = title.strip()

        children = getattr(entry, "subitems", None) or getattr(entry, "children", None)
        if children is not None:
            walk(children)

    walk(toc)
    return labels


def _guess_section_title(
    soup: BeautifulSoup,
    item: epub.EpubHtml,
    toc_labels: dict[str, str],
    index: int,
) -> tuple[str, Optional[str]]:
    href = getattr(item, "file_name", None) or ""
    toc_label = toc_labels.get(_normalize_href(str(href))) if href else None
    if toc_label:
        return toc_label, toc_label

    for tag_name in ("h1", "h2", "h3"):
        heading = soup.find(tag_name)
        if heading is not None:
            text = heading.get_text(separator=" ", strip=True)
            if text:
                return text, None

    raw_title = getattr(item, "title", None)
    if isinstance(raw_title, str) and raw_title.strip():
        return raw_title.strip(), None

    fallback = Path(str(href)).stem.replace("_", " ").strip()
    if not fallback:
        fallback = f"Section {index}"
    return fallback, None


def extract_sections_from_epub(
    epub_file: str, *, books_dir: Optional[str] = None
) -> List[dict[str, object]]:
    """Return ordered text sections extracted from an EPUB file."""

    context = cfg.get_runtime_context(None)
    base_dir = books_dir or (context.books_dir if context is not None else None)
    epub_path = cfg.resolve_file_path(epub_file, base_dir)
    if not epub_path or not epub_path.exists():
        raise FileNotFoundError(f"EPUB file '{epub_file}' could not be found.")

    try:
        book = epub.read_epub(str(epub_path))
    except Exception as exc:  # pragma: no cover - passthrough to main flow
        logger.error("Error reading EPUB file '%s': %s", epub_path, exc)
        sys.exit(1)

    toc_labels = _collect_toc_labels(getattr(book, "toc", None))
    spine_index: dict[str, int] = {}
    for idx, entry in enumerate(getattr(book, "spine", []) or []):
        if isinstance(entry, tuple):
            item_id = entry[0]
        else:
            item_id = entry
        if isinstance(item_id, str) and item_id and item_id not in spine_index:
            spine_index[item_id] = idx

    sections: List[dict[str, object]] = []
    section_index = 0
    for item in book.get_items():
        if not isinstance(item, epub.EpubHtml):
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        if not text:
            continue
        section_index += 1
        href = getattr(item, "file_name", None)
        if not href:
            continue
        title, toc_label = _guess_section_title(soup, item, toc_labels, section_index)
        entry: dict[str, object] = {
            "id": f"section-{section_index:04d}",
            "title": title,
            "href": str(href),
            "text": text,
        }
        item_id = getattr(item, "get_id", lambda: None)()
        if isinstance(item_id, str) and item_id in spine_index:
            entry["spine_index"] = spine_index[item_id]
        if toc_label:
            entry["toc_label"] = toc_label
        sections.append(entry)
    return sections


def extract_text_from_epub(epub_file: str, books_dir: Optional[str] = None) -> str:
    """Read an EPUB file and return its textual content."""
    context = cfg.get_runtime_context(None)
    base_dir = books_dir or (context.books_dir if context is not None else None)
    epub_path = cfg.resolve_file_path(epub_file, base_dir)
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
        final_sentences.extend(
            _split_segment_with_word_limit(words, max_words=max_words)
        )
    return final_sentences


def _split_segment_with_word_limit(
    words: List[str], *, max_words: int
) -> List[str]:
    """Split a word list while avoiding tiny trailing fragments.

    Keeps chunks at ``max_words`` where possible but allows the final chunk to
    merge with the previous one when doing so would avoid creating a 1-2 word
    tail and the combined chunk stays under ``SENTENCE_LENGTH_OVERFLOW_RATIO``
    of ``max_words`` (default 125%).
    """

    if not words:
        return []

    chunks: List[List[str]] = []
    max_with_overflow = max(
        max_words, int(max_words * SENTENCE_LENGTH_OVERFLOW_RATIO)
    )
    index = 0
    while index < len(words):
        remaining = len(words) - index
        if chunks:
            previous_len = len(chunks[-1])
            if previous_len + remaining <= max_with_overflow:
                chunks[-1].extend(words[index:])
                break

        chunk = words[index : index + max_words]
        chunks.append(chunk)
        index += max_words

    return [" ".join(chunk) for chunk in chunks if chunk]


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
    "extract_sections_from_epub",
    "extract_text_from_epub",
    "remove_quotes",
    "split_text_into_sentences",
    "split_text_into_sentences_no_refine",
]
