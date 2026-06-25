"""Utilities for extracting and preparing text from EPUB sources."""

from __future__ import annotations

import re
import warnings
from collections.abc import Iterable as IterableABC
from pathlib import Path
from typing import Iterable, List, Optional

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from . import config_manager as cfg
from . import logging_manager as log_mgr

warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib.epub")
warnings.filterwarnings("ignore", category=FutureWarning, module="ebooklib.epub")

logger = log_mgr.logger

DEFAULT_MAX_WORDS = 18
DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON = False
SENTENCE_SPLITTER_VERSION = "regex-v5"
DEFAULT_SENTENCE_SPLITTER_MODE = "regex"
MODERN_SENTENCE_SPLITTER_VERSION = f"modern-syntok-v1+{SENTENCE_SPLITTER_VERSION}-fallback"
SENTENCE_LENGTH_OVERFLOW_RATIO = 1.25
_SENTENCE_BOUNDARY_MARKER = "<EBOOK_SENTENCE_BOUNDARY>"
_NON_LATIN_SENTENCE_PUNCTUATION = "。！？؟۔।॥"
_CLOSING_SENTENCE_QUOTES = "\"'”’」』）】〕〉》)"
_TRAILING_PUNCTUATION_RE = re.compile(rf"^[.?!,:;{_NON_LATIN_SENTENCE_PUNCTUATION}]+$")
_TERMINAL_SENTENCE_RE = re.compile(
    rf"[.?!{re.escape(_NON_LATIN_SENTENCE_PUNCTUATION)}][{re.escape(_CLOSING_SENTENCE_QUOTES)}]*$"
)
_SUPPORTED_SENTENCE_SPLITTER_MODES = {"regex", "modern"}


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


def normalize_sentence_splitter_mode(mode: str | None) -> str:
    """Return a supported sentence splitter mode, defaulting to regex."""

    if not isinstance(mode, str):
        return DEFAULT_SENTENCE_SPLITTER_MODE
    normalized = mode.strip().lower()
    if normalized in _SUPPORTED_SENTENCE_SPLITTER_MODES:
        return normalized
    return DEFAULT_SENTENCE_SPLITTER_MODE


def sentence_splitter_version_for_mode(mode: str | None) -> str:
    """Return the cache version identifier for a splitter mode."""

    normalized = normalize_sentence_splitter_mode(mode)
    if normalized == "modern":
        return MODERN_SENTENCE_SPLITTER_VERSION
    return SENTENCE_SPLITTER_VERSION


def _preserve_quoted_sentence_boundaries(text: str) -> str:
    """Mark punctuation+quote boundaries without dropping the closing quote."""

    closing_chars = re.escape(_CLOSING_SENTENCE_QUOTES)
    return re.sub(
        rf"([.?!])([{closing_chars}])\s+(?=[A-Za-z“‘])",
        rf"\1\2{_SENTENCE_BOUNDARY_MARKER}",
        text,
    )


def _preserve_non_latin_sentence_boundaries(text: str) -> str:
    """Mark boundaries for sentence punctuation that does not rely on casing."""

    boundary_chars = re.escape(_NON_LATIN_SENTENCE_PUNCTUATION)
    closing_chars = re.escape(_CLOSING_SENTENCE_QUOTES)
    return re.sub(
        rf"([{boundary_chars}][{closing_chars}]*)\s*(?=[^\s{boundary_chars}{closing_chars}])",
        rf"\1{_SENTENCE_BOUNDARY_MARKER}",
        text,
    )


def _mark_sentence_boundaries(text: str) -> str:
    text = _preserve_quoted_sentence_boundaries(text)
    return _preserve_non_latin_sentence_boundaries(text)


def _split_marked_sentence_boundaries(text: str, pattern: re.Pattern[str]) -> List[str]:
    segments: List[str] = []
    for part in text.split(_SENTENCE_BOUNDARY_MARKER):
        segments.extend(pattern.split(part))
    return segments


def _append_refined_segment(segments: List[str], value: str) -> None:
    value = value.strip()
    if not value:
        return
    if segments and _TRAILING_PUNCTUATION_RE.fullmatch(value):
        segments[-1] = segments[-1] + value
        return
    segments.append(value)


def _split_on_comma_semicolon_preserving_delimiters(text: str) -> List[str]:
    parts: List[str] = []
    start = 0
    for match in re.finditer(r"[;,]\s*", text):
        part = text[start : match.start()].strip()
        if part:
            parts.append(part + match.group()[0])
        start = match.end()
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


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


def _epub_item_id(item: object) -> Optional[str]:
    candidate = getattr(item, "get_id", lambda: None)()
    return candidate if isinstance(candidate, str) and candidate else None


def _epub_item_properties(item: object) -> set[str]:
    raw = getattr(item, "properties", None)
    if raw is None:
        raw = getattr(item, "get_properties", lambda: [])()
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, IterableABC):
        return {str(value) for value in raw if value is not None}
    return set()


def _is_navigation_document(item: object, soup: BeautifulSoup) -> bool:
    nav_class = getattr(epub, "EpubNav", None)
    if nav_class is not None and isinstance(item, nav_class):
        return True

    item_type = getattr(item, "get_type", lambda: None)()
    if item_type == ebooklib.ITEM_NAVIGATION:
        return True

    if "nav" in _epub_item_properties(item):
        return True

    href = getattr(item, "file_name", None)
    filename = Path(str(href)).name.lower() if href else ""
    if filename in {"nav.xhtml", "nav.html", "toc.xhtml", "toc.html"}:
        if soup.find("nav") is not None:
            return True

    for nav in soup.find_all("nav"):
        nav_type = nav.get("epub:type") or nav.get("type")
        if isinstance(nav_type, str) and any(
            token in nav_type.lower() for token in ("toc", "landmarks", "page-list")
        ):
            return True

    return False


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
        raise RuntimeError("EPUB file could not be read.") from exc

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
    ordered_items: list[tuple[tuple[int, int], epub.EpubHtml]] = []
    for fallback_index, item in enumerate(book.get_items()):
        if not isinstance(item, epub.EpubHtml):
            continue
        item_id = _epub_item_id(item)
        spine_pos = spine_index.get(item_id or "")
        sort_key = (0, spine_pos) if spine_pos is not None else (1, fallback_index)
        ordered_items.append((sort_key, item))

    section_index = 0
    for _sort_key, item in sorted(ordered_items, key=lambda entry: entry[0]):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        if _is_navigation_document(item, soup):
            continue
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
        item_id = _epub_item_id(item)
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
        raise RuntimeError("EPUB file could not be read.") from exc

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
    text = _mark_sentence_boundaries(text)
    pattern = re.compile(
        r"(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!Jr\.)(?<!Sr\.)"
        r"(?<!Prof\.)(?<!St\.)(?<!e\.g\.)(?<!i\.e\.)(?<!vs\.)(?<!etc\.)"
        r"(?<!\b[A-Za-z]\.)"
        r"(?:(?<=[?!])\s+(?=[A-Za-z\"“‘])|(?<!\.\.\.)(?<=[.])\s+(?=[A-Za-z\"“‘]))"
    )
    sentences = [
        s.strip()
        for s in _split_marked_sentence_boundaries(text, pattern)
        if s.strip()
    ]
    if extend_split_with_comma_semicolon:
        new_sentences: List[str] = []
        for sentence in sentences:
            new_sentences.extend(
                _split_on_comma_semicolon_preserving_delimiters(sentence)
            )
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
            _append_refined_segment(segments, before)
        bracket_text = match.group().strip()
        if bracket_text:
            _append_refined_segment(segments, bracket_text)
        pos = match.end()
    remainder = sentence[pos:].strip()
    if remainder:
        _append_refined_segment(segments, remainder)
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
                _append_refined_segment(parts, before)
            quote_text = match.group(0).strip()
            if quote_text:
                if parts and not _TERMINAL_SENTENCE_RE.search(parts[-1]):
                    parts[-1] = f"{parts[-1]} {quote_text}"
                else:
                    _append_refined_segment(parts, quote_text)
            pos = match.end()
        remainder = seg[pos:].strip()
        if remainder:
            if (
                parts
                and parts[-1].lstrip().startswith(('"', "“", "‘"))
                and not _TERMINAL_SENTENCE_RE.search(parts[-1])
            ):
                parts[-1] = f"{parts[-1]} {remainder}"
            else:
                _append_refined_segment(parts, remainder)
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
            extended.extend(_split_on_comma_semicolon_preserving_delimiters(seg))
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
        stripped = sentence.strip()
        if len(stripped) == 1:
            separator = "" if _TRAILING_PUNCTUATION_RE.fullmatch(stripped) else " "
            merged[-1] = merged[-1] + separator + stripped
        else:
            merged.append(sentence)
    return merged


def _split_text_into_sentences_regex(
    text: str,
    *,
    max_words: int = DEFAULT_MAX_WORDS,
    extend_split_with_comma_semicolon: bool = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
) -> List[str]:
    """Split text into refined sentences using the existing regex strategy."""

    text = re.sub(r"\s+", " ", text).strip()
    text = _mark_sentence_boundaries(text)
    pattern = re.compile(
        r"(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!Jr\.)(?<!Sr\.)"
        r"(?<!Prof\.)(?<!St\.)(?<!e\.g\.)(?<!i\.e\.)(?<!vs\.)(?<!etc\.)"
        r"(?<!\b[A-Za-z]\.)"
        r"(?:(?<=[?!])\s+(?=[A-Za-z\"“‘])|(?<!\.\.\.)(?<=[.])\s+(?=[A-Za-z\"“‘]))"
    )
    raw_segments = _split_marked_sentence_boundaries(text, pattern)
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


def _normalized_splitter_text(text: str) -> str:
    return " ".join(text.split())


def _split_text_into_sentences_modern(
    text: str,
    *,
    max_words: int,
    extend_split_with_comma_semicolon: bool,
) -> List[str] | None:
    """Split with syntok when available, falling back to regex on any doubt."""

    try:
        from syntok import segmenter  # type: ignore
    except Exception:
        return None

    normalized_text = re.sub(r"\s+", " ", text).strip()
    if not normalized_text:
        return []

    raw_sentences: List[str] = []
    try:
        for paragraph in segmenter.process(normalized_text):
            for sentence in paragraph:
                pieces: List[str] = []
                for token in sentence:
                    spacing = getattr(token, "spacing", " ") or " "
                    value = getattr(token, "value", str(token))
                    if pieces:
                        pieces.append(str(spacing))
                    pieces.append(str(value))
                raw = "".join(pieces).strip()
                if raw:
                    raw_sentences.append(raw)
    except Exception:
        return None

    if not raw_sentences:
        return None

    refined: List[str] = []
    for sentence in raw_sentences:
        refined.extend(
            _refine_and_split_sentence(
                sentence,
                max_words=max_words,
                extend_split_with_comma_semicolon=extend_split_with_comma_semicolon,
            )
        )
    refined = _merge_single_char_sentences(refined)

    if _normalized_splitter_text(" ".join(refined)) != _normalized_splitter_text(normalized_text):
        return None
    return refined


def split_text_into_sentences(
    text: str,
    *,
    max_words: int = DEFAULT_MAX_WORDS,
    extend_split_with_comma_semicolon: bool = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    splitter_mode: str | None = DEFAULT_SENTENCE_SPLITTER_MODE,
) -> List[str]:
    """Split text into refined sentences respecting punctuation and word limits."""

    mode = normalize_sentence_splitter_mode(splitter_mode)
    if mode == "modern":
        modern = _split_text_into_sentences_modern(
            text,
            max_words=max_words,
            extend_split_with_comma_semicolon=extend_split_with_comma_semicolon,
        )
        if modern is not None:
            return modern
    return _split_text_into_sentences_regex(
        text,
        max_words=max_words,
        extend_split_with_comma_semicolon=extend_split_with_comma_semicolon,
    )


def _splitter_stats(sentences: List[str], source_text: str) -> dict[str, object]:
    word_counts = [len(sentence.split()) for sentence in sentences]
    tiny_count = sum(1 for count in word_counts if 0 < count <= 2)
    return {
        "sentence_count": len(sentences),
        "normalized_text_preserved": _normalized_splitter_text(" ".join(sentences))
        == _normalized_splitter_text(source_text),
        "tiny_fragment_count": tiny_count,
        "tiny_fragment_rate": (tiny_count / len(sentences)) if sentences else 0.0,
        "max_words_per_segment": max(word_counts, default=0),
    }


def compare_sentence_splitter_modes(
    text: str,
    *,
    max_words: int = DEFAULT_MAX_WORDS,
    extend_split_with_comma_semicolon: bool = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
) -> dict[str, object]:
    """Return dry-run quality metrics for regex vs opt-in modern splitting."""

    regex_sentences = _split_text_into_sentences_regex(
        text,
        max_words=max_words,
        extend_split_with_comma_semicolon=extend_split_with_comma_semicolon,
    )
    modern_direct = _split_text_into_sentences_modern(
        text,
        max_words=max_words,
        extend_split_with_comma_semicolon=extend_split_with_comma_semicolon,
    )
    modern_fell_back = modern_direct is None
    modern_sentences = modern_direct if modern_direct is not None else list(regex_sentences)
    regex_stats = _splitter_stats(regex_sentences, text)
    modern_stats = _splitter_stats(modern_sentences, text)
    return {
        "max_words": max_words,
        "split_on_comma_semicolon": extend_split_with_comma_semicolon,
        "regex": regex_stats,
        "modern": {
            **modern_stats,
            "fallback_to_regex": modern_fell_back,
        },
        "sentence_count_delta": int(modern_stats["sentence_count"])
        - int(regex_stats["sentence_count"]),
        "normalized_text_coverage": {
            "regex": bool(regex_stats["normalized_text_preserved"]),
            "modern": bool(modern_stats["normalized_text_preserved"]),
        },
    }


__all__ = [
    "DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON",
    "DEFAULT_MAX_WORDS",
    "DEFAULT_SENTENCE_SPLITTER_MODE",
    "MODERN_SENTENCE_SPLITTER_VERSION",
    "SENTENCE_SPLITTER_VERSION",
    "compare_sentence_splitter_modes",
    "extract_sections_from_epub",
    "extract_text_from_epub",
    "normalize_sentence_splitter_mode",
    "remove_quotes",
    "sentence_splitter_version_for_mode",
    "split_text_into_sentences",
    "split_text_into_sentences_no_refine",
]
