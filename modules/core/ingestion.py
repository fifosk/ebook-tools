from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, Sequence, Tuple

from ..config_manager import resolve_file_path
from ..epub_parser import extract_text_from_epub, split_text_into_sentences
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

    text = extract_text_from_epub(input_file)
    refined = split_text_into_sentences(
        text,
        max_words=pipeline_config.max_words,
        extend_split_with_comma_semicolon=pipeline_config.split_on_comma_semicolon,
    )
    save_refined_list(refined, input_file, pipeline_config, metadata=metadata)
    return refined, True
