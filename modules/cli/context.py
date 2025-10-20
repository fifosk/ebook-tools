"""Runtime context helpers for CLI workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from ..audio.tts import macos_voice_inventory
from ..book_cover import fetch_book_cover
from ..epub_parser import (
    DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    DEFAULT_MAX_WORDS,
    extract_text_from_epub,
    split_text_into_sentences,
)
from ..shared import assets

console_info = log_mgr.console_info
console_warning = log_mgr.console_warning

DEFAULT_EXTEND = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON
DEFAULT_MAX = DEFAULT_MAX_WORDS


def refresh_runtime_context(
    config: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None
) -> cfg.RuntimeContext:
    """Build and activate a runtime context for menu operations."""

    overrides = overrides or {}
    context = cfg.build_runtime_context(config, overrides)
    cfg.set_runtime_context(context)
    return context


def get_active_context(default: Optional[cfg.RuntimeContext] = None) -> Optional[cfg.RuntimeContext]:
    """Return the currently active runtime context."""

    return cfg.get_runtime_context(default)


def active_books_dir(config: Dict[str, Any]) -> Path:
    """Return the effective books directory based on the current context."""

    context = get_active_context(None)
    if context is not None:
        return context.books_dir
    return cfg.resolve_directory(config.get("ebooks_dir"), cfg.DEFAULT_BOOKS_RELATIVE)


def active_output_dir(config: Dict[str, Any]) -> Path:
    """Return the effective output directory based on the current context."""

    context = get_active_context(None)
    if context is not None:
        return context.output_dir
    return cfg.resolve_directory(config.get("output_dir"), cfg.DEFAULT_OUTPUT_RELATIVE)


def update_book_cover_file_in_config(
    config: Dict[str, Any],
    ebooks_dir_value: Optional[str],
    *,
    debug_enabled: bool = False,
    context: Optional[cfg.RuntimeContext] = None,
) -> Dict[str, Any]:
    """Ensure the configuration references an available book cover file."""

    title = config.get("book_title", "Unknown Title")
    author = config.get("book_author", "Unknown Author")
    ebooks_dir_value = ebooks_dir_value or str(cfg.DEFAULT_BOOKS_RELATIVE)
    context = context or get_active_context(None)
    ebooks_dir_path = (
        context.books_dir
        if context is not None
        else cfg.resolve_directory(ebooks_dir_value, cfg.DEFAULT_BOOKS_RELATIVE)
    )
    default_cover_relative = "book_cover.jpg"
    default_cover_path = ebooks_dir_path / default_cover_relative

    cover_file = config.get("book_cover_file")
    cover_base = context.books_dir if context is not None else None
    cover_path = cfg.resolve_file_path(cover_file, cover_base)
    if cover_path and cover_path.exists():
        return config

    if default_cover_path.exists():
        config["book_cover_file"] = default_cover_relative
        config["book_cover_title"] = title
        return config

    cover_image = fetch_book_cover(f"{title} {author}", debug_enabled=debug_enabled)
    if cover_image:
        cover_image.thumbnail((80, 80))
        try:
            cover_image.save(default_cover_path, format="JPEG")
        except Exception as exc:  # pragma: no cover - file system errors
            if debug_enabled:
                console_warning("Unable to save downloaded cover image: %s", exc)
        else:
            config["book_cover_file"] = default_cover_relative
            config["book_cover_title"] = title
            return config

    config["book_cover_file"] = None
    return config


def update_sentence_config(config: Dict[str, Any], refined_list: Sequence[str]) -> Dict[str, Any]:
    """Resolve start sentence lookups to numeric positions when possible."""

    lookup = config.get("start_sentence_lookup")
    if lookup:
        query = lookup.strip()
        found_index = None
        for idx, sentence in enumerate(refined_list):
            if query.lower() in sentence.lower():
                found_index = idx
                break
        if found_index is not None:
            config["start_sentence"] = found_index + 1
            console_info(
                "(Lookup) Starting sentence updated to %s based on query '%s'.",
                config["start_sentence"],
                query,
            )
        else:
            config["start_sentence"] = 1
            console_info("(Lookup) Query '%s' not found. Starting sentence set to 1.", query)
        config["start_sentence_lookup"] = ""
    else:
        try:
            config["start_sentence"] = int(config.get("start_sentence", 1))
        except Exception:
            config["start_sentence"] = 1
    return config


def get_macos_voices(debug_enabled: bool = False) -> List[str]:
    """Return available macOS voices filtered to Enhanced/Premium quality."""

    voices = []
    for name, locale, quality, gender in macos_voice_inventory(debug_enabled=debug_enabled):
        if quality not in {"Enhanced", "Premium"}:
            continue
        gender_suffix = f" - {gender.capitalize()}" if gender else ""
        voices.append(f"{name} - {locale} - ({quality}){gender_suffix}")
    return voices


def recalculate_percentile(config: Dict[str, Any]) -> None:
    """Recalculate percentile guidance after manual ``max_words`` edits."""

    text = extract_text_from_epub(config["input_file"])
    refined_tmp = split_text_into_sentences(
        text,
        max_words=config.get("max_words", DEFAULT_MAX),
        extend_split_with_comma_semicolon=config.get(
            "split_on_comma_semicolon",
            DEFAULT_EXTEND,
        ),
    )
    lengths = [len(sentence.split()) for sentence in refined_tmp]
    new_percentile = None
    for idx, length in enumerate(lengths):
        if length >= config["max_words"]:
            new_percentile = int(((idx + 1) / len(lengths)) * 100)
            break
    config["percentile"] = new_percentile if new_percentile is not None else 100


def default_language() -> str:
    return assets.DEFAULT_ASSET_VALUES.get("input_language", "English")


def default_target_languages() -> List[str]:
    return assets.DEFAULT_ASSET_VALUES.get("target_languages", ["Arabic"]).copy()


__all__ = [
    "DEFAULT_EXTEND",
    "DEFAULT_MAX",
    "active_books_dir",
    "active_output_dir",
    "default_language",
    "default_target_languages",
    "get_active_context",
    "get_macos_voices",
    "recalculate_percentile",
    "refresh_runtime_context",
    "update_book_cover_file_in_config",
    "update_sentence_config",
]
