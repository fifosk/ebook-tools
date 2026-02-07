"""Menu rendering helpers for the interactive CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from ... import config_manager as cfg
from ...audio.backends import get_default_backend_name
from ...shared import assets
from .. import context
from .common import (
    AUDIO_MODE_DESC,
    DEFAULT_MODEL,
    WRITTEN_MODE_DESC,
    console_info,
    format_selected_voice,
)


def _input_display(config: Dict[str, Any], resolved_input: Optional[Path]) -> str:
    if resolved_input:
        return str(resolved_input)
    return config.get("input_file", "")


def _target_languages_display(config: Dict[str, Any]) -> str:
    return ", ".join(config.get("target_languages", context.default_target_languages()))


def display_menu(config: Dict[str, Any], refined: Sequence[str], resolved_input: Optional[Path]) -> None:
    """Emit the interactive configuration summary for the user."""

    input_display = _input_display(config, resolved_input)
    console_info("\n--- File / Language Settings ---")
    console_info("1. Input EPUB file: %s", input_display)
    console_info("2. Base output file: %s", config.get("base_output_file", ""))
    console_info("3. Input language: %s", config.get("input_language", context.default_language()))
    console_info("4. Target languages: %s", _target_languages_display(config))

    console_info("\n--- LLM & Audio Settings ---")
    console_info("5. Ollama model: %s", config.get("ollama_model", DEFAULT_MODEL))
    console_info("6. Generate audio output: %s", config.get("generate_audio", True))
    console_info(
        "7. Selected voice for audio generation: %s (backend: %s)",
        format_selected_voice(config.get("selected_voice", "gTTS")),
        config.get("tts_backend", get_default_backend_name()),
    )
    console_info(
        "   TTS executable override: %s",
        config.get("tts_executable_path")
        or config.get("say_path")
        or "None",
    )
    console_info(
        "8. macOS TTS reading speed (words per minute): %s",
        config.get("macos_reading_speed", 100),
    )
    console_info("9. Audio tempo (default: %s)", config.get("tempo", 1.0))
    console_info("10. Sync ratio for word slides: %s", config.get("sync_ratio", 0.9))
    console_info(
        "11. Worker thread count (1-10): %s",
        config.get("thread_count", cfg.DEFAULT_THREADS),
    )

    console_info("\n--- Sentence Parsing Settings ---")
    console_info(
        "12. Sentences per output file: %s",
        config.get("sentences_per_output_file", 1),
    )
    console_info(
        "13. Starting sentence (number or lookup word): %s",
        config.get("start_sentence", 1),
    )
    console_info(
        "14. Ending sentence (absolute or offset): %s",
        config.get("end_sentence", f"Last sentence [{len(refined)}]"),
    )
    console_info("15. Max words per sentence chunk: %s", config.get("max_words", context.DEFAULT_MAX))
    console_info(
        "16. Percentile for computing suggested max words: %s",
        config.get("percentile", assets.DEFAULT_ASSET_VALUES.get("percentile", 96)),
    )

    console_info("\n--- Format Options ---")
    console_info(
        "17. Audio output mode: %s (%s)",
        config.get("audio_mode", assets.DEFAULT_ASSET_VALUES.get("audio_mode", "1")),
        AUDIO_MODE_DESC.get(config.get("audio_mode", "1"), ""),
    )
    console_info(
        "18. Written output mode: %s (%s)",
        config.get("written_mode", assets.DEFAULT_ASSET_VALUES.get("written_mode", "4")),
        WRITTEN_MODE_DESC.get(config.get("written_mode", "4"), ""),
    )
    console_info(
        "19. Extend split logic with comma and semicolon: %s",
        "Yes" if config.get("split_on_comma_semicolon", False) else "No",
    )
    console_info(
        "20. Include transliteration for non-Latin alphabets: %s",
        config.get("include_transliteration", True),
    )
    console_info(
        "21. Word highlighting for video slides: %s",
        "Yes" if config.get("word_highlighting", True) else "No",
    )
    highlight_mode_label = "Uniform inference"
    if config.get("char_weighted_highlighting_default"):
        highlight_mode_label = (
            "Punctuation-weighted char timings"
            if config.get("char_weighted_punctuation_boost")
            else "Char-weighted timings"
        )
    console_info("22. Highlight inference mode: %s", highlight_mode_label)
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
        "\nPress Enter to confirm settings, choose a number to edit, or type 'q' to quit the menu.")
