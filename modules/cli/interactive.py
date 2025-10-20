"""Interactive CLI utilities for ebook-tools."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import metadata_manager
from .. import translation_engine
from ..core import ingestion
from ..core.config import build_pipeline_config
from ..services.pipeline_service import PipelineInput
from ..shared import assets
from . import context

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


def _prompt_user(prompt: str) -> str:
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


def _default_base_output_file(config: Dict[str, Any]) -> str:
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


def _select_from_epub_directory(config: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
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
    inp_val = _prompt_user(
        f"Select an input file by number or enter a path (default: {prompt_default}): "
    )
    if inp_val.isdigit() and 0 < int(inp_val) <= len(epub_files):
        config["input_file"] = epub_files[int(inp_val) - 1]
    elif inp_val:
        config["input_file"] = inp_val
    else:
        config["input_file"] = default_input
    return config, True


def _format_selected_voice(selected: str) -> str:
    if selected == "macOS-auto-female":
        return "macOS auto (Premium/Enhanced preferred, female)"
    if selected == "macOS-auto-male":
        return "macOS auto (Premium/Enhanced preferred, male)"
    if selected == "macOS-auto":
        return "macOS auto (Premium/Enhanced preferred)"
    return selected


def display_menu(config: Dict[str, Any], refined: Sequence[str], resolved_input: Optional[Path]) -> None:
    """Emit the interactive configuration summary for the user."""

    input_display = str(resolved_input) if resolved_input else config.get("input_file", "")
    console_info("\n--- File / Language Settings ---")
    console_info("1. Input EPUB file: %s", input_display)
    console_info("2. Base output file: %s", config.get("base_output_file", ""))
    console_info("3. Input language: %s", config.get("input_language", context.default_language()))
    console_info(
        "4. Target languages: %s",
        ", ".join(config.get("target_languages", context.default_target_languages())),
    )

    console_info("\n--- LLM, Audio, Video Settings ---")
    console_info("5. Ollama model: %s", config.get("ollama_model", DEFAULT_MODEL))
    console_info("6. Generate audio output: %s", config.get("generate_audio", True))
    console_info("7. Generate video slides: %s", config.get("generate_video", False))
    console_info(
        "8. Selected voice for audio generation: %s",
        _format_selected_voice(config.get("selected_voice", "gTTS")),
    )
    console_info(
        "9. macOS TTS reading speed (words per minute): %s",
        config.get("macos_reading_speed", 100),
    )
    console_info("10. Audio tempo (default: %s)", config.get("tempo", 1.0))
    console_info("11. Sync ratio for word slides: %s", config.get("sync_ratio", 0.9))
    console_info(
        "12. Worker thread count (1-10): %s",
        config.get("thread_count", cfg.DEFAULT_THREADS),
    )

    console_info("\n--- Sentence Parsing Settings ---")
    console_info(
        "13. Sentences per output file: %s",
        config.get("sentences_per_output_file", 10),
    )
    console_info(
        "14. Starting sentence (number or lookup word): %s",
        config.get("start_sentence", 1),
    )
    console_info(
        "15. Ending sentence (absolute or offset): %s",
        config.get("end_sentence", f"Last sentence [{len(refined)}]"),
    )
    console_info("16. Max words per sentence chunk: %s", config.get("max_words", context.DEFAULT_MAX))
    console_info(
        "17. Percentile for computing suggested max words: %s",
        config.get("percentile", assets.DEFAULT_ASSET_VALUES.get("percentile", 96)),
    )

    console_info("\n--- Format Options ---")
    console_info(
        "18. Audio output mode: %s (%s)",
        config.get("audio_mode", assets.DEFAULT_ASSET_VALUES.get("audio_mode", "1")),
        AUDIO_MODE_DESC.get(config.get("audio_mode", "1"), ""),
    )
    console_info(
        "19. Written output mode: %s (%s)",
        config.get("written_mode", assets.DEFAULT_ASSET_VALUES.get("written_mode", "4")),
        WRITTEN_MODE_DESC.get(config.get("written_mode", "4"), ""),
    )
    console_info(
        "20. Extend split logic with comma and semicolon: %s",
        "Yes" if config.get("split_on_comma_semicolon", False) else "No",
    )
    console_info(
        "21. Include transliteration for non-Latin alphabets: %s",
        config.get("include_transliteration", False),
    )
    console_info(
        "22. Word highlighting for video slides: %s",
        "Yes" if config.get("word_highlighting", True) else "No",
    )
    console_info("23. Debug mode: %s", config.get("debug", False))
    console_info("24. HTML output: %s", config.get("output_html", True))
    console_info("25. PDF output: %s", config.get("output_pdf", False))
    console_info("26. Generate stitched full output file: %s", config.get("stitch_full", False))

    console_info("\n--- Book Metadata ---")
    console_info("27. Book Title: %s", config.get("book_title"))
    console_info("28. Author: %s", config.get("book_author"))
    console_info("29. Year: %s", config.get("book_year"))
    console_info("30. Summary: %s", config.get("book_summary"))
    console_info("31. Book Cover File: %s", config.get("book_cover_file", "None"))

    console_info("\n--- Paths and Services ---")
    console_info("32. Working directory: %s", config.get("working_dir"))
    console_info("33. Output directory: %s", config.get("output_dir"))
    console_info("34. Ebooks directory: %s", config.get("ebooks_dir"))
    console_info("35. Temporary directory: %s", config.get("tmp_dir"))
    console_info("36. FFmpeg path: %s", config.get("ffmpeg_path"))
    console_info(
        "37. LLM source: %s",
        config.get("llm_source", cfg.DEFAULT_LLM_SOURCE),
    )
    console_info("38. Ollama API URL: %s", config.get("ollama_url"))
    console_info(
        "39. Local Ollama URL: %s",
        config.get("ollama_local_url", cfg.DEFAULT_OLLAMA_URL),
    )
    console_info(
        "40. Ollama Cloud URL: %s",
        config.get("ollama_cloud_url", cfg.DEFAULT_OLLAMA_CLOUD_URL),
    )
    console_info(
        "\nPress Enter to confirm settings, choose a number to edit, or type 'q' to quit the menu."
    )


def edit_parameter(
    config: Dict[str, Any],
    selection: int,
    refined: Sequence[str],
    overrides: Dict[str, Any],
    debug_enabled: bool,
) -> Tuple[Dict[str, Any], bool]:
    """Handle a parameter edit request from the interactive menu."""

    refined_cache_stale = False
    active_context = context.get_active_context(None)

    if selection == 1:
        previous_input = config.get("input_file")
        previous_default_output = _default_base_output_file(config) if previous_input else None
        previous_base_output = config.get("base_output_file")

        config, refined_cache_stale = _select_from_epub_directory(config)
        books_base = active_context.books_dir if active_context is not None else None
        resolved_input_path = cfg.resolve_file_path(config.get("input_file"), books_base)

        if config.get("input_file") != previous_input:
            for field in (
                "book_title",
                "book_author",
                "book_year",
                "book_summary",
                "book_cover_file",
            ):
                config.pop(field, None)

        if (
            resolved_input_path
            and config.get("auto_metadata", True)
            and resolved_input_path.exists()
        ):
            metadata_manager.populate_config_metadata(
                config,
                str(resolved_input_path),
                force=True,
            )

        if config.get("input_file") != previous_input:
            new_default_output = _default_base_output_file(config)
            if not previous_base_output or previous_base_output == previous_default_output:
                config["base_output_file"] = new_default_output
    elif selection == 2:
        default_file = _default_base_output_file(config)
        inp_val = _prompt_user(
            f"Enter base output file name (default: {default_file}): "
        )
        config["base_output_file"] = inp_val if inp_val else default_file
    elif selection == 3:
        console_info("\nSelect input language:")
        print_languages_in_four_columns()
        default_in = config.get("input_language", context.default_language())
        inp_val = _prompt_user(
            f"Select input language by number (default: {default_in}): "
        )
        if inp_val.isdigit() and 0 < int(inp_val) <= len(TOP_LANGUAGES):
            config["input_language"] = TOP_LANGUAGES[int(inp_val) - 1]
        else:
            config["input_language"] = default_in
    elif selection == 4:
        console_info(
            "\nSelect target languages (separate choices by comma, e.g. 1,4,7):"
        )
        print_languages_in_four_columns()
        default_targets = config.get("target_languages", context.default_target_languages())
        inp_val = _prompt_user(
            f"Select target languages by number (default: {', '.join(default_targets)}): "
        )
        if inp_val:
            choices = [int(x) for x in inp_val.split(",") if x.strip().isdigit()]
            selected = [
                TOP_LANGUAGES[x - 1]
                for x in choices
                if 0 < x <= len(TOP_LANGUAGES)
            ]
            config["target_languages"] = selected or default_targets
        else:
            config["target_languages"] = default_targets
    elif selection == 5:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=True,
            )
            models = [line.split()[0] for line in result.stdout.splitlines() if line]
        except Exception:
            models = []
        if not models:
            console_warning("No local Ollama models detected. Keeping current selection.")
        else:
            console_info("Available models:")
            for idx, model in enumerate(models, start=1):
                console_info("%s. %s", idx, model)
            default_model = config.get("ollama_model", DEFAULT_MODEL)
            inp_val = _prompt_user(
                f"Select model by number (default: {default_model}): "
            )
            if inp_val.isdigit() and 0 < int(inp_val) <= len(models):
                config["ollama_model"] = models[int(inp_val) - 1]
            else:
                config["ollama_model"] = default_model
    elif selection == 6:
        default_audio = config.get("generate_audio", True)
        inp_val = _prompt_user(
            f"Generate audio output? (yes/no, default {'yes' if default_audio else 'no'}): "
        ).lower()
        config["generate_audio"] = True if inp_val in ["", "yes", "y"] else False
    elif selection == 7:
        default_video = config.get("generate_video", False)
        inp_val = _prompt_user(
            f"Generate video slides? (yes/no, default {'yes' if default_video else 'no'}): "
        ).lower()
        config["generate_video"] = True if inp_val in ["yes", "y"] else False
    elif selection == 8:
        voices = context.get_macos_voices(debug_enabled=debug_enabled)
        voices.extend(["gTTS", "macOS-auto", "macOS-auto-female", "macOS-auto-male"])
        for idx, voice in enumerate(voices, start=1):
            console_info("%s. %s", idx, voice)
        default_voice = config.get("selected_voice", "gTTS")
        inp_val = _prompt_user(
            f"Select voice by number (default: {default_voice}): "
        )
        if inp_val.isdigit() and 0 < int(inp_val) <= len(voices):
            selected = voices[int(inp_val) - 1]
            if selected.startswith("macOS auto"):
                config["selected_voice"] = "macOS-auto"
            elif selected.endswith("female"):
                config["selected_voice"] = "macOS-auto-female"
            elif selected.endswith("male"):
                config["selected_voice"] = "macOS-auto-male"
            else:
                config["selected_voice"] = selected
        else:
            config["selected_voice"] = default_voice
    elif selection == 9:
        default_speed = config.get("macos_reading_speed", 100)
        inp_val = _prompt_user(
            f"Enter macOS TTS reading speed (words per minute, default {default_speed}): "
        )
        if inp_val.isdigit():
            config["macos_reading_speed"] = int(inp_val)
        else:
            config["macos_reading_speed"] = default_speed
    elif selection == 10:
        default_tempo = config.get("tempo", 1.0)
        inp_val = _prompt_user(
            f"Enter audio tempo multiplier (default {default_tempo}): "
        )
        try:
            config["tempo"] = float(inp_val) if inp_val else default_tempo
        except ValueError:
            config["tempo"] = default_tempo
    elif selection == 11:
        default_sync = config.get("sync_ratio", 0.9)
        inp_val = _prompt_user(
            f"Enter sync ratio for word slides (default {default_sync}): "
        )
        try:
            config["sync_ratio"] = float(inp_val) if inp_val else default_sync
        except ValueError:
            config["sync_ratio"] = default_sync
    elif selection == 12:
        default_threads = config.get("thread_count", cfg.DEFAULT_THREADS)
        inp_val = _prompt_user(
            f"Enter worker thread count (default {default_threads}): "
        )
        if inp_val.isdigit():
            config["thread_count"] = max(1, min(10, int(inp_val)))
        else:
            config["thread_count"] = default_threads
    elif selection == 13:
        default_sentences = config.get("sentences_per_output_file", 10)
        inp_val = _prompt_user(
            f"Enter sentences per output file (default {default_sentences}): "
        )
        if inp_val.isdigit():
            config["sentences_per_output_file"] = int(inp_val)
        else:
            config["sentences_per_output_file"] = default_sentences
    elif selection == 14:
        default_start = config.get("start_sentence", 1)
        inp_val = _prompt_user(
            f"Enter starting sentence number or lookup term (default {default_start}): "
        )
        if inp_val.isdigit():
            config["start_sentence"] = int(inp_val)
            config.pop("start_sentence_lookup", None)
        elif inp_val:
            config["start_sentence_lookup"] = inp_val
        else:
            config["start_sentence"] = default_start
    elif selection == 15:
        default_end = config.get("end_sentence")
        inp_val = _prompt_user(
            "Enter ending sentence (number, +/- offset, or blank for none): "
        )
        if not inp_val:
            config["end_sentence"] = default_end
        elif inp_val[0] in ["+", "-"]:
            try:
                offset = int(inp_val)
                start_val = int(config.get("start_sentence", 1))
                config["end_sentence"] = start_val + offset
                console_info("Ending sentence updated to %s", config["end_sentence"])
            except Exception:
                config["end_sentence"] = default_end
        elif inp_val.isdigit():
            config["end_sentence"] = int(inp_val)
        else:
            config["end_sentence"] = default_end
    elif selection == 16:
        default_max = config.get("max_words", context.DEFAULT_MAX)
        inp_val = _prompt_user(
            f"Enter maximum words per sentence chunk (default {default_max}): "
        )
        if inp_val.isdigit():
            config["max_words"] = int(inp_val)
            config["max_words_manual"] = True
            context.recalculate_percentile(config)
        else:
            config["max_words"] = default_max
    elif selection == 17:
        default_perc = config.get("percentile", assets.DEFAULT_ASSET_VALUES.get("percentile", 96))
        inp_val = _prompt_user(
            f"Enter percentile for suggested max words (default {default_perc}): "
        )
        if inp_val.isdigit():
            perc = int(inp_val)
            if 1 <= perc <= 100:
                config["percentile"] = perc
            else:
                console_warning("Invalid percentile, must be between 1 and 100. Keeping previous value.")
        else:
            config["percentile"] = default_perc
    elif selection == 18:
        default_am = config.get("audio_mode", assets.DEFAULT_ASSET_VALUES.get("audio_mode", "1"))
        console_info("\nChoose audio output mode:")
        for key, description in AUDIO_MODE_DESC.items():
            console_info("%s: %s", key, description)
        inp_val = _prompt_user(
            f"Select audio output mode (default {default_am}): "
        )
        config["audio_mode"] = inp_val if inp_val in AUDIO_MODE_DESC else default_am
    elif selection == 19:
        default_wm = config.get("written_mode", assets.DEFAULT_ASSET_VALUES.get("written_mode", "4"))
        console_info("\nChoose written output mode:")
        for key, description in WRITTEN_MODE_DESC.items():
            console_info("%s: %s", key, description)
        inp_val = _prompt_user(
            f"Select written output mode (default {default_wm}): "
        )
        config["written_mode"] = inp_val if inp_val in WRITTEN_MODE_DESC else default_wm
    elif selection == 20:
        default_split = config.get("split_on_comma_semicolon", False)
        inp_val = _prompt_user(
            f"Extend split logic with comma and semicolon? (yes/no, default {'yes' if default_split else 'no'}): "
        ).lower()
        config["split_on_comma_semicolon"] = True if inp_val in ["yes", "y"] else default_split
    elif selection == 21:
        default_translit = config.get("include_transliteration", False)
        inp_val = _prompt_user(
            f"Include transliteration for non-Latin alphabets? (yes/no, default {'yes' if default_translit else 'no'}): "
        ).lower()
        config["include_transliteration"] = True if inp_val in ["yes", "y"] else False
    elif selection == 22:
        default_highlight = config.get("word_highlighting", True)
        inp_val = _prompt_user(
            f"Enable word highlighting for video slides? (yes/no, default {'yes' if default_highlight else 'no'}): "
        ).lower()
        config["word_highlighting"] = True if inp_val in ["", "yes", "y"] else False
    elif selection == 23:
        default_debug = config.get("debug", False)
        inp_val = _prompt_user(
            f"Enable debug mode? (yes/no, default {'yes' if default_debug else 'no'}): "
        ).lower()
        config["debug"] = True if inp_val in ["yes", "y"] else False
        configure_logging_level(config["debug"])
        translation_engine.configure_default_client(debug=config["debug"])
    elif selection == 24:
        default_html = config.get("output_html", True)
        inp_val = _prompt_user(
            f"Generate HTML output? (yes/no, default {'yes' if default_html else 'no'}): "
        ).lower()
        config["output_html"] = True if inp_val in ["", "yes", "y"] else False
    elif selection == 25:
        default_pdf = config.get("output_pdf", False)
        inp_val = _prompt_user(
            f"Generate PDF output? (yes/no, default {'yes' if default_pdf else 'no'}): "
        ).lower()
        config["output_pdf"] = True if inp_val in ["yes", "y"] else False
    elif selection == 26:
        default_stitch = config.get("stitch_full", False)
        inp_val = _prompt_user(
            f"Generate stitched full output file? (yes/no, default {'yes' if default_stitch else 'no'}): "
        ).lower()
        config["stitch_full"] = True if inp_val in ["yes", "y"] else False
    elif selection == 27:
        default_title = config.get("book_title", "")
        inp_val = _prompt_user(
            f"Enter book title (default: {default_title}): "
        )
        if inp_val:
            config["book_title"] = inp_val
    elif selection == 28:
        default_author = config.get("book_author", "")
        inp_val = _prompt_user(
            f"Enter author name (default: {default_author}): "
        )
        if inp_val:
            config["book_author"] = inp_val
    elif selection == 29:
        default_year = config.get("book_year", "")
        inp_val = _prompt_user(
            f"Enter publication year (default: {default_year}): "
        )
        if inp_val:
            config["book_year"] = inp_val
    elif selection == 30:
        default_summary = config.get("book_summary", "")
        inp_val = _prompt_user(
            "Enter book summary (press Enter to keep current): "
        )
        if inp_val:
            config["book_summary"] = inp_val
    elif selection == 31:
        current_cover = config.get("book_cover_file") or "None"
        inp_val = _prompt_user(
            f"Enter book cover file path (default: {current_cover}): "
        )
        if inp_val:
            config["book_cover_file"] = inp_val
        config = context.update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=debug_enabled,
            context=context.get_active_context(None),
        )
    elif selection == 32:
        current = config.get("working_dir")
        inp_val = _prompt_user(
            f"Enter working directory (default: {current}): "
        )
        if inp_val:
            config["working_dir"] = inp_val
        active_context = context.refresh_runtime_context(config, overrides)
        config = context.update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=debug_enabled,
            context=active_context,
        )
        refined_cache_stale = True
    elif selection == 33:
        current = config.get("output_dir")
        inp_val = _prompt_user(
            f"Enter output directory (default: {current}): "
        )
        if inp_val:
            config["output_dir"] = inp_val
        context.refresh_runtime_context(config, overrides)
        refined_cache_stale = True
    elif selection == 34:
        current = config.get("ebooks_dir")
        inp_val = _prompt_user(
            f"Enter ebooks directory (default: {current}): "
        )
        if inp_val:
            config["ebooks_dir"] = inp_val
        active_context = context.refresh_runtime_context(config, overrides)
        config = context.update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=debug_enabled,
            context=active_context,
        )
        refined_cache_stale = True
    elif selection == 35:
        current = config.get("tmp_dir")
        inp_val = _prompt_user(
            f"Enter temporary directory (default: {current}): "
        )
        if inp_val:
            config["tmp_dir"] = inp_val
        context.refresh_runtime_context(config, overrides)
    elif selection == 36:
        current = config.get("ffmpeg_path")
        inp_val = _prompt_user(
            f"Enter FFmpeg executable path (default: {current}): "
        )
        if inp_val:
            config["ffmpeg_path"] = inp_val
        context.refresh_runtime_context(config, overrides)
    elif selection == 37:
        current = config.get("llm_source", cfg.DEFAULT_LLM_SOURCE)
        inp_val = _prompt_user(
            f"Select LLM source (local/cloud) (current: {current}): "
        ).strip().lower()
        if inp_val:
            if inp_val in cfg.VALID_LLM_SOURCES:
                config["llm_source"] = inp_val
                context.refresh_runtime_context(config, overrides)
            else:
                console_warning("Invalid LLM source. Please enter 'local' or 'cloud'.")
    elif selection == 38:
        current = config.get("ollama_url")
        inp_val = _prompt_user(
            f"Enter Ollama API URL (default: {current}): "
        )
        if inp_val:
            config["ollama_url"] = inp_val
        context.refresh_runtime_context(config, overrides)
    elif selection == 39:
        current = config.get("ollama_local_url", cfg.DEFAULT_OLLAMA_URL)
        inp_val = _prompt_user(
            f"Enter local Ollama URL (default: {current}): "
        )
        if inp_val:
            config["ollama_local_url"] = inp_val
        context.refresh_runtime_context(config, overrides)
    elif selection == 40:
        current = config.get("ollama_cloud_url", cfg.DEFAULT_OLLAMA_CLOUD_URL)
        inp_val = _prompt_user(
            f"Enter Ollama Cloud URL (default: {current}): "
        )
        if inp_val:
            config["ollama_cloud_url"] = inp_val
        context.refresh_runtime_context(config, overrides)
    else:
        console_warning("Invalid parameter number. Please try again.")

    return config, refined_cache_stale


def confirm_settings(
    config: Dict[str, Any],
    resolved_input: Optional[Path],
    entry_script_name: str,
) -> Tuple[Dict[str, Any], PipelineInput]:
    """Finalize the interactive session and prepare pipeline arguments."""

    resolved_input_str = str(resolved_input) if resolved_input else config.get("input_file", "")
    input_arg = f'"{resolved_input_str}"'
    target_languages = config.get("target_languages", context.default_target_languages())
    target_arg = f'"{",".join(target_languages)}"'
    cmd_parts = [
        os.path.basename(sys.executable) if sys.executable else "python3",
        entry_script_name,
        input_arg,
        f'"{config.get("input_language", context.default_language())}"',
        target_arg,
        str(config.get("sentences_per_output_file", 10)),
        f'"{config.get("base_output_file", "")}"',
        str(config.get("start_sentence", 1)),
    ]
    if config.get("end_sentence") is not None:
        cmd_parts.append(str(config.get("end_sentence")))
    if config.get("debug"):
        cmd_parts.append("--debug")
    console_info("\nTo run non-interactively with these settings, use the following command:")
    console_info("%s", " ".join(cmd_parts))

    book_metadata = {
        "book_title": config.get("book_title"),
        "book_author": config.get("book_author"),
        "book_year": config.get("book_year"),
        "book_summary": config.get("book_summary"),
        "book_cover_file": config.get("book_cover_file"),
    }

    pipeline_input = PipelineInput(
        input_file=resolved_input_str,
        base_output_file=config.get("base_output_file", ""),
        input_language=config.get("input_language", context.default_language()),
        target_languages=target_languages,
        sentences_per_output_file=config.get("sentences_per_output_file", 10),
        start_sentence=config.get("start_sentence", 1),
        end_sentence=config.get("end_sentence"),
        stitch_full=config.get("stitch_full", False),
        generate_audio=config.get("generate_audio", True),
        audio_mode=config.get("audio_mode", assets.DEFAULT_ASSET_VALUES.get("audio_mode", "1")),
        written_mode=config.get("written_mode", assets.DEFAULT_ASSET_VALUES.get("written_mode", "4")),
        selected_voice=config.get("selected_voice", "gTTS"),
        output_html=config.get("output_html", True),
        output_pdf=config.get("output_pdf", False),
        generate_video=config.get("generate_video", False),
        include_transliteration=config.get("include_transliteration", False),
        tempo=config.get("tempo", 1.0),
        book_metadata=book_metadata,
    )
    return config, pipeline_input


def run_interactive_menu(
    overrides: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
    entry_script_name: str = "main.py",
) -> Tuple[Dict[str, Any], PipelineInput]:
    """Run the interactive configuration menu and return the final configuration."""

    overrides = overrides or {}
    previous_menu_flag = os.environ.get("EBOOK_MENU_ACTIVE")
    os.environ["EBOOK_MENU_ACTIVE"] = "1"
    try:
        if config_path:
            config_file_path = Path(config_path).expanduser()
            if not config_file_path.is_absolute():
                config_file_path = (Path.cwd() / config_file_path).resolve()
        else:
            config_file_path = cfg.DEFAULT_LOCAL_CONFIG_PATH

        config = cfg.load_configuration(config_file_path, verbose=True)
        configure_logging_level(config.get("debug", False))

        if "start_sentence" in config and not str(config["start_sentence"]).isdigit():
            config["start_sentence_lookup"] = config["start_sentence"]

        active_context = context.refresh_runtime_context(config, overrides)
        config = context.update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=config.get("debug", False),
            context=active_context,
        )

        refined_cache_stale = True
        refined: List[str] = []

        while True:
            active_context = context.get_active_context(None)
            resolved_input_path = cfg.resolve_file_path(
                config.get("input_file"),
                active_context.books_dir if active_context is not None else None,
            )

            if (
                resolved_input_path
                and config.get("auto_metadata", True)
                and resolved_input_path.exists()
            ):
                metadata_manager.populate_config_metadata(
                    config,
                    str(resolved_input_path),
                )

            if config.get("input_file"):
                active_context = context.get_active_context(None)
                if active_context is None:
                    active_context = context.refresh_runtime_context(config, overrides)
                pipeline_config = build_pipeline_config(active_context, config)
                refined, refreshed = ingestion.get_refined_sentences(
                    config["input_file"],
                    pipeline_config,
                    force_refresh=refined_cache_stale,
                    metadata={"mode": "interactive"},
                )
                if refreshed:
                    console_info(
                        "Refined sentence list written to: %s",
                        ingestion.refined_list_output_path(
                            config["input_file"], pipeline_config
                        ),
                    )
                refined_cache_stale = False
            else:
                refined = []

            config = context.update_sentence_config(config, refined)

            display_menu(config, refined, resolved_input_path)

            inp_choice_raw = _prompt_user(
                "\nEnter a parameter number to change (or press Enter to confirm): "
            )
            inp_choice = inp_choice_raw.strip()
            if inp_choice.lower() == "q":
                console_info("Interactive session exited by user request.")
                raise MenuExit()
            if inp_choice == "":
                break
            if not inp_choice.isdigit():
                console_warning("Invalid input. Please enter a number or press Enter.")
                continue
            selection = int(inp_choice)
            config, made_stale = edit_parameter(
                config,
                selection,
                refined,
                overrides,
                config.get("debug", False),
            )
            refined_cache_stale = refined_cache_stale or made_stale

            try:
                config_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_file_path, "w", encoding="utf-8") as cfg_file:
                    json.dump(cfg.strip_derived_config(config), cfg_file, indent=4)
                console_info("Configuration saved to %s", config_file_path)
            except Exception as exc:
                console_error("Error saving configuration: %s", exc)

        active_context = context.get_active_context(None)
        resolved_input_path = cfg.resolve_file_path(
            config.get("input_file"),
            active_context.books_dir if active_context is not None else None,
        )
        config, pipeline_input = confirm_settings(
            config, resolved_input_path, entry_script_name
        )

        if active_context is None:
            active_context = context.refresh_runtime_context(config, overrides)

        pipeline_config = build_pipeline_config(active_context, config)
        pipeline_config.apply_runtime_settings()
        configure_logging_level(pipeline_config.debug)

        return config, pipeline_input
    finally:
        if previous_menu_flag is None:
            os.environ.pop("EBOOK_MENU_ACTIVE", None)
        else:
            os.environ["EBOOK_MENU_ACTIVE"] = previous_menu_flag


__all__ = [
    "AUDIO_MODE_DESC",
    "MenuExit",
    "TOP_LANGUAGES",
    "confirm_settings",
    "display_menu",
    "edit_parameter",
    "print_languages_in_four_columns",
    "run_interactive_menu",
]
