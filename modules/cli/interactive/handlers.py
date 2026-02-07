"""Configuration editing handlers for the interactive CLI."""

from __future__ import annotations

import subprocess
from typing import Any, Callable, Dict, Sequence, Tuple

from ... import config_manager as cfg
from ... import metadata_manager
from ... import llm_client_manager
from ...shared import assets
from .. import context
from .common import (
    AUDIO_MODE_DESC,
    DEFAULT_MODEL,
    TOP_LANGUAGES,
    WRITTEN_MODE_DESC,
    console_info,
    console_warning,
    configure_logging_level,
    default_base_output_file,
    print_languages_in_four_columns,
    prompt_user,
    select_from_epub_directory,
)

EditHandler = Callable[[Dict[str, Any], Sequence[str], Dict[str, Any], bool], Tuple[Dict[str, Any], bool]]


def _handle_input_file(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    previous_input = config.get("input_file")
    previous_default_output = default_base_output_file(config) if previous_input else None
    previous_base_output = config.get("base_output_file")

    config, refined_cache_stale = select_from_epub_directory(config)
    active_context = context.get_active_context(None)
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

    if resolved_input_path and config.get("auto_metadata", True) and resolved_input_path.exists():
        metadata_manager.populate_config_metadata(
            config,
            str(resolved_input_path),
            force=True,
        )

    if config.get("input_file") != previous_input:
        new_default_output = default_base_output_file(config)
        if not previous_base_output or previous_base_output == previous_default_output:
            config["base_output_file"] = new_default_output
    return config, refined_cache_stale


def _handle_base_output(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_file = default_base_output_file(config)
    inp_val = prompt_user(f"Enter base output file name (default: {default_file}): ")
    config["base_output_file"] = inp_val if inp_val else default_file
    return config, False


def _handle_input_language(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    console_info("\nSelect input language:")
    print_languages_in_four_columns()
    default_in = config.get("input_language", context.default_language())
    inp_val = prompt_user(f"Select input language by number (default: {default_in}): ")
    if inp_val.isdigit() and 0 < int(inp_val) <= len(TOP_LANGUAGES):
        config["input_language"] = TOP_LANGUAGES[int(inp_val) - 1]
    else:
        config["input_language"] = default_in
    return config, False


def _handle_target_languages(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    console_info("\nSelect target languages (separate choices by comma, e.g. 1,4,7):")
    print_languages_in_four_columns()
    default_targets = config.get("target_languages", context.default_target_languages())
    prompt = f"Select target languages by number (default: {', '.join(default_targets)}): "
    inp_val = prompt_user(prompt)
    if inp_val:
        choices = [int(x) for x in inp_val.split(",") if x.strip().isdigit()]
        selected = [TOP_LANGUAGES[x - 1] for x in choices if 0 < x <= len(TOP_LANGUAGES)]
        config["target_languages"] = selected or default_targets
    else:
        config["target_languages"] = default_targets
    return config, False


def _handle_ollama_model(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
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
        return config, False

    console_info("Available models:")
    for idx, model in enumerate(models, start=1):
        console_info("%s. %s", idx, model)
    default_model = config.get("ollama_model", DEFAULT_MODEL)
    inp_val = prompt_user(f"Select model by number (default: {default_model}): ")
    if inp_val.isdigit() and 0 < int(inp_val) <= len(models):
        config["ollama_model"] = models[int(inp_val) - 1]
    else:
        config["ollama_model"] = default_model
    return config, False


def _prompt_boolean(prompt_text: str, default: bool, accept_blank: bool) -> bool:
    response = prompt_user(prompt_text).lower()
    if accept_blank and response == "":
        return default
    return response in {"yes", "y"}


def _handle_generate_audio(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_audio = config.get("generate_audio", True)
    prompt = f"Generate audio output? (yes/no, default {'yes' if default_audio else 'no'}): "
    config["generate_audio"] = _prompt_boolean(prompt, default_audio, accept_blank=True)
    return config, False


def _handle_selected_voice(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    voices = context.get_macos_voices(debug_enabled=debug_enabled)
    voices.extend(["gTTS", "macOS-auto", "macOS-auto-female", "macOS-auto-male"])
    for idx, voice in enumerate(voices, start=1):
        console_info("%s. %s", idx, voice)
    default_voice = config.get("selected_voice", "gTTS")
    inp_val = prompt_user(f"Select voice by number (default: {default_voice}): ")
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
    return config, False


def _handle_macos_speed(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_speed = config.get("macos_reading_speed", 100)
    inp_val = prompt_user(
        f"Enter macOS TTS reading speed (words per minute, default {default_speed}): "
    )
    if inp_val.isdigit():
        config["macos_reading_speed"] = int(inp_val)
    else:
        config["macos_reading_speed"] = default_speed
    return config, False


def _handle_tempo(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_tempo = config.get("tempo", 1.0)
    inp_val = prompt_user(f"Enter audio tempo multiplier (default {default_tempo}): ")
    try:
        config["tempo"] = float(inp_val) if inp_val else default_tempo
    except ValueError:
        config["tempo"] = default_tempo
    return config, False


def _handle_sync_ratio(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_sync = config.get("sync_ratio", 0.9)
    inp_val = prompt_user(f"Enter sync ratio for word slides (default {default_sync}): ")
    try:
        config["sync_ratio"] = float(inp_val) if inp_val else default_sync
    except ValueError:
        config["sync_ratio"] = default_sync
    return config, False


def _handle_thread_count(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_threads = config.get("thread_count", cfg.DEFAULT_THREADS)
    inp_val = prompt_user(f"Enter worker thread count (default {default_threads}): ")
    if inp_val.isdigit():
        config["thread_count"] = max(1, min(10, int(inp_val)))
    else:
        config["thread_count"] = default_threads
    return config, False


def _handle_sentences_per_file(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_sentences = config.get("sentences_per_output_file", 1)
    inp_val = prompt_user(f"Enter sentences per output file (default {default_sentences}): ")
    if inp_val.isdigit():
        config["sentences_per_output_file"] = int(inp_val)
    else:
        config["sentences_per_output_file"] = default_sentences
    return config, False


def _handle_start_sentence(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_start = config.get("start_sentence", 1)
    inp_val = prompt_user(
        f"Enter starting sentence number or lookup term (default {default_start}): "
    )
    if inp_val.isdigit():
        config["start_sentence"] = int(inp_val)
        config.pop("start_sentence_lookup", None)
    elif inp_val:
        config["start_sentence_lookup"] = inp_val
    else:
        config["start_sentence"] = default_start
    return config, False


def _handle_end_sentence(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_end = config.get("end_sentence")
    inp_val = prompt_user("Enter ending sentence (number, +/- offset, or blank for none): ")
    if not inp_val:
        config["end_sentence"] = default_end
    elif inp_val[0] in {"+", "-"}:
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
    return config, False


def _handle_max_words(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_max = config.get("max_words", context.DEFAULT_MAX)
    inp_val = prompt_user(
        f"Enter maximum words per sentence chunk (default {default_max}): "
    )
    if inp_val.isdigit():
        config["max_words"] = int(inp_val)
        config["max_words_manual"] = True
        context.recalculate_percentile(config)
    else:
        config["max_words"] = default_max
    return config, False


def _handle_percentile(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_percentile = config.get("percentile", assets.DEFAULT_ASSET_VALUES.get("percentile", 96))
    inp_val = prompt_user(
        f"Enter percentile for suggested max words (default {default_percentile}): "
    )
    if inp_val.isdigit():
        perc = int(inp_val)
        if 1 <= perc <= 100:
            config["percentile"] = perc
        else:
            console_warning(
                "Invalid percentile, must be between 1 and 100. Keeping previous value."
            )
    else:
        config["percentile"] = default_percentile
    return config, False


def _handle_audio_mode(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_audio_mode = config.get("audio_mode", assets.DEFAULT_ASSET_VALUES.get("audio_mode", "1"))
    console_info("\nChoose audio output mode:")
    for key, description in AUDIO_MODE_DESC.items():
        console_info("%s: %s", key, description)
    inp_val = prompt_user(f"Select audio output mode (default {default_audio_mode}): ")
    config["audio_mode"] = inp_val if inp_val in AUDIO_MODE_DESC else default_audio_mode
    return config, False


def _handle_written_mode(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_written_mode = config.get("written_mode", assets.DEFAULT_ASSET_VALUES.get("written_mode", "4"))
    console_info("\nChoose written output mode:")
    for key, description in WRITTEN_MODE_DESC.items():
        console_info("%s: %s", key, description)
    inp_val = prompt_user(f"Select written output mode (default {default_written_mode}): ")
    config["written_mode"] = inp_val if inp_val in WRITTEN_MODE_DESC else default_written_mode
    return config, False


def _handle_split_on_punctuation(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_split = config.get("split_on_comma_semicolon", False)
    prompt = (
        f"Extend split logic with comma and semicolon? (yes/no, default {'yes' if default_split else 'no'}): "
    )
    response = prompt_user(prompt).lower()
    config["split_on_comma_semicolon"] = True if response in {"yes", "y"} else default_split
    return config, False


def _handle_transliteration(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_value = config.get("include_transliteration", True)
    prompt = (
        f"Include transliteration for non-Latin alphabets? (yes/no, default {'yes' if default_value else 'no'}): "
    )
    response = prompt_user(prompt).lower()
    config["include_transliteration"] = True if response not in {"no", "n"} else False
    return config, False


def _handle_word_highlighting(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_value = config.get("word_highlighting", True)
    prompt = f"Enable word highlighting for video slides? (yes/no, default {'yes' if default_value else 'no'}): "
    response = prompt_user(prompt).lower()
    config["word_highlighting"] = True if response in {"", "yes", "y"} else False
    return config, False


def _handle_highlight_mode(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current_default = bool(config.get("char_weighted_highlighting_default"))
    current_punct = bool(config.get("char_weighted_punctuation_boost"))
    if current_default and current_punct:
        current_label = "punctuation-weighted"
    elif current_default:
        current_label = "char-weighted"
    else:
        current_label = "uniform"
    console_info(
        "\nSelect highlight inference mode:\n"
        "1. Uniform (legacy inference)\n"
        "2. Char-weighted\n"
        "3. Punctuation-weighted char timing"
    )
    inp_val = prompt_user(f"Enter choice (1-3, current {current_label}): ").strip()
    if inp_val == "2":
        config["char_weighted_highlighting_default"] = True
        config["char_weighted_punctuation_boost"] = False
    elif inp_val == "3":
        config["char_weighted_highlighting_default"] = True
        config["char_weighted_punctuation_boost"] = True
    elif inp_val == "1":
        config["char_weighted_highlighting_default"] = False
        config["char_weighted_punctuation_boost"] = False
    return config, False


def _handle_debug(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_debug = config.get("debug", False)
    prompt = f"Enable debug mode? (yes/no, default {'yes' if default_debug else 'no'}): "
    config["debug"] = _prompt_boolean(prompt, default_debug, accept_blank=False)
    configure_logging_level(config["debug"])
    llm_client_manager.configure_default_client(debug=config["debug"])
    return config, False


def _handle_output_html(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_html = config.get("output_html", True)
    prompt = f"Generate HTML output? (yes/no, default {'yes' if default_html else 'no'}): "
    config["output_html"] = _prompt_boolean(prompt, default_html, accept_blank=True)
    return config, False


def _handle_output_pdf(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_pdf = config.get("output_pdf", False)
    prompt = f"Generate PDF output? (yes/no, default {'yes' if default_pdf else 'no'}): "
    config["output_pdf"] = _prompt_boolean(prompt, default_pdf, accept_blank=False)
    return config, False


def _handle_stitch_full(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_stitch = config.get("stitch_full", False)
    prompt = f"Generate stitched full output file? (yes/no, default {'yes' if default_stitch else 'no'}): "
    config["stitch_full"] = _prompt_boolean(prompt, default_stitch, accept_blank=False)
    return config, False


def _handle_book_title(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_title = config.get("book_title", "")
    inp_val = prompt_user(f"Enter book title (default: {default_title}): ")
    if inp_val:
        config["book_title"] = inp_val
    return config, False


def _handle_book_author(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_author = config.get("book_author", "")
    inp_val = prompt_user(f"Enter author name (default: {default_author}): ")
    if inp_val:
        config["book_author"] = inp_val
    return config, False


def _handle_book_year(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    default_year = config.get("book_year", "")
    inp_val = prompt_user(f"Enter publication year (default: {default_year}): ")
    if inp_val:
        config["book_year"] = inp_val
    return config, False


def _handle_book_summary(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    inp_val = prompt_user("Enter book summary (press Enter to keep current): ")
    if inp_val:
        config["book_summary"] = inp_val
    return config, False


def _handle_book_cover(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current_cover = config.get("book_cover_file") or "None"
    inp_val = prompt_user(f"Enter book cover file path (default: {current_cover}): ")
    if inp_val:
        config["book_cover_file"] = inp_val
    config = context.update_book_cover_file_in_config(
        config,
        config.get("ebooks_dir"),
        debug_enabled=debug_enabled,
        context=context.get_active_context(None),
    )
    return config, False


def _handle_working_dir(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("working_dir")
    inp_val = prompt_user(f"Enter working directory (default: {current}): ")
    if inp_val:
        config["working_dir"] = inp_val
    active_context = context.refresh_runtime_context(config, overrides)
    config = context.update_book_cover_file_in_config(
        config,
        config.get("ebooks_dir"),
        debug_enabled=debug_enabled,
        context=active_context,
    )
    return config, True


def _handle_output_dir(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("output_dir")
    inp_val = prompt_user(f"Enter output directory (default: {current}): ")
    if inp_val:
        config["output_dir"] = inp_val
    context.refresh_runtime_context(config, overrides)
    return config, True


def _handle_ebooks_dir(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("ebooks_dir")
    inp_val = prompt_user(f"Enter ebooks directory (default: {current}): ")
    if inp_val:
        config["ebooks_dir"] = inp_val
    active_context = context.refresh_runtime_context(config, overrides)
    config = context.update_book_cover_file_in_config(
        config,
        config.get("ebooks_dir"),
        debug_enabled=debug_enabled,
        context=active_context,
    )
    return config, True


def _handle_tmp_dir(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("tmp_dir")
    inp_val = prompt_user(f"Enter temporary directory (default: {current}): ")
    if inp_val:
        config["tmp_dir"] = inp_val
    context.refresh_runtime_context(config, overrides)
    return config, False


def _handle_ffmpeg_path(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("ffmpeg_path")
    inp_val = prompt_user(f"Enter FFmpeg executable path (default: {current}): ")
    if inp_val:
        config["ffmpeg_path"] = inp_val
    context.refresh_runtime_context(config, overrides)
    return config, False


def _handle_llm_source(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("llm_source", cfg.DEFAULT_LLM_SOURCE)
    inp_val = prompt_user(
        f"Select LLM source (local/cloud/lmstudio) (current: {current}): "
    ).strip().lower()
    if inp_val:
        if inp_val in cfg.VALID_LLM_SOURCES:
            config["llm_source"] = inp_val
            context.refresh_runtime_context(config, overrides)
        else:
            console_warning("Invalid LLM source. Please enter 'local', 'cloud', or 'lmstudio'.")
    return config, False


def _handle_ollama_url(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("ollama_url")
    inp_val = prompt_user(f"Enter Ollama API URL (default: {current}): ")
    if inp_val:
        config["ollama_url"] = inp_val
    context.refresh_runtime_context(config, overrides)
    return config, False


def _handle_ollama_local_url(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("ollama_local_url", cfg.DEFAULT_OLLAMA_URL)
    inp_val = prompt_user(f"Enter local Ollama URL (default: {current}): ")
    if inp_val:
        config["ollama_local_url"] = inp_val
    context.refresh_runtime_context(config, overrides)
    return config, False


def _handle_ollama_cloud_url(
    config: Dict[str, Any], refined: Sequence[str], overrides: Dict[str, Any], debug_enabled: bool
) -> Tuple[Dict[str, Any], bool]:
    current = config.get("ollama_cloud_url", cfg.DEFAULT_OLLAMA_CLOUD_URL)
    inp_val = prompt_user(f"Enter Ollama Cloud URL (default: {current}): ")
    if inp_val:
        config["ollama_cloud_url"] = inp_val
    context.refresh_runtime_context(config, overrides)
    return config, False


_HANDLERS: Dict[int, EditHandler] = {
    1: _handle_input_file,
    2: _handle_base_output,
    3: _handle_input_language,
    4: _handle_target_languages,
    5: _handle_ollama_model,
    6: _handle_generate_audio,
    7: _handle_selected_voice,
    8: _handle_macos_speed,
    9: _handle_tempo,
    10: _handle_sync_ratio,
    11: _handle_thread_count,
    12: _handle_sentences_per_file,
    13: _handle_start_sentence,
    14: _handle_end_sentence,
    15: _handle_max_words,
    16: _handle_percentile,
    17: _handle_audio_mode,
    18: _handle_written_mode,
    19: _handle_split_on_punctuation,
    20: _handle_transliteration,
    21: _handle_word_highlighting,
    22: _handle_highlight_mode,
    23: _handle_debug,
    24: _handle_output_html,
    25: _handle_output_pdf,
    26: _handle_stitch_full,
    27: _handle_book_title,
    28: _handle_book_author,
    29: _handle_book_year,
    30: _handle_book_summary,
    31: _handle_book_cover,
    32: _handle_working_dir,
    33: _handle_output_dir,
    34: _handle_ebooks_dir,
    35: _handle_tmp_dir,
    36: _handle_ffmpeg_path,
    37: _handle_llm_source,
    38: _handle_ollama_url,
    39: _handle_ollama_local_url,
    40: _handle_ollama_cloud_url,
}


def edit_parameter(
    config: Dict[str, Any],
    selection: int,
    refined: Sequence[str],
    overrides: Dict[str, Any],
    debug_enabled: bool,
) -> Tuple[Dict[str, Any], bool]:
    """Handle a parameter edit request from the interactive menu."""

    handler = _HANDLERS.get(selection)
    if handler is None:
        console_warning("Invalid parameter number. Please try again.")
        return config, False
    return handler(config, refined, overrides, debug_enabled)
