"""Automatic metadata extraction and enrichment for EPUB files."""

from __future__ import annotations

import copy
import json
import re
import shutil
import textwrap
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
from ebooklib import epub

from . import config_manager as cfg
from . import logging_manager as log_mgr
from .llm_client import LLMClient, create_client

logger = log_mgr.get_logger()

_METADATA_CACHE: Dict[str, Dict[str, Optional[str]]] = {}
_DEFAULT_PLACEHOLDERS = {
    "book_title": {"", None, "Unknown", "Unknown Title", "Book"},
    "book_author": {"", None, "Unknown", "Unknown Author"},
    "book_year": {"", None, "Unknown", "Unknown Year"},
    "book_summary": {"", None, "No summary provided.", "Summary unavailable."},
    "book_cover_file": {"", None},
}

_PLACEHOLDER_LOOKUP = {
    key: {
        value.strip().casefold()
        for value in values
        if isinstance(value, str) and value.strip()
    }
    for key, values in _DEFAULT_PLACEHOLDERS.items()
}

_SENTENCE_LIMIT = 10
_SUMMARY_MAX_SENTENCES = 4
_SUMMARY_MAX_CHARACTERS = 600
_OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
_OPENLIBRARY_COVER_TEMPLATE = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


def _normalize_isbn(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = re.sub(r"[^0-9Xx]", "", value)
    if len(cleaned) in {10, 13}:
        return cleaned.upper()
    return None


def _is_placeholder(key: str, value: Optional[str]) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return True
        return cleaned.casefold() in _PLACEHOLDER_LOOKUP.get(key, set())
    return False


def _needs_metadata(metadata: Dict[str, Optional[str]]) -> bool:
    return any(_is_placeholder(key, metadata.get(key)) for key in _DEFAULT_PLACEHOLDERS)


def _apply_metadata(
    metadata: Dict[str, Optional[str]],
    key: str,
    value: Optional[str],
    *,
    force: bool = False,
) -> None:
    if value is None:
        return
    if force:
        metadata[key] = value
        return
    current = metadata.get(key)
    if _is_placeholder(key, current):
        metadata[key] = value
        return
    if not _is_placeholder(key, value) and current != value:
        metadata[key] = value


def _parse_filename_metadata(epub_path: Path) -> Dict[str, Optional[str]]:
    base = epub_path.stem
    base = base.replace("_", " ").replace(".", " ")
    base = re.sub(r"\s+", " ", base).strip()
    result: Dict[str, Optional[str]] = {}

    year_match = re.search(r"(18|19|20|21)\d{2}", base)
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


def _split_sentences(text: str) -> List[str]:
    if not text:
        return []
    segments = re.split(r"(?<=[.!?])\s+", text)
    sentences: List[str] = []
    for segment in segments:
        cleaned = segment.strip()
        if cleaned:
            sentences.append(cleaned)
        if len(sentences) >= _SENTENCE_LIMIT:
            break
    return sentences


def _extract_epub_context(epub_path: Path) -> Tuple[Dict[str, Optional[str]], List[str]]:
    metadata: Dict[str, Optional[str]] = {}
    sentences: List[str] = []
    try:
        book = epub.read_epub(str(epub_path))
    except Exception as exc:  # pragma: no cover - delegate to heuristics
        logger.debug("Unable to load EPUB metadata from %s: %s", epub_path, exc)
        return metadata, sentences

    def _first_value(entries: Iterable) -> Optional[str]:
        for entry in entries:
            value = entry[0] if isinstance(entry, tuple) and entry else entry
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
        return None

    title = _first_value(book.get_metadata("DC", "title"))
    author = _first_value(book.get_metadata("DC", "creator"))
    date = _first_value(book.get_metadata("DC", "date"))

    if title:
        metadata["book_title"] = title
    if author:
        metadata["book_author"] = author
    if date:
        year_match = re.search(r"(18|19|20|21)\d{2}", date)
        if year_match:
            metadata["book_year"] = year_match.group(0)

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
        new_sentences = _split_sentences(text)
        for sentence in new_sentences:
            sentences.append(sentence)
            if len(sentences) >= _SENTENCE_LIMIT:
                return metadata, sentences
    return metadata, sentences


def _build_llm_messages(
    filename: str,
    sentences: List[str],
    seed_metadata: Dict[str, Optional[str]],
) -> List[Dict[str, str]]:
    system_message = {
        "role": "system",
        "content": (
            "You are an expert bibliographic researcher. "
            "Using the provided EPUB filename context and the opening sentences from the book, "
            "determine the published book title, the main author, and the original publication year. "
            "Prefer evidence that appears directly in the supplied sentences, such as title pages or forewords. "
            "Respond with a single JSON object that contains exactly the keys book_title, book_author, and book_year. "
            "If uncertain, provide your best historically plausible estimate. "
            "Always return four-digit years and avoid additional commentary."
        ),
    }
    user_payload = {
        "filename": filename,
        "first_sentences": sentences,
        "embedded_metadata": {k: v for k, v in seed_metadata.items() if v},
    }
    user_message = {
        "role": "user",
        "content": "```json\n" + json.dumps(user_payload, ensure_ascii=False, indent=2) + "\n```",
    }
    return [system_message, user_message]


def _invoke_llm_metadata(
    filename: str,
    sentences: List[str],
    seed_metadata: Dict[str, Optional[str]],
    timeout: int = 90,
    *,
    client: Optional[LLMClient] = None,
) -> Dict[str, Optional[str]]:
    if not sentences:
        return {}

    if client is not None:
        managed_client = client
    else:
        settings = cfg.get_settings()
        secret = settings.ollama_api_key
        api_key = secret.get_secret_value() if secret is not None else None
        managed_client = create_client(
            model=settings.ollama_model,
            api_url=cfg.get_ollama_url(),
            api_key=api_key,
            llm_source=cfg.get_llm_source(),
            local_api_url=cfg.get_local_ollama_url(),
            cloud_api_url=cfg.get_cloud_ollama_url(),
            cloud_api_key=api_key,
        )
    try:
        if not managed_client.model:
            return {}

        messages = _build_llm_messages(filename, sentences, seed_metadata)
        try:
            response = managed_client.send_chat_request(
                {"messages": messages, "stream": False},
                max_attempts=1,
                timeout=timeout,
            )
        except Exception as exc:  # pragma: no cover - network issues
            logger.debug("LLM request failed: %s", exc)
            return {}
    finally:
        if client is None:
            managed_client.close()

    if response.error or not response.text:
        if response.error:
            logger.debug("LLM enrichment error: %s", response.error)
        return {}

    candidate = response.text.strip()
    if not candidate.startswith("{"):
        match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if match:
            candidate = match.group(0)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        logger.debug("LLM response was not valid JSON: %s", candidate[:200])
        return {}

    results: Dict[str, Optional[str]] = {}
    current_year = datetime.utcnow().year
    for key in ("book_title", "book_author", "book_year"):
        value = parsed.get(key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        if key == "book_year":
            match = re.search(r"(\d{4})", cleaned)
            if not match:
                continue
            year_int = int(match.group(1))
            if year_int > current_year:
                continue
            cleaned = match.group(1)
        results[key] = cleaned
    return results


def _normalize(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip().lower()


def _select_openlibrary_doc(
    docs: List[Dict[str, Any]],
    title: str,
    author: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not docs:
        return None
    normalized_title = _normalize(title)
    normalized_author = _normalize(author)

    best_doc = None
    best_score = -1
    for doc in docs:
        doc_title = _normalize(doc.get("title"))
        if not doc_title:
            continue
        score = 0
        if doc_title == normalized_title:
            score += 3
        elif normalized_title and normalized_title in doc_title:
            score += 1

        author_names = [_normalize(name) for name in doc.get("author_name", []) if name]
        if normalized_author and author_names:
            if normalized_author in author_names:
                score += 3
            else:
                for candidate in author_names:
                    if normalized_author.split()[0] in candidate:
                        score += 1
                        break

        if not best_doc or score > best_score:
            best_doc = doc
            best_score = score
    return best_doc


def _fetch_openlibrary_details(title: str, author: Optional[str]) -> Dict[str, Optional[str]]:
    if not title:
        return {}

    params = {"title": title}
    if author:
        params["author"] = author

    try:
        response = requests.get(_OPENLIBRARY_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network issues
        logger.debug("OpenLibrary search failed: %s", exc)
        return {}

    docs = payload.get("docs", []) if isinstance(payload, dict) else []
    best_doc = _select_openlibrary_doc(docs, title, author)
    if not best_doc:
        return {}

    enrichment: Dict[str, Optional[str]] = {}

    first_publish_year = best_doc.get("first_publish_year") or best_doc.get("publish_year", [None])[0]
    if first_publish_year:
        enrichment["book_year"] = str(first_publish_year)

    cover_id = best_doc.get("cover_i")
    if cover_id:
        enrichment["cover_url"] = _OPENLIBRARY_COVER_TEMPLATE.format(cover_id=cover_id)

    summary = None
    if isinstance(best_doc.get("first_sentence"), dict):
        summary = best_doc["first_sentence"].get("value")
    elif isinstance(best_doc.get("first_sentence"), str):
        summary = best_doc.get("first_sentence")

    work_key = best_doc.get("key")
    if work_key:
        try:
            work_resp = requests.get(f"https://openlibrary.org{work_key}.json", timeout=10)
            if work_resp.status_code == 200:
                work_data = work_resp.json()
                description = work_data.get("description")
                if isinstance(description, dict):
                    description = description.get("value")
                if isinstance(description, str):
                    summary = description.strip() or summary
        except Exception as exc:  # pragma: no cover
            logger.debug("Failed to fetch OpenLibrary work details for %s: %s", work_key, exc)

    if summary:
        enrichment["book_summary"] = _limit_summary_length(summary)

    return enrichment


def fetch_metadata_from_isbn(isbn: str) -> Dict[str, Optional[str]]:
    """Return metadata for ``isbn`` sourced from public APIs."""

    normalized = _normalize_isbn(isbn)
    if not normalized:
        raise ValueError("ISBN must contain 10 or 13 digits (optionally including X)")

    metadata: Dict[str, Optional[str]] = {"isbn": normalized}

    params = {
        "bibkeys": f"ISBN:{normalized}",
        "format": "json",
        "jscmd": "data",
    }

    try:
        response = requests.get("https://openlibrary.org/api/books", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network issues
        logger.debug("OpenLibrary ISBN lookup failed: %s", exc)
        return metadata

    key = f"ISBN:{normalized}"
    book_data = payload.get(key)
    if not isinstance(book_data, dict):
        return metadata

    title = book_data.get("title")
    if isinstance(title, str) and title.strip():
        metadata["book_title"] = title.strip()

    authors = book_data.get("authors")
    if isinstance(authors, list):
        names = []
        for entry in authors:
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
        if names:
            metadata["book_author"] = ", ".join(names)

    publish_date = book_data.get("publish_date")
    if isinstance(publish_date, str):
        year_match = re.search(r"(18|19|20|21)\d{2}", publish_date)
        if year_match:
            metadata["book_year"] = year_match.group(0)

    description = book_data.get("description")
    if isinstance(description, dict):
        description = description.get("value")
    if isinstance(description, str):
        metadata["book_summary"] = _limit_summary_length(description)

    subjects = book_data.get("subjects")
    if isinstance(subjects, list):
        for candidate in subjects:
            if isinstance(candidate, dict):
                name = candidate.get("name")
                if isinstance(name, str) and name.strip():
                    metadata["book_genre"] = name.strip()
                    break
            elif isinstance(candidate, str) and candidate.strip():
                metadata["book_genre"] = candidate.strip()
                break

    languages = book_data.get("languages")
    if isinstance(languages, list):
        for entry in languages:
            if isinstance(entry, dict):
                key_value = entry.get("key")
                if isinstance(key_value, str) and key_value.strip():
                    code = key_value.strip().split("/")[-1]
                    if code:
                        metadata["book_language"] = code
                        break

    cover_info = book_data.get("cover")
    cover_url: Optional[str] = None
    if isinstance(cover_info, dict):
        cover_url = cover_info.get("large") or cover_info.get("medium") or cover_info.get("small")
    elif isinstance(cover_info, str):
        cover_url = cover_info

    if cover_url:
        destination = _cover_destination_for_isbn(normalized)
        if _download_cover_from_url(cover_url, destination):
            metadata["book_cover_file"] = str(destination)
        metadata["cover_url"] = cover_url

    return metadata


def _limit_summary_length(summary: str) -> str:
    cleaned = summary.strip()
    if not cleaned:
        return cleaned

    primary_paragraph = cleaned.split("\n\n", 1)[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+", primary_paragraph)

    limited_sentences: List[str] = []
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        limited_sentences.append(stripped)
        if len(limited_sentences) >= _SUMMARY_MAX_SENTENCES:
            break

    short_summary = " ".join(limited_sentences) if limited_sentences else primary_paragraph
    if len(short_summary) <= _SUMMARY_MAX_CHARACTERS:
        return short_summary

    truncated = short_summary[: _SUMMARY_MAX_CHARACTERS - 1].rsplit(" ", 1)[0]
    return truncated + "…"


def _download_cover_from_url(url: str, destination: Path) -> bool:
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "wb") as handle:
            handle.write(response.content)
        return True
    except Exception as exc:  # pragma: no cover - network errors
        logger.debug("Failed to download cover image from %s: %s", url, exc)
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


def _get_cover_storage_root() -> Path:
    return cfg.resolve_directory(None, cfg.DEFAULT_COVERS_RELATIVE)


def _cover_destination(epub_path: Path) -> Path:
    root = _get_cover_storage_root()
    safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", epub_path.stem) or "book"
    digest = hashlib.sha1(epub_path.as_posix().encode("utf-8")).hexdigest()[:8]
    return root / f"{safe_base}_{digest}.jpg"


def _cover_destination_for_isbn(isbn: str) -> Path:
    root = _get_cover_storage_root()
    safe_isbn = re.sub(r"[^0-9Xx]", "", isbn) or "isbn"
    return root / f"isbn_{safe_isbn}.jpg"


def _resolve_cover_path(candidate: Optional[str]) -> Optional[Path]:
    if not candidate:
        return None
    path = Path(candidate)
    if path.is_absolute():
        return path if path.exists() else None
    context = cfg.get_runtime_context(None)
    base_dir = context.books_dir if context is not None else None
    resolved = cfg.resolve_file_path(candidate, base_dir)
    if resolved and resolved.exists():
        return resolved
    return None


def _ensure_cover_image(
    metadata: Dict[str, Optional[str]],
    epub_path: Path,
    *,
    preferred_url: Optional[str] = None,
) -> Optional[str]:
    title = metadata.get("book_title") or "Unknown Title"
    destination = _cover_destination(epub_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    current_path = _resolve_cover_path(metadata.get("book_cover_file"))
    if current_path and current_path.exists():
        if current_path.resolve() != destination.resolve():
            try:
                shutil.copy(current_path, destination)
            except Exception as exc:  # pragma: no cover - filesystem errors
                logger.debug("Unable to mirror existing cover to cover storage directory: %s", exc)
            else:
                return str(destination)
        else:
            return str(destination)

    if destination.exists():
        return str(destination)

    if preferred_url and _download_cover_from_url(preferred_url, destination):
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
    force_refresh: bool = False,
) -> Dict[str, Optional[str]]:
    context = cfg.get_runtime_context(None)
    base_dir = context.books_dir if context is not None else None
    epub_path = cfg.resolve_file_path(input_file, base_dir)
    if not epub_path:
        logger.debug("Cannot infer metadata: input file %s could not be resolved", input_file)
        return existing_metadata or {}

    cache_key = str(epub_path)
    metadata: Dict[str, Optional[str]] = {} if force_refresh else dict(existing_metadata or {})

    if cache_key in _METADATA_CACHE:
        cached = _METADATA_CACHE[cache_key].copy()
        if force_refresh:
            logger.debug("Force refreshing metadata for %s", epub_path.name)
            metadata.update({k: v for k, v in cached.items() if v})
        elif _needs_metadata(cached):
            logger.debug("Metadata cache contains placeholders for %s; refreshing", epub_path.name)
        else:
            metadata.update({k: v for k, v in cached.items() if v})
            return metadata

    logger.info("Inferring metadata for %s", epub_path.name)

    filename_guesses = _parse_filename_metadata(epub_path)
    metadata_seed = metadata.copy()
    metadata_seed.update({k: v for k, v in filename_guesses.items() if v})

    embedded_metadata, sentences = _extract_epub_context(epub_path)
    metadata_seed.update({k: v for k, v in embedded_metadata.items() if v})

    for key, value in metadata_seed.items():
        if not value:
            continue
        _apply_metadata(metadata, key, value, force=force_refresh)

    need_llm = any(
        _is_placeholder(field, metadata.get(field)) for field in ("book_title", "book_author", "book_year")
    )

    if need_llm:
        llm_results = _invoke_llm_metadata(epub_path.name, sentences, metadata_seed)
        for key, value in llm_results.items():
            if not value:
                continue
            previous = metadata.get(key)
            _apply_metadata(metadata, key, value, force=force_refresh)
            if metadata.get(key) != previous:
                logger.info("LLM inferred %s: %s", key, value)

    title = metadata.get("book_title")
    author = metadata.get("book_author")
    openlibrary_data = _fetch_openlibrary_details(title or "", author)

    for key in ("book_year", "book_summary"):
        value = openlibrary_data.get(key)
        if value:
            previous = metadata.get(key)
            _apply_metadata(metadata, key, value, force=force_refresh)
            if metadata.get(key) != previous:
                logger.info("OpenLibrary provided %s", key)

    isbn_candidate = metadata.get("isbn") or (existing_metadata or {}).get("isbn")
    normalized_isbn = _normalize_isbn(isbn_candidate)
    if normalized_isbn:
        metadata["isbn"] = normalized_isbn
        try:
            isbn_enrichment = fetch_metadata_from_isbn(normalized_isbn)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Unable to fetch metadata for ISBN %s: %s", normalized_isbn, exc)
        else:
            for key, value in isbn_enrichment.items():
                if key == "isbn":
                    continue
                _apply_metadata(metadata, key, value, force=force_refresh)

    cover_url = metadata.get("cover_url") or openlibrary_data.get("cover_url")
    cover_path = _ensure_cover_image(metadata, epub_path, preferred_url=cover_url)
    if cover_path:
        if force_refresh or metadata.get("book_cover_file") != cover_path:
            metadata["book_cover_file"] = cover_path

    if metadata.get("book_summary"):
        metadata["book_summary"] = _limit_summary_length(metadata["book_summary"] or "")

    _METADATA_CACHE[cache_key] = metadata.copy()

    logger.info(
        "Metadata inference result: title='%(book_title)s', author='%(book_author)s', year='%(book_year)s'",
        metadata,
    )
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

    inferred = infer_metadata(
        input_file,
        existing_metadata=existing,
        force_refresh=force,
    )

    for key, value in inferred.items():
        if key not in existing:
            continue
        if value and (force or _is_placeholder(key, existing.get(key)) or existing.get(key) != value):
            config[key] = value
            logger.info("Updated %s via automatic metadata manager", key)

    return config


class MetadataLoader:
    """Helper class for reading per-chunk pipeline metadata payloads."""

    def __init__(self, job_root: str | Path) -> None:
        self._job_root = Path(job_root)
        self._metadata_root = self._job_root / "metadata"
        self._manifest_cache: Optional[Dict[str, Any]] = None

    def _manifest_path(self) -> Path:
        return self._metadata_root / "job.json"

    def load_manifest(self, *, refresh: bool = False) -> Dict[str, Any]:
        if self._manifest_cache is not None and not refresh:
            return copy.deepcopy(self._manifest_cache)
        manifest_path = self._manifest_path()
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        self._manifest_cache = manifest
        return copy.deepcopy(manifest)

    def get_generated_files(self) -> Mapping[str, Any]:
        manifest = self.load_manifest()
        generated = manifest.get("generated_files")
        if isinstance(generated, Mapping):
            return copy.deepcopy(generated)
        fallback_chunks = manifest.get("chunks")
        if isinstance(fallback_chunks, list):
            return {
                "chunks": [
                    copy.deepcopy(chunk)
                    for chunk in fallback_chunks
                    if isinstance(chunk, Mapping)
                ]
            }
        return {}

    def iter_chunks(self) -> Iterator[Mapping[str, Any]]:
        generated = self.get_generated_files()
        chunks = generated.get("chunks") if isinstance(generated, Mapping) else None
        if not isinstance(chunks, list):
            return iter(())
        return (
            copy.deepcopy(chunk)
            for chunk in chunks
            if isinstance(chunk, Mapping)
        )

    def load_chunks(self, *, include_sentences: bool = True) -> List[Dict[str, Any]]:
        return [
            self._load_chunk_payload(chunk, include_sentences=include_sentences)
            for chunk in self.iter_chunks()
        ]

    def load_chunk(
        self,
        chunk: Mapping[str, Any],
        *,
        include_sentences: bool = True,
    ) -> Dict[str, Any]:
        return self._load_chunk_payload(chunk, include_sentences=include_sentences)

    def load_chunk_sentences(self, chunk: Mapping[str, Any]) -> List[Any]:
        payload = self._load_chunk_payload(chunk, include_sentences=True)
        sentences = payload.get("sentences")
        return list(sentences) if isinstance(sentences, list) else []

    def build_chunk_manifest(self) -> Dict[str, Any]:
        manifest = self.load_manifest()
        raw_manifest = manifest.get("chunk_manifest")
        if isinstance(raw_manifest, Mapping):
            normalized = {
                "chunk_count": int(raw_manifest.get("chunk_count", 0))
                if isinstance(raw_manifest.get("chunk_count"), int)
                else len(raw_manifest.get("chunks", []) or []),
                "chunks": [],
            }
            raw_chunks = raw_manifest.get("chunks")
            if isinstance(raw_chunks, list):
                for entry in raw_chunks:
                    if not isinstance(entry, Mapping):
                        continue
                    normalized["chunks"].append(
                        {
                            "index": entry.get("index"),
                            "chunk_id": entry.get("chunk_id"),
                            "path": entry.get("path"),
                            "url": entry.get("url"),
                            "sentence_count": entry.get("sentence_count"),
                        }
                    )
            return normalized

        chunk_entries = []
        for index, chunk in enumerate(self.iter_chunks()):
            summary = self._load_chunk_payload(chunk, include_sentences=False)
            chunk_entries.append(
                {
                    "index": index,
                    "chunk_id": summary.get("chunk_id"),
                    "path": summary.get("metadata_path"),
                    "url": summary.get("metadata_url"),
                    "sentence_count": summary.get("sentence_count"),
                }
            )
        return {"chunk_count": len(chunk_entries), "chunks": chunk_entries}

    def _resolve_chunk_path(self, path_value: str) -> Path:
        normalized = path_value.replace("\\", "/").lstrip("/")
        candidate = Path(normalized)
        if candidate.is_absolute():
            return candidate
        return self._job_root / candidate

    def _load_chunk_payload(
        self,
        chunk: Mapping[str, Any],
        *,
        include_sentences: bool,
    ) -> Dict[str, Any]:
        payload = {
            key: copy.deepcopy(value)
            for key, value in chunk.items()
            if key != "sentences"
        }

        sentence_count = payload.get("sentence_count")
        if not isinstance(sentence_count, int):
            sentence_count = 0

        sentences: List[Any] = []
        if include_sentences:
            sentences = self._load_sentences_from_chunk(chunk)
            if sentences:
                payload["sentences"] = sentences
                sentence_count = len(sentences)
        elif "sentences" in chunk and not payload.get("metadata_path"):
            inline = chunk.get("sentences")
            if isinstance(inline, list) and inline:
                sentence_count = len(inline)

        payload["sentence_count"] = sentence_count
        return payload

    def _load_sentences_from_chunk(self, chunk: Mapping[str, Any]) -> List[Any]:
        metadata_path = chunk.get("metadata_path")
        if isinstance(metadata_path, str) and metadata_path.strip():
            candidate = self._resolve_chunk_path(metadata_path)
            try:
                with candidate.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError):
                data = None
            if isinstance(data, Mapping):
                sentences = data.get("sentences")
                if isinstance(sentences, list):
                    return [copy.deepcopy(entry) for entry in sentences]

        inline = chunk.get("sentences")
        if isinstance(inline, list):
            return [copy.deepcopy(entry) for entry in inline]
        return []


__all__ = [
    "infer_metadata",
    "populate_config_metadata",
    "fetch_metadata_from_isbn",
    "MetadataLoader",
]
