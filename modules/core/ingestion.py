from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence, Tuple

from ..config_manager import resolve_file_path
from ..epub_parser import (
    extract_sections_from_epub,
    extract_text_from_epub,
    split_text_into_sentences,
)
from .config import PipelineConfig


def get_runtime_output_dir(pipeline_config: PipelineConfig) -> Path:
    """Return the directory used for storing derived runtime artifacts."""

    return pipeline_config.ensure_runtime_dir()


def refined_list_output_path(
    input_file: Optional[str], pipeline_config: PipelineConfig
) -> Path:
    """Return the path for storing the refined sentence cache."""

    base_name = Path(input_file).stem if input_file else "refined"
    safe_base = re.sub(r"[^A-Za-z0-9_.-]", "_", base_name)
    runtime_dir = get_runtime_output_dir(pipeline_config)
    return runtime_dir / pipeline_config.derived_refined_filename_template.format(
        base_name=safe_base
    )


def save_refined_list(
    refined_list: Sequence[str],
    input_file: Optional[str],
    pipeline_config: PipelineConfig,
    metadata: Optional[dict] = None,
) -> Path:
    """Persist the refined sentence list to the runtime output directory."""

    output_path = refined_list_output_path(input_file, pipeline_config)
    payload = {
        "generated_at": time.time(),
        "input_file": input_file,
        "max_words": pipeline_config.max_words,
        "split_on_comma_semicolon": pipeline_config.split_on_comma_semicolon,
        "metadata": metadata or {},
        "refined_list": list(refined_list),
    }
    with open(output_path, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2)
    return output_path


def load_refined_list(
    input_file: Optional[str], pipeline_config: PipelineConfig
) -> Optional[dict]:
    """Load a previously generated refined list from the runtime directory."""

    output_path = refined_list_output_path(input_file, pipeline_config)
    if not output_path.exists():
        return None
    try:
        with open(output_path, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except (json.JSONDecodeError, OSError):
        return None


def get_refined_sentences(
    input_file: Optional[str],
    pipeline_config: PipelineConfig,
    *,
    force_refresh: bool = False,
    metadata: Optional[dict] = None,
) -> Tuple[Sequence[str], bool]:
    """Return the refined sentence list and whether it was regenerated."""

    if not input_file:
        return [], False

    resolved_input = resolve_file_path(
        input_file, pipeline_config.resolved_books_dir()
    )
    if not resolved_input:
        return [], False

    if not resolved_input.exists():
        logging.getLogger(__name__).warning(
            "EPUB file '%s' could not be found.", resolved_input
        )
        return [], False

    input_file = str(resolved_input)
    expected_settings = {
        "max_words": pipeline_config.max_words,
        "split_on_comma_semicolon": pipeline_config.split_on_comma_semicolon,
    }

    cached = None if force_refresh else load_refined_list(input_file, pipeline_config)
    if cached and cached.get("refined_list") is not None:
        cached_settings = {
            "max_words": cached.get("max_words"),
            "split_on_comma_semicolon": cached.get("split_on_comma_semicolon"),
        }
        if cached_settings == expected_settings:
            return cached.get("refined_list", []), False

    refined: Sequence[str]
    try:
        sections = extract_sections_from_epub(
            input_file, books_dir=pipeline_config.resolved_books_dir()
        )
    except Exception:
        sections = []
    if sections:
        refined_list: list[str] = []
        for section in sections:
            text = section.get("text") if isinstance(section, dict) else None
            if not isinstance(text, str) or not text.strip():
                continue
            refined_list.extend(
                split_text_into_sentences(
                    text,
                    max_words=pipeline_config.max_words,
                    extend_split_with_comma_semicolon=pipeline_config.split_on_comma_semicolon,
                )
            )
        refined = refined_list
    else:
        text = extract_text_from_epub(input_file)
        refined = split_text_into_sentences(
            text,
            max_words=pipeline_config.max_words,
            extend_split_with_comma_semicolon=pipeline_config.split_on_comma_semicolon,
        )
    save_refined_list(refined, input_file, pipeline_config, metadata=metadata)
    return refined, True


def build_content_index(
    input_file: Optional[str],
    pipeline_config: PipelineConfig,
    refined_sentences: Sequence[str],
) -> Optional[dict]:
    """Return chapter-aware content metadata for ``input_file``."""

    if not input_file:
        return None

    resolved_input = resolve_file_path(
        input_file, pipeline_config.resolved_books_dir()
    )
    if not resolved_input or not resolved_input.exists():
        return None

    try:
        sections = extract_sections_from_epub(
            str(resolved_input), books_dir=pipeline_config.resolved_books_dir()
        )
    except Exception:
        logging.getLogger(__name__).debug(
            "Failed to extract EPUB sections for content index.",
            exc_info=True,
        )
        return None

    if not sections:
        return None

    refined_list = list(refined_sentences or [])
    total_sentences = len(refined_list)
    cursor = 0
    combined: list[str] = []
    alignment_exact = True
    chapters: list[dict[str, object]] = []

    for index, section in enumerate(sections, start=1):
        text = section.get("text") if isinstance(section, dict) else None
        if not isinstance(text, str) or not text.strip():
            continue
        sentences = split_text_into_sentences(
            text,
            max_words=pipeline_config.max_words,
            extend_split_with_comma_semicolon=pipeline_config.split_on_comma_semicolon,
        )
        if not sentences:
            continue

        combined.extend(sentences)
        start_sentence = cursor + 1
        end_sentence = cursor + len(sentences)
        range_truncated = False
        if total_sentences:
            if start_sentence > total_sentences:
                start_sentence = 0
                end_sentence = 0
                range_truncated = True
            else:
                if end_sentence > total_sentences:
                    end_sentence = total_sentences
                    range_truncated = True
                expected = refined_list[cursor : cursor + len(sentences)]
                if expected != sentences:
                    alignment_exact = False

        entry: dict[str, object] = {
            "id": section.get("id") or f"section-{index:04d}",
            "title": section.get("title") or f"Section {index}",
            "start_sentence": start_sentence if start_sentence > 0 else None,
            "end_sentence": end_sentence if end_sentence > 0 else None,
            "sentence_count": len(sentences),
            "range_truncated": range_truncated,
        }
        if isinstance(section.get("href"), str):
            entry["href"] = section.get("href")
        if isinstance(section.get("toc_label"), str):
            entry["toc_label"] = section.get("toc_label")
        if isinstance(section.get("spine_index"), int):
            entry["spine_index"] = section.get("spine_index")
        chapters.append(entry)
        cursor += len(sentences)

    if refined_list and combined != refined_list:
        alignment_exact = False

    alignment_status = "exact" if alignment_exact and cursor == total_sentences else "approximate"
    toc_detected = any("toc_label" in chapter for chapter in chapters)
    spine_detected = any("spine_index" in chapter for chapter in chapters)

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_sentences": total_sentences,
        "chapters": chapters,
        "alignment": {
            "status": alignment_status,
            "section_sentence_total": cursor,
            "sentence_total": total_sentences,
        },
        "sources": {
            "order": "item",
            "toc_detected": toc_detected,
            "spine_detected": spine_detected,
        },
    }


__all__ = [
    "build_content_index",
    "extract_text_from_epub",
    "get_refined_sentences",
    "load_refined_list",
    "refined_list_output_path",
    "save_refined_list",
]
