#!/usr/bin/env python3
"""Interactive menu and CLI handling for ebook-tools."""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
from PIL import Image

from . import config_manager as cfg
from . import logging_manager as log_mgr
from . import translation_engine
from .epub_parser import (
    DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    DEFAULT_MAX_WORDS,
    extract_text_from_epub,
    split_text_into_sentences,
)

logger = log_mgr.logger
configure_logging_level = log_mgr.configure_logging_level
resolve_directory = cfg.resolve_directory
resolve_file_path = cfg.resolve_file_path
initialize_environment = cfg.initialize_environment
load_configuration = cfg.load_configuration
strip_derived_config = cfg.strip_derived_config

DEFAULT_MODEL = cfg.DEFAULT_MODEL
DEFAULT_BOOKS_RELATIVE = cfg.DEFAULT_BOOKS_RELATIVE
DEFAULT_LOCAL_CONFIG_PATH = cfg.DEFAULT_LOCAL_CONFIG_PATH
DEFAULT_EXTEND = DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON
DEFAULT_MAX = DEFAULT_MAX_WORDS

AUDIO_MODE_DESC = {
    "1": "Only translated sentence",
    "2": "Sentence numbering + translated sentence",
    "3": "Full original format (numbering, original sentence, translated sentence)",
    "4": "Original sentence + translated sentence",
}

WRITTEN_MODE_DESC = {
    "1": "Only fluent translation",
    "2": "Sentence numbering + fluent translation",
    "3": "Full original format (numbering, original sentence, fluent translation)",
    "4": "Original sentence + fluent translation",
}

TOP_LANGUAGES = [
    "Afrikaans", "Albanian", "Arabic", "Armenian", "Basque", "Bengali", "Bosnian", "Burmese",
    "Catalan", "Chinese (Simplified)", "Chinese (Traditional)", "Czech", "Croatian", "Danish",
    "Dutch", "English", "Esperanto", "Estonian", "Filipino", "Finnish", "French", "German",
    "Greek", "Gujarati", "Hausa", "Hebrew", "Hindi", "Hungarian", "Icelandic", "Indonesian",
    "Italian", "Japanese", "Javanese", "Kannada", "Khmer", "Korean", "Latin", "Latvian",
    "Macedonian", "Malay", "Malayalam", "Marathi", "Nepali", "Norwegian", "Polish",
    "Portuguese", "Romanian", "Russian", "Sinhala", "Slovak", "Serbian", "Sundanese",
    "Swahili", "Swedish", "Tamil", "Telugu", "Thai", "Turkish", "Ukrainian", "Urdu",
    "Vietnamese", "Welsh", "Xhosa", "Yoruba", "Zulu", "Persian",
]


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command line arguments for the ebook tools pipeline."""
    parser = argparse.ArgumentParser(description="Generate translated outputs from EPUB files.")
    parser.add_argument("input_file", nargs="?", help="Path to the input EPUB file.")
    parser.add_argument("input_language", nargs="?", help="Source language of the EPUB text.")
    parser.add_argument("target_languages", nargs="?", help="Comma-separated list of target languages.")
    parser.add_argument(
        "sentences_per_output_file",
        nargs="?",
        type=int,
        help="Number of sentences per generated output file.",
    )
    parser.add_argument("base_output_file", nargs="?", help="Base path for generated output files.")
    parser.add_argument("start_sentence", nargs="?", type=int, help="Sentence number to start processing from.")
    parser.add_argument(
        "end_sentence",
        nargs="?",
        help="Sentence number (or offset) to stop processing at.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a configuration override JSON file (defaults to conf/config.local.json if present).",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Open the interactive configuration menu.",
    )
    parser.add_argument("--ebooks-dir", help="Directory containing source EPUB files and cover images.")
    parser.add_argument("--working-dir", help="Override the working directory for intermediate files.")
    parser.add_argument("--output-dir", help="Override the output directory for generated files.")
    parser.add_argument("--tmp-dir", help="Override the temporary directory for transient files.")
    parser.add_argument("--ffmpeg-path", help="Override the path to the FFmpeg executable.")
    parser.add_argument("--ollama-url", help="Override the Ollama API URL.")
    parser.add_argument(
        "--thread-count",
        type=int,
        help="Number of worker threads to use for translation and media generation.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging output.")
    return parser.parse_args(argv)


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
            logger.info("%s", "".join(row_items))


def fetch_book_cover(query: str, debug_enabled: bool = False) -> Optional[Image.Image]:
    """Retrieve a book cover image from OpenLibrary when available."""
    encoded = urllib.parse.quote(query)
    url = f"http://openlibrary.org/search.json?title={encoded}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        for doc in data.get("docs", []):
            if "cover_i" not in doc:
                continue
            cover_id = doc["cover_i"]
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
            cover_response = requests.get(cover_url, stream=True, timeout=10)
            if cover_response.status_code == 200:
                return Image.open(io.BytesIO(cover_response.content))
        return None
    except Exception as exc:  # pragma: no cover - network errors
        if debug_enabled:
            logger.error("Error fetching book cover: %s", exc)
        return None


def update_book_cover_file_in_config(
    config: Dict[str, Any],
    ebooks_dir_value: Optional[str],
    debug_enabled: bool = False,
) -> Dict[str, Any]:
    """Ensure the configuration references an available book cover file."""
    title = config.get("book_title", "Unknown Title")
    author = config.get("book_author", "Unknown Author")
    ebooks_dir_value = ebooks_dir_value or str(DEFAULT_BOOKS_RELATIVE)
    ebooks_dir_path = (
        Path(cfg.BOOKS_DIR)
        if cfg.BOOKS_DIR
        else resolve_directory(ebooks_dir_value, DEFAULT_BOOKS_RELATIVE)
    )
    default_cover_relative = "book_cover.jpg"
    default_cover_path = ebooks_dir_path / default_cover_relative

    cover_file = config.get("book_cover_file")
    cover_path = resolve_file_path(cover_file, cfg.BOOKS_DIR)
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
                logger.warning("Unable to save downloaded cover image: %s", exc)
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
            logger.info(
                "(Lookup) Starting sentence updated to %s based on query '%s'.",
                config["start_sentence"],
                query,
            )
        else:
            config["start_sentence"] = 1
            logger.info("(Lookup) Query '%s' not found. Starting sentence set to 1.", query)
        config["start_sentence_lookup"] = ""
    else:
        try:
            config["start_sentence"] = int(config.get("start_sentence", 1))
        except Exception:
            config["start_sentence"] = 1
    return config


def get_macos_voices(debug_enabled: bool = False) -> List[str]:
    """Return available macOS voices filtered to Enhanced/Premium quality."""
    try:
        output = subprocess.check_output(["say", "-v", "?"], universal_newlines=True)
    except Exception as exc:  # pragma: no cover - platform specific
        if debug_enabled:
            logger.error("Error retrieving macOS voices: %s", exc)
        return []

    voices: List[str] = []
    for line in output.splitlines():
        details = line.strip().split("#")[0].strip().split()
        if len(details) >= 3 and details[1].startswith("("):
            voice_name = details[0]
            quality = details[1].strip("()")
            locale = details[2]
        elif len(details) >= 2:
            voice_name = details[0]
            locale = details[1]
            quality = ""
        else:
            continue
        if quality in {"Enhanced", "Premium"}:
            voices.append(f"{voice_name} - {locale} - ({quality})")
    return voices


def display_menu(config: Dict[str, Any], refined: Sequence[str], resolved_input: Optional[Path]) -> None:
    """Emit the interactive configuration summary for the user."""
    input_display = str(resolved_input) if resolved_input else config.get("input_file", "")
    logger.info("\n--- File / Language Settings ---")
    logger.info("1. Input EPUB file: %s", input_display)
    logger.info("2. Base output file: %s", config.get("base_output_file", ""))
    logger.info("3. Input language: %s", config.get("input_language", "English"))
    logger.info(
        "4. Target languages: %s",
        ", ".join(config.get("target_languages", ["Arabic"])),
    )

    logger.info("\n--- LLM, Audio, Video Settings ---")
    logger.info("5. Ollama model: %s", config.get("ollama_model", DEFAULT_MODEL))
    logger.info("6. Generate audio output: %s", config.get("generate_audio", True))
    logger.info("7. Generate video slides: %s", config.get("generate_video", False))
    logger.info("8. Selected voice for audio generation: %s", config.get("selected_voice", "gTTS"))
    logger.info(
        "9. macOS TTS reading speed (words per minute): %s",
        config.get("macos_reading_speed", 100),
    )
    logger.info("10. Audio tempo (default: %s)", config.get("tempo", 1.0))
    logger.info("11. Sync ratio for word slides: %s", config.get("sync_ratio", 0.9))

    logger.info("\n--- Sentence Parsing Settings ---")
    logger.info(
        "12. Sentences per output file: %s",
        config.get("sentences_per_output_file", 10),
    )
    logger.info(
        "13. Starting sentence (number or lookup word): %s",
        config.get("start_sentence", 1),
    )
    logger.info(
        "14. Ending sentence (absolute or offset): %s",
        config.get("end_sentence", f"Last sentence [{len(refined)}]"),
    )
    logger.info("15. Max words per sentence chunk: %s", config.get("max_words", 18))
    logger.info(
        "16. Percentile for computing suggested max words: %s",
        config.get("percentile", 96),
    )

    logger.info("\n--- Format Options ---")
    logger.info(
        "17. Audio output mode: %s (%s)",
        config.get("audio_mode", "1"),
        AUDIO_MODE_DESC.get(config.get("audio_mode", "1"), ""),
    )
    logger.info(
        "18. Written output mode: %s (%s)",
        config.get("written_mode", "4"),
        WRITTEN_MODE_DESC.get(config.get("written_mode", "4"), ""),
    )
    logger.info(
        "19. Extend split logic with comma and semicolon: %s",
        "Yes" if config.get("split_on_comma_semicolon", False) else "No",
    )
    logger.info(
        "20. Include transliteration for non-Latin alphabets: %s",
        config.get("include_transliteration", False),
    )
    logger.info(
        "21. Word highlighting for video slides: %s",
        "Yes" if config.get("word_highlighting", True) else "No",
    )
    logger.info("22. Debug mode: %s", config.get("debug", False))
    logger.info("23. HTML output: %s", config.get("output_html", True))
    logger.info("24. PDF output: %s", config.get("output_pdf", False))
    logger.info("25. Generate stitched full output file: %s", config.get("stitch_full", False))

    logger.info("\n--- Book Metadata ---")
    logger.info("26. Book Title: %s", config.get("book_title"))
    logger.info("27. Author: %s", config.get("book_author"))
    logger.info("28. Year: %s", config.get("book_year"))
    logger.info("29. Summary: %s", config.get("book_summary"))
    logger.info("30. Book Cover File: %s", config.get("book_cover_file", "None"))

    logger.info("\n--- Paths and Services ---")
    logger.info("31. Working directory: %s", config.get("working_dir"))
    logger.info("32. Output directory: %s", config.get("output_dir"))
    logger.info("33. Ebooks directory: %s", config.get("ebooks_dir"))
    logger.info("34. Temporary directory: %s", config.get("tmp_dir"))
    logger.info("35. FFmpeg path: %s", config.get("ffmpeg_path"))
    logger.info("36. Ollama API URL: %s", config.get("ollama_url"))


def _select_from_epub_directory(config: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    books_dir_path = (
        Path(cfg.BOOKS_DIR)
        if cfg.BOOKS_DIR
        else resolve_directory(config.get("ebooks_dir"), DEFAULT_BOOKS_RELATIVE)
    )
    epub_files = sorted([p.name for p in books_dir_path.glob("*.epub")])
    if epub_files:
        for idx, file_name in enumerate(epub_files, start=1):
            logger.info("%s. %s", idx, file_name)
    else:
        logger.info("No EPUB files found in %s. You can type a custom path.", books_dir_path)
    default_input = config.get("input_file", epub_files[0] if epub_files else "")
    default_display = (
        str(resolve_file_path(default_input, cfg.BOOKS_DIR)) if default_input else ""
    )
    prompt_default = default_display or default_input
    inp_val = input(
        f"Select an input file by number or enter a path (default: {prompt_default}): "
    ).strip()
    if inp_val.isdigit() and 0 < int(inp_val) <= len(epub_files):
        config["input_file"] = epub_files[int(inp_val) - 1]
    elif inp_val:
        config["input_file"] = inp_val
    else:
        config["input_file"] = default_input
    return config, True


def _default_base_output_file(config: Dict[str, Any]) -> str:
    if config.get("input_file"):
        base = os.path.splitext(os.path.basename(config["input_file"]))[0]
        target_lang = ", ".join(config.get("target_languages", ["Arabic"]))
        default_file = os.path.join(
            cfg.EBOOK_DIR,
            base,
            f"{target_lang}_{base}.html",
        )
    else:
        default_file = os.path.join(cfg.EBOOK_DIR, "output.html")
    return default_file


def edit_parameter(
    config: Dict[str, Any],
    selection: int,
    refined: Sequence[str],
    overrides: Dict[str, Any],
    debug_enabled: bool,
) -> Tuple[Dict[str, Any], bool]:
    """Handle a parameter edit request from the interactive menu."""
    refined_cache_stale = False

    if selection == 1:
        config, refined_cache_stale = _select_from_epub_directory(config)
    elif selection == 2:
        default_file = _default_base_output_file(config)
        inp_val = input(
            f"Enter base output file name (default: {default_file}): "
        ).strip()
        config["base_output_file"] = inp_val if inp_val else default_file
    elif selection == 3:
        logger.info("\nSelect input language:")
        print_languages_in_four_columns()
        default_in = config.get("input_language", "English")
        inp_val = input(
            f"Select input language by number (default: {default_in}): "
        ).strip()
        if inp_val.isdigit() and 0 < int(inp_val) <= len(TOP_LANGUAGES):
            config["input_language"] = TOP_LANGUAGES[int(inp_val) - 1]
        else:
            config["input_language"] = default_in
    elif selection == 4:
        logger.info(
            "\nSelect target languages (separate choices by comma, e.g. 1,4,7):"
        )
        print_languages_in_four_columns()
        default_targets = config.get("target_languages", ["Arabic"])
        inp_val = input(
            f"Select target languages by number (default: {', '.join(default_targets)}): "
        ).strip()
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
                check=False,
            )
            models = [line.strip() for line in result.stdout.splitlines()[1:] if line.strip()]
            for idx, model in enumerate(models, start=1):
                logger.info("%s. %s", idx, model)
            default_model = config.get("ollama_model", models[0].split()[0] if models else DEFAULT_MODEL)
            inp_val = input(
                f"Select a model by number (default: {default_model}): "
            ).strip()
            if inp_val.isdigit() and models:
                chosen = models[int(inp_val) - 1].split()[0]
                config["ollama_model"] = chosen
            else:
                config["ollama_model"] = default_model
        except Exception as exc:
            logger.error("Error listing models: %s", exc)
    elif selection == 6:
        default_audio = config.get("generate_audio", True)
        inp_val = input(
            f"Generate audio output files? (yes/no, default {'yes' if default_audio else 'no'}): "
        ).strip().lower()
        config["generate_audio"] = True if inp_val in ["", "yes", "y"] else False
    elif selection == 7:
        default_video = config.get("generate_video", False)
        inp_val = input(
            f"Generate video slide output? (yes/no, default {'yes' if default_video else 'no'}): "
        ).strip().lower()
        config["generate_video"] = True if inp_val in ["yes", "y"] else False
    elif selection == 8:
        default_voice = config.get("selected_voice", "gTTS")
        logger.info("\nSelect voice for audio generation:")
        logger.info("1. Use gTTS (online text-to-speech)")
        logger.info("2. Use macOS TTS voice (only Enhanced/Premium voices shown)")
        voice_choice = input("Enter 1 for gTTS or 2 for macOS voice (default: 1): ").strip()
        if voice_choice == "2":
            voices = get_macos_voices(debug_enabled=debug_enabled)
            if voices:
                logger.info("Available macOS voices (Enhanced/Premium):")
                for idx, voice in enumerate(voices, start=1):
                    logger.info("%s. %s", idx, voice)
                inp = input(
                    f"Select a macOS voice by number (default: {voices[0]}): "
                ).strip()
                if inp.isdigit() and 1 <= int(inp) <= len(voices):
                    voice_selected = voices[int(inp) - 1]
                else:
                    voice_selected = voices[0]
            else:
                logger.warning("No macOS voices found, defaulting to gTTS")
                voice_selected = "gTTS"
        else:
            voice_selected = default_voice
        config["selected_voice"] = voice_selected
    elif selection == 9:
        default_speed = config.get("macos_reading_speed", 100)
        inp_val = input(
            f"Enter macOS TTS reading speed (words per minute) (default {default_speed}): "
        ).strip()
        config["macos_reading_speed"] = int(inp_val) if inp_val.isdigit() else default_speed
    elif selection == 10:
        default_tempo = config.get("tempo", 1.0)
        inp_val = input(
            f"Enter audio tempo (e.g. 1 for normal, 1.5 for faster, 0.75 for slower) (default {default_tempo}): "
        ).strip()
        try:
            config["tempo"] = float(inp_val) if inp_val else default_tempo
        except Exception:
            config["tempo"] = default_tempo
    elif selection == 11:
        default_sync = config.get("sync_ratio", 0.9)
        inp_val = input(
            f"Enter sync ratio for word slides (default {default_sync}): "
        ).strip()
        try:
            config["sync_ratio"] = float(inp_val)
        except Exception:
            config["sync_ratio"] = default_sync
    elif selection == 12:
        default_sent = config.get("sentences_per_output_file", 10)
        inp_val = input(
            f"Enter number of sentences per output file (default {default_sent}): "
        ).strip()
        config["sentences_per_output_file"] = int(inp_val) if inp_val.isdigit() else default_sent
    elif selection == 13:
        default_start = config.get("start_sentence", 1)
        inp_val = input(
            f"Enter starting sentence (number or lookup word) (default: {default_start}): "
        ).strip()
        if inp_val:
            if inp_val.isdigit():
                config["start_sentence"] = int(inp_val)
                config["start_sentence_lookup"] = ""
            else:
                config["start_sentence_lookup"] = inp_val
                config["start_sentence"] = inp_val
        else:
            config["start_sentence"] = default_start
    elif selection == 14:
        total_sent = len(refined)
        default_end = config.get("end_sentence")
        inp_val = input(
            f"Enter ending sentence (absolute or offset, e.g. +100) (default: last sentence [{total_sent}]): "
        ).strip()
        if inp_val == "":
            config["end_sentence"] = total_sent
        elif inp_val[0] in ["+", "-"]:
            try:
                offset = int(inp_val)
                start_val = int(config.get("start_sentence", 1))
                config["end_sentence"] = start_val + offset
                logger.info("Ending sentence updated to %s", config["end_sentence"])
            except Exception:
                config["end_sentence"] = default_end
        elif inp_val.isdigit():
            config["end_sentence"] = int(inp_val)
        else:
            config["end_sentence"] = default_end
    elif selection == 15:
        default_max = config.get("max_words", DEFAULT_MAX)
        inp_val = input(
            f"Enter maximum words per sentence chunk (default {default_max}): "
        ).strip()
        if inp_val.isdigit():
            new_max = int(inp_val)
            config["max_words"] = new_max
            config["max_words_manual"] = True
            text = extract_text_from_epub(config["input_file"])
            refined_tmp = split_text_into_sentences(
                text,
                max_words=new_max,
                extend_split_with_comma_semicolon=config.get(
                    "split_on_comma_semicolon",
                    DEFAULT_EXTEND,
                ),
            )
            lengths = [len(sentence.split()) for sentence in refined_tmp]
            new_percentile = None
            for idx, length in enumerate(lengths):
                if length >= new_max:
                    new_percentile = int(((idx + 1) / len(lengths)) * 100)
                    break
            config["percentile"] = new_percentile if new_percentile is not None else 100
        else:
            config["max_words"] = default_max
    elif selection == 16:
        default_perc = config.get("percentile", 96)
        inp_val = input(
            f"Enter percentile for suggested max words (default {default_perc}): "
        ).strip()
        if inp_val.isdigit():
            perc = int(inp_val)
            if 1 <= perc <= 100:
                config["percentile"] = perc
            else:
                logger.warning("Invalid percentile, must be between 1 and 100. Keeping previous value.")
        else:
            config["percentile"] = default_perc
    elif selection == 17:
        default_am = config.get("audio_mode", "1")
        logger.info("\nChoose audio output mode:")
        for key, description in AUDIO_MODE_DESC.items():
            logger.info("%s: %s", key, description)
        inp_val = input(
            f"Select audio output mode (default {default_am}): "
        ).strip()
        config["audio_mode"] = inp_val if inp_val in AUDIO_MODE_DESC else default_am
    elif selection == 18:
        default_wm = config.get("written_mode", "4")
        logger.info("\nChoose written output mode:")
        for key, description in WRITTEN_MODE_DESC.items():
            logger.info("%s: %s", key, description)
        inp_val = input(
            f"Select written output mode (default {default_wm}): "
        ).strip()
        config["written_mode"] = inp_val if inp_val in WRITTEN_MODE_DESC else default_wm
    elif selection == 19:
        default_split = config.get("split_on_comma_semicolon", False)
        inp_val = input(
            f"Extend split logic with comma and semicolon? (yes/no, default {'yes' if default_split else 'no'}): "
        ).strip().lower()
        config["split_on_comma_semicolon"] = True if inp_val in ["yes", "y"] else default_split
    elif selection == 20:
        default_translit = config.get("include_transliteration", False)
        inp_val = input(
            f"Include transliteration for non-Latin alphabets? (yes/no, default {'yes' if default_translit else 'no'}): "
        ).strip().lower()
        config["include_transliteration"] = True if inp_val in ["yes", "y"] else False
    elif selection == 21:
        default_highlight = config.get("word_highlighting", True)
        inp_val = input(
            f"Enable word highlighting for video slides? (yes/no, default {'yes' if default_highlight else 'no'}): "
        ).strip().lower()
        config["word_highlighting"] = True if inp_val in ["", "yes", "y"] else False
    elif selection == 22:
        default_debug = config.get("debug", False)
        inp_val = input(
            f"Enable debug mode? (yes/no, default {'yes' if default_debug else 'no'}): "
        ).strip().lower()
        config["debug"] = True if inp_val in ["yes", "y"] else False
        configure_logging_level(config["debug"])
        translation_engine.set_debug(config["debug"])
    elif selection == 23:
        default_html = config.get("output_html", True)
        inp_val = input(
            f"Generate HTML output? (yes/no, default {'yes' if default_html else 'no'}): "
        ).strip().lower()
        config["output_html"] = True if inp_val in ["", "yes", "y"] else False
    elif selection == 24:
        default_pdf = config.get("output_pdf", False)
        inp_val = input(
            f"Generate PDF output? (yes/no, default {'yes' if default_pdf else 'no'}): "
        ).strip().lower()
        config["output_pdf"] = True if inp_val in ["yes", "y"] else False
    elif selection == 25:
        default_stitch = config.get("stitch_full", False)
        inp_val = input(
            f"Generate stitched full output file? (yes/no, default {'yes' if default_stitch else 'no'}): "
        ).strip().lower()
        config["stitch_full"] = True if inp_val in ["yes", "y"] else False
    elif selection == 26:
        default_title = config.get("book_title", "")
        inp_val = input(
            f"Enter book title (default: {default_title}): "
        ).strip()
        if inp_val:
            config["book_title"] = inp_val
    elif selection == 27:
        default_author = config.get("book_author", "")
        inp_val = input(
            f"Enter author name (default: {default_author}): "
        ).strip()
        if inp_val:
            config["book_author"] = inp_val
    elif selection == 28:
        default_year = config.get("book_year", "")
        inp_val = input(
            f"Enter publication year (default: {default_year}): "
        ).strip()
        if inp_val:
            config["book_year"] = inp_val
    elif selection == 29:
        default_summary = config.get("book_summary", "")
        inp_val = input(
            "Enter book summary (press Enter to keep current): "
        ).strip()
        if inp_val:
            config["book_summary"] = inp_val
    elif selection == 30:
        current_cover = config.get("book_cover_file") or "None"
        inp_val = input(
            f"Enter book cover file path (default: {current_cover}): "
        ).strip()
        if inp_val:
            config["book_cover_file"] = inp_val
        debug_enabled = config.get("debug", False)
        config = update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=debug_enabled,
        )
    elif selection == 31:
        current = config.get("working_dir")
        inp_val = input(
            f"Enter working directory (default: {current}): "
        ).strip()
        if inp_val:
            config["working_dir"] = inp_val
        initialize_environment(config, overrides)
        config = update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=debug_enabled,
        )
        refined_cache_stale = True
    elif selection == 32:
        current = config.get("output_dir")
        inp_val = input(
            f"Enter output directory (default: {current}): "
        ).strip()
        if inp_val:
            config["output_dir"] = inp_val
        initialize_environment(config, overrides)
        refined_cache_stale = True
    elif selection == 33:
        current = config.get("ebooks_dir")
        inp_val = input(
            f"Enter ebooks directory (default: {current}): "
        ).strip()
        if inp_val:
            config["ebooks_dir"] = inp_val
        initialize_environment(config, overrides)
        config = update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=debug_enabled,
        )
        refined_cache_stale = True
    elif selection == 34:
        current = config.get("tmp_dir")
        inp_val = input(
            f"Enter temporary directory (default: {current}): "
        ).strip()
        if inp_val:
            config["tmp_dir"] = inp_val
        initialize_environment(config, overrides)
    elif selection == 35:
        current = config.get("ffmpeg_path")
        inp_val = input(
            f"Enter FFmpeg executable path (default: {current}): "
        ).strip()
        if inp_val:
            config["ffmpeg_path"] = inp_val
        initialize_environment(config, overrides)
    elif selection == 36:
        current = config.get("ollama_url")
        inp_val = input(
            f"Enter Ollama API URL (default: {current}): "
        ).strip()
        if inp_val:
            config["ollama_url"] = inp_val
        initialize_environment(config, overrides)
    else:
        logger.warning("Invalid parameter number. Please try again.")

    return config, refined_cache_stale


def confirm_settings(
    config: Dict[str, Any],
    resolved_input: Optional[Path],
    entry_script_name: str,
) -> Tuple[
    Dict[str, Any],
    Tuple[
        str,
        str,
        str,
        List[str],
        int,
        int,
        Optional[int],
        bool,
        bool,
        str,
        str,
        str,
        bool,
        bool,
        bool,
        bool,
        float,
        Dict[str, Any],
    ],
]:
    """Finalize the interactive session and prepare pipeline arguments."""
    resolved_input_str = str(resolved_input) if resolved_input else config.get("input_file", "")
    input_arg = f'"{resolved_input_str}"'
    target_languages = config.get("target_languages", ["Arabic"])
    target_arg = f'"{",".join(target_languages)}"'
    cmd_parts = [
        os.path.basename(sys.executable) if sys.executable else "python3",
        entry_script_name,
        input_arg,
        f'"{config.get("input_language", "English")}"',
        target_arg,
        str(config.get("sentences_per_output_file", 10)),
        f'"{config.get("base_output_file", "")}"',
        str(config.get("start_sentence", 1)),
    ]
    if config.get("end_sentence") is not None:
        cmd_parts.append(str(config.get("end_sentence")))
    if config.get("debug"):
        cmd_parts.append("--debug")
    logger.info("\nTo run non-interactively with these settings, use the following command:")
    logger.info("%s", " ".join(cmd_parts))

    book_metadata = {
        "book_title": config.get("book_title"),
        "book_author": config.get("book_author"),
        "book_year": config.get("book_year"),
        "book_summary": config.get("book_summary"),
        "book_cover_file": config.get("book_cover_file"),
    }

    pipeline_args = (
        resolved_input_str,
        config.get("base_output_file", ""),
        config.get("input_language", "English"),
        target_languages,
        config.get("sentences_per_output_file", 10),
        config.get("start_sentence", 1),
        config.get("end_sentence"),
        config.get("stitch_full", False),
        config.get("generate_audio", True),
        config.get("audio_mode", "1"),
        config.get("written_mode", "4"),
        config.get("selected_voice", "gTTS"),
        config.get("output_html", True),
        config.get("output_pdf", False),
        config.get("generate_video", False),
        config.get("include_transliteration", False),
        config.get("tempo", 1.0),
        book_metadata,
    )
    return config, pipeline_args


def run_interactive_menu(
    overrides: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
    entry_script_name: str = "main.py",
) -> Tuple[Dict[str, Any], Tuple[Any, ...]]:
    """Run the interactive configuration menu and return the final configuration."""
    overrides = overrides or {}
    if config_path:
        config_file_path = Path(config_path).expanduser()
        if not config_file_path.is_absolute():
            config_file_path = (Path.cwd() / config_file_path).resolve()
    else:
        config_file_path = DEFAULT_LOCAL_CONFIG_PATH

    config = load_configuration(config_file_path, verbose=True)
    configure_logging_level(config.get("debug", False))

    if "start_sentence" in config and not str(config["start_sentence"]).isdigit():
        config["start_sentence_lookup"] = config["start_sentence"]

    initialize_environment(config, overrides)
    config = update_book_cover_file_in_config(
        config,
        config.get("ebooks_dir"),
        debug_enabled=config.get("debug", False),
    )

    refined_cache_stale = True
    refined: List[str] = []

    from . import ebook_tools as pipeline  # Local import to avoid circular dependency

    while True:
        resolved_input_path = resolve_file_path(config.get("input_file"), cfg.BOOKS_DIR)

        if config.get("input_file"):
            refined, refreshed = pipeline.get_refined_sentences(
                config["input_file"],
                force_refresh=refined_cache_stale,
                metadata={"mode": "interactive"},
            )
            if refreshed:
                logger.info(
                    "Refined sentence list written to: %s",
                    pipeline.refined_list_output_path(config["input_file"]),
                )
            refined_cache_stale = False
        else:
            refined = []

        config = update_sentence_config(config, refined)

        display_menu(config, refined, resolved_input_path)

        inp_choice = input(
            "\nEnter a parameter number to change (or press Enter to confirm): "
        ).strip()
        if inp_choice == "":
            break
        if not inp_choice.isdigit():
            logger.warning("Invalid input. Please enter a number or press Enter.")
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
                json.dump(strip_derived_config(config), cfg_file, indent=4)
            logger.info("Configuration saved to %s", config_file_path)
        except Exception as exc:
            logger.error("Error saving configuration: %s", exc)

    resolved_input_path = resolve_file_path(config.get("input_file"), cfg.BOOKS_DIR)
    config, pipeline_args = confirm_settings(config, resolved_input_path, entry_script_name)

    translation_engine.set_model(config.get("ollama_model", DEFAULT_MODEL))
    translation_engine.set_debug(config.get("debug", False))
    configure_logging_level(config.get("debug", False))

    return config, pipeline_args
