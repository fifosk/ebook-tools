"""Automatic metadata extraction and enrichment for EPUB files."""

from __future__ import annotations

import json
import re
import shutil
import textwrap
import urllib.parse
from pathlib import Path
from typing import Dict, Iterable, Optional

import requests
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
from ebooklib import epub
from datetime import datetime

from . import config_manager as cfg
from . import logging_manager as log_mgr
from . import llm_client

logger = log_mgr.get_logger()

_METADATA_CACHE: Dict[str, Dict[str, Optional[str]]] = {}
_DEFAULT_PLACEHOLDERS = {
    "book_title": {"", None, "Unknown", "Unknown Title"},
    "book_author": {"", None, "Unknown", "Unknown Author"},
    "book_year": {"", None, "Unknown", "Unknown Year"},
    "book_summary": {"", None, "No summary provided.", "Summary unavailable."},
    "book_cover_file": {"", None},
}


def _is_placeholder(key: str, value: Optional[str]) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in _DEFAULT_PLACEHOLDERS.get(key, set())
    return False


def _needs_metadata(metadata: Dict[str, Optional[str]]) -> bool:
    return any(_is_placeholder(key, metadata.get(key)) for key in _DEFAULT_PLACEHOLDERS)


def _parse_filename_metadata(epub_path: Path) -> Dict[str, Optional[str]]:
    base = epub_path.stem
    base = base.replace("_", " ").replace(".", " ")
    base = re.sub(r"\s+", " ", base).strip()
    result: Dict[str, Optional[str]] = {}

    year_match = re.search(r"(19|20|21)\d{2}", base)
    if year_match:
        result["book_year"] = year_match.group(0)
        base = base.replace(year_match.group(0), " ")

    patterns = [" - ", " by ", " : "]
    for delimiter in patterns:
        if delimiter in base:
            parts = [part.strip() for part in base.split(delimiter, 1)]
            if len(parts) == 2:
                result.setdefault("book_title", parts[0] if len(parts[0]) > 2 else None)
                result.setdefault("book_author", parts[1] if len(parts[1]) > 2 else None)
                break

    if "book_title" not in result:
        cleaned = base.strip()
        if cleaned:
            result["book_title"] = cleaned

    return result


def _first_metadata_value(entries: Iterable) -> Optional[str]:
    for entry in entries:
        if isinstance(entry, tuple) and entry:
            value = entry[0]
        else:
            value = entry
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _extract_epub_metadata(epub_path: Path) -> Dict[str, Optional[str]]:
    metadata: Dict[str, Optional[str]] = {}
    try:
        book = epub.read_epub(str(epub_path))
    except Exception as exc:  # pragma: no cover - delegate to heuristics
        logger.debug("Unable to load EPUB metadata from %s: %s", epub_path, exc)
        return metadata

    title = _first_metadata_value(book.get_metadata("DC", "title"))
    author = _first_metadata_value(book.get_metadata("DC", "creator"))
    date = _first_metadata_value(book.get_metadata("DC", "date"))
    description = _first_metadata_value(book.get_metadata("DC", "description"))

    if title:
        metadata["book_title"] = title
    if author:
        metadata["book_author"] = author
    if date:
        year_match = re.search(r"(19|20|21)\d{2}", date)
        if year_match:
            metadata["book_year"] = year_match.group(0)
    if description:
        metadata["book_summary"] = description

    text_fragments = []
    accumulated = 0
    max_chars = 6000
    for item in book.get_items():
        if not isinstance(item, epub.EpubHtml):
            continue
        try:
            soup = BeautifulSoup(item.get_content(), "html.parser")
        except Exception:
            continue
        text = soup.get_text(separator=" ", strip=True)
        if not text:
            continue
        text_fragments.append(text)
        accumulated += len(text)
        if accumulated >= max_chars:
            break
    if text_fragments:
        metadata["_preview_text"] = "\n\n".join(text_fragments)[:max_chars]

    return metadata


def _invoke_llm_enrichment(
    filename: str,
    preview: str,
    base_metadata: Dict[str, Optional[str]],
    *,
    summary_hint: Optional[str] = None,
    missing_fields: Iterable[str] = (),
    timeout: int = 90,
) -> Dict[str, Optional[str]]:
    if not preview or not llm_client.get_model():
        return {}

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", preview) if part.strip()]
    first_block = paragraphs[0] if paragraphs else preview[:600]
    first_sentences = re.split(r"(?<=[.!?])\s+", first_block)
    leading_excerpt = " ".join(first_sentences[:4]).strip() or first_block[:600]

    prompt_context = {
        "filename": filename,
        "known_metadata": {k: v for k, v in base_metadata.items() if v},
        "preview_excerpt": preview[:4000],
        "first_block_excerpt": leading_excerpt,
        "summary_hint": summary_hint,
        "requested_fields": list(missing_fields),
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert bibliographic researcher. "
                "Infer the true published title, author, original publication year, and a 2-3 sentence summary for an EPUB. "
                "Prioritize evidence from the supplied summary and opening paragraphs. "
                "Return valid JSON with keys book_title, book_author, book_year, book_summary. "
                "Use historically plausible four-digit years; never invent future years. "
                "Avoid generic placeholders such as 'Book' or 'Unknown'."
            ),
        },
        {
            "role": "user",
            "content": "```json\n" + json.dumps(prompt_context, ensure_ascii=False, indent=2) + "\n```",
        },
    ]

    try:
        response = llm_client.send_chat_request(
            {"messages": messages, "stream": False},
            max_attempts=1,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - network issues
        logger.debug("LLM request failed: %s", exc)
        return {}

    if response.error or not response.text:
        if response.error:
            logger.debug("LLM enrichment error: %s", response.error)
        return {}

    text = response.text.strip()
    json_candidate = text
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_candidate = match.group(0)
    try:
        parsed = json.loads(json_candidate)
    except json.JSONDecodeError:
        logger.debug("LLM response was not valid JSON: %s", text[:200])
        return {}

    enriched: Dict[str, Optional[str]] = {}
    current_year = datetime.utcnow().year
    for key in ["book_title", "book_author", "book_year", "book_summary"]:
        value = parsed.get(key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        if key == "book_title" and cleaned.lower() in {"book", "unknown", "novel", "story"}:
            logger.debug("Discarding non-specific LLM title suggestion: %s", cleaned)
            continue
        if key == "book_year":
            match = re.search(r"(\d{4})", cleaned)
            if not match:
                logger.debug("Ignoring LLM year without four digits: %s", cleaned)
                continue
            year_int = int(match.group(1))
            if year_int > current_year:
                logger.debug("Ignoring implausible future year suggested by LLM: %s", cleaned)
                continue
            cleaned = match.group(1)
        enriched[key] = cleaned
    return enriched


def _download_cover_image(title: str, author: str, destination: Path) -> bool:
    query = " ".join(part for part in [title, author] if part)
    if not query.strip():
        return False
    encoded = urllib.parse.quote(query.strip())
    search_url = f"https://openlibrary.org/search.json?title={encoded}"
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code != 200:
            return False
        data = response.json()
    except Exception as exc:  # pragma: no cover - network/JSON errors
        logger.debug("Failed to query OpenLibrary for cover: %s", exc)
        return False

    docs = data.get("docs", []) if isinstance(data, dict) else []
    for doc in docs:
        cover_id = doc.get("cover_i")
        if not cover_id:
            continue
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        try:
            cover_resp = requests.get(cover_url, timeout=10)
            if cover_resp.status_code != 200:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, "wb") as handle:
                handle.write(cover_resp.content)
            return True
        except Exception as exc:  # pragma: no cover
            logger.debug("Failed to download cover image %s: %s", cover_url, exc)
            continue
    return False


def _create_placeholder_cover(title: str, destination: Path) -> bool:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        width, height = 600, 900
        image = Image.new("RGB", (width, height), color=(35, 47, 62))
        draw = ImageDraw.Draw(image)
        text = title or "Unknown Title"
        wrapped = textwrap.wrap(text, width=18)[:5]
        if not wrapped:
            wrapped = ["Unknown Title"]
        font = ImageFont.load_default()
        line_heights = []
        line_widths = []
        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])
        total_text_height = sum(line_heights) + (len(wrapped) - 1) * 10
        current_y = (height - total_text_height) // 2
        for idx, line in enumerate(wrapped):
            text_height = line_heights[idx]
            text_width = line_widths[idx]
            draw.text(((width - text_width) / 2, current_y), line, font=font, fill=(240, 240, 240))
            current_y += text_height + 10
        image.save(destination, format="JPEG")
        return True
    except Exception as exc:  # pragma: no cover - PIL errors
        logger.debug("Failed to create placeholder cover: %s", exc)
        return False


def _get_runtime_output_dir() -> Path:
    base_candidate = cfg.WORKING_DIR or cfg.DEFAULT_WORKING_RELATIVE
    base_path = cfg.resolve_directory(base_candidate, cfg.DEFAULT_WORKING_RELATIVE)
    runtime_dir = Path(base_path) / cfg.DERIVED_RUNTIME_DIRNAME
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def _runtime_cover_destination(epub_path: Path) -> Path:
    runtime_dir = _get_runtime_output_dir()
    safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", epub_path.stem) or "book"
    return runtime_dir / f"{safe_base}_cover.jpg"


def _resolve_cover_path(candidate: Optional[str]) -> Optional[Path]:
    if not candidate:
        return None
    path = Path(candidate)
    if path.is_absolute():
        return path if path.exists() else None
    resolved = cfg.resolve_file_path(candidate, cfg.BOOKS_DIR)
    if resolved and resolved.exists():
        return resolved
    return None


def _ensure_cover_image(metadata: Dict[str, Optional[str]], epub_path: Path) -> Optional[str]:
    title = metadata.get("book_title") or "Unknown Title"
    author = metadata.get("book_author") or ""
    destination = _runtime_cover_destination(epub_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    current_path = _resolve_cover_path(metadata.get("book_cover_file"))
    if current_path and current_path.exists():
        if current_path.resolve() != destination.resolve():
            try:
                shutil.copy(current_path, destination)
            except Exception as exc:  # pragma: no cover - filesystem errors
                logger.debug("Unable to mirror existing cover to runtime directory: %s", exc)
            else:
                return str(destination)
        else:
            return str(destination)

    if destination.exists():
        return str(destination)

    logger.info("Attempting to retrieve a cover image for '%s' by %s", title, author or "Unknown Author")
    if _download_cover_image(title, author, destination):
        logger.info("Downloaded cover image to %s", destination)
        return str(destination)

    if _create_placeholder_cover(title, destination):
        logger.info("Generated placeholder cover image at %s", destination)
        return str(destination)

    return None


def infer_metadata(
    input_file: str,
    *,
    existing_metadata: Optional[Dict[str, Optional[str]]] = None,
) -> Dict[str, Optional[str]]:
    epub_path = cfg.resolve_file_path(input_file, cfg.BOOKS_DIR)
    if not epub_path:
        logger.debug("Cannot infer metadata: input file %s could not be resolved", input_file)
        return existing_metadata or {}

    cache_key = str(epub_path)
    if cache_key in _METADATA_CACHE:
        cached = _METADATA_CACHE[cache_key].copy()
        merged = dict(existing_metadata or {})
        merged.update({k: v for k, v in cached.items() if v})
        return merged

    logger.info("Inferring metadata for %s", epub_path.name)
    metadata: Dict[str, Optional[str]] = dict(existing_metadata or {})

    filename_guesses = _parse_filename_metadata(epub_path)
    for key, value in filename_guesses.items():
        if value and _is_placeholder(key, metadata.get(key)):
            metadata[key] = value
            logger.debug("Filename heuristic provided %s: %s", key, value)

    epub_metadata = _extract_epub_metadata(epub_path)
    preview_text = epub_metadata.pop("_preview_text", None)
    for key, value in epub_metadata.items():
        if value and _is_placeholder(key, metadata.get(key)):
            metadata[key] = value
            logger.debug("EPUB embedded metadata provided %s: %s", key, value)

    summary_hint = metadata.get("book_summary")
    if _is_placeholder("book_summary", summary_hint):
        summary_hint = None

    if preview_text and not summary_hint:
        logger.debug("Using preview text fallback to craft summary")
        sentences = re.split(r"(?<=[.!?])\s+", preview_text.strip())
        summary = " ".join(sentences[:3]).strip()
        if summary:
            metadata["book_summary"] = summary
            summary_hint = summary

    missing_fields = [
        key
        for key in ["book_title", "book_author", "book_year", "book_summary"]
        if _is_placeholder(key, metadata.get(key))
    ]

    if preview_text and missing_fields:
        enriched = _invoke_llm_enrichment(
            epub_path.name,
            preview_text,
            metadata,
            summary_hint=summary_hint,
            missing_fields=missing_fields,
        )
        for key, value in enriched.items():
            if value and _is_placeholder(key, metadata.get(key)):
                metadata[key] = value
                logger.info("LLM enriched %s", key)
            elif key == "book_summary" and value:
                metadata[key] = value

    cover_path = _ensure_cover_image(metadata, epub_path)
    if cover_path:
        metadata["book_cover_file"] = cover_path

    _METADATA_CACHE[cache_key] = metadata.copy()
    return metadata


def populate_config_metadata(
    config: Dict[str, Optional[str]],
    input_file: str,
    *,
    force: bool = False,
) -> Dict[str, Optional[str]]:
    existing = {
        "book_title": config.get("book_title"),
        "book_author": config.get("book_author"),
        "book_year": config.get("book_year"),
        "book_summary": config.get("book_summary"),
        "book_cover_file": config.get("book_cover_file"),
    }

    if not force and not _needs_metadata(existing):
        return config

    inferred = infer_metadata(input_file, existing_metadata=existing)

    for key, value in inferred.items():
        if key not in existing:
            continue
        if value and (force or _is_placeholder(key, existing.get(key)) or existing.get(key) != value):
            config[key] = value
            logger.info("Updated %s via automatic metadata manager", key)

    return config


__all__ = ["infer_metadata", "populate_config_metadata"]
