"""Interactive menu runner for ebook-tools."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ... import config_manager as cfg
from ... import metadata_manager
from ...core import ingestion
from ...core.config import build_pipeline_config
from ...services.pipeline_service import PipelineInput
from ...services.pipeline_types import PipelineMetadata
from ...shared import assets
from .. import context
from .common import (
    MenuExit,
    console_error,
    console_info,
    console_warning,
    configure_logging_level,
    prompt_user,
)
from .display import display_menu
from .handlers import edit_parameter


def _resolved_input_display(resolved_input: Optional[Path], config: Dict[str, Any]) -> str:
    if resolved_input:
        return str(resolved_input)
    return config.get("input_file", "")


def confirm_settings(
    config: Dict[str, Any],
    resolved_input: Optional[Path],
    entry_script_name: str,
) -> Tuple[Dict[str, Any], PipelineInput]:
    """Finalize the interactive session and prepare pipeline arguments."""

    resolved_input_str = _resolved_input_display(resolved_input, config)
    input_arg = f'"{resolved_input_str}"'
    target_languages = config.get("target_languages", context.default_target_languages())
    target_arg = f'"{",".join(target_languages)}"'
    cmd_parts = [
        os.path.basename(sys.executable) if sys.executable else "python3",
        entry_script_name,
        input_arg,
        f'"{config.get("input_language", context.default_language())}"',
        target_arg,
        str(config.get("sentences_per_output_file", 1)),
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
        sentences_per_output_file=config.get("sentences_per_output_file", 1),
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
        include_transliteration=config.get("include_transliteration", True),
        tempo=config.get("tempo", 1.0),
        book_metadata=PipelineMetadata.from_mapping(book_metadata),
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

            inp_choice_raw = prompt_user(
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
