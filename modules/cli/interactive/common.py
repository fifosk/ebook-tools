"""Shared utilities for the interactive CLI menu."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ...shared import assets
from .. import context

console_info = log_mgr.console_info
console_warning = log_mgr.console_warning
console_error = log_mgr.console_error
configure_logging_level = log_mgr.configure_logging_level

DEFAULT_MODEL = cfg.DEFAULT_MODEL

AUDIO_MODE_DESC = assets.get_audio_mode_descriptions()
WRITTEN_MODE_DESC = assets.get_written_mode_descriptions()
TOP_LANGUAGES = assets.get_top_languages()


class MenuExit(Exception):
    """Raised when the user exits the interactive menu without running the pipeline."""


def prompt_user(prompt: str) -> str:
    """Return sanitized user input for interactive prompts."""

    try:
        response = input(prompt)
    except EOFError:
        return ""
    except KeyboardInterrupt:  # pragma: no cover - manual interruption
        print()
        raise

    if not response:
        return ""

    cleaned = response.replace("\r", "")
    cleaned = cleaned.rstrip("\n")
    return cleaned.strip()


def print_languages_in_four_columns() -> None:
    """Display the supported languages in four-column format."""

    languages = TOP_LANGUAGES[:]
    n_languages = len(languages)
    cols = 4
    rows = (n_languages + cols - 1) // cols
    col_width = max(len(language) for language in languages) + 4
    for row in range(rows):
        row_items: List[str] = []
        for col in range(cols):
            idx = row + col * rows
            if idx < n_languages:
                row_items.append(f"{idx + 1:2d}. {languages[idx]:<{col_width}}")
        if row_items:
            console_info("%s", "".join(row_items))


def default_base_output_file(config: Dict[str, Any]) -> str:
    if config.get("input_file"):
        base = os.path.splitext(os.path.basename(config["input_file"]))[0]
        target_lang = ", ".join(config.get("target_languages", context.default_target_languages()))
        output_dir = context.active_output_dir(config)
        default_file = os.path.join(
            str(output_dir),
            base,
            f"{target_lang}_{base}.html",
        )
    else:
        output_dir = context.active_output_dir(config)
        default_file = os.path.join(str(output_dir), "output.html")
    return default_file


def select_from_epub_directory(config: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    books_dir_path = context.active_books_dir(config)
    epub_files = sorted([p.name for p in books_dir_path.glob("*.epub")])
    if epub_files:
        for idx, file_name in enumerate(epub_files, start=1):
            console_info("%s. %s", idx, file_name)
    else:
        console_info("No EPUB files found in %s. You can type a custom path.", books_dir_path)
    default_input = config.get("input_file", epub_files[0] if epub_files else "")
    active_context = context.get_active_context(None)
    default_display = (
        str(cfg.resolve_file_path(default_input, active_context.books_dir))
        if default_input and active_context is not None
        else (str(cfg.resolve_file_path(default_input, None)) if default_input else "")
    )
    prompt_default = default_display or default_input
    inp_val = prompt_user(
        f"Select an input file by number or enter a path (default: {prompt_default}): "
    )
    if inp_val.isdigit() and 0 < int(inp_val) <= len(epub_files):
        config["input_file"] = epub_files[int(inp_val) - 1]
    elif inp_val:
        config["input_file"] = inp_val
    else:
        config["input_file"] = default_input
    return config, True


def format_selected_voice(selected: str) -> str:
    if selected == "macOS-auto-female":
        return "macOS auto (Premium/Enhanced preferred, female)"
    if selected == "macOS-auto-male":
        return "macOS auto (Premium/Enhanced preferred, male)"
    if selected == "macOS-auto":
        return "macOS auto (Premium/Enhanced preferred)"
    return selected
