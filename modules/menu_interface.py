#!/usr/bin/env python3
"""Compatibility shim for the legacy menu interface.

Historically this module mixed argument parsing, interactive prompts, runtime
context management, and pipeline orchestration.  The refactor in
:mod:`modules.cli` decomposes those responsibilities into dedicated modules:

* :mod:`modules.cli.args` – builds both the modern sub-command parser and the
  legacy positional parser used by :func:`parse_arguments`.
* :mod:`modules.cli.context` – owns runtime context refresh logic and the
  implicit configuration flow that updates derived directories after a prompt
  changes them.
* :mod:`modules.cli.interactive` – contains the interactive prompt loop and
  formatting helpers.
* :mod:`modules.cli.pipeline_runner` – bridges CLI configuration with the
  ingestion pipeline for both interactive and non-interactive execution.

The shim keeps backwards compatibility for imports while documenting the
implicit flow where directory overrides trigger
:func:`modules.cli.context.refresh_runtime_context` so that subsequent pipeline
runs see the updated configuration.
"""

from __future__ import annotations

from .cli.args import parse_legacy_args as parse_arguments
from .cli.context import (
    DEFAULT_EXTEND,
    DEFAULT_MAX,
    active_books_dir,
    active_output_dir,
    default_language,
    default_target_languages,
    get_active_context,
    get_macos_voices,
    recalculate_percentile,
    refresh_runtime_context,
    update_book_cover_file_in_config,
    update_sentence_config,
)
from .cli.interactive import (
    AUDIO_MODE_DESC,
    MenuExit,
    TOP_LANGUAGES,
    confirm_settings,
    display_menu,
    edit_parameter,
    print_languages_in_four_columns,
    run_interactive_menu,
)

__all__ = [
    "AUDIO_MODE_DESC",
    "DEFAULT_EXTEND",
    "DEFAULT_MAX",
    "MenuExit",
    "TOP_LANGUAGES",
    "active_books_dir",
    "active_output_dir",
    "confirm_settings",
    "default_language",
    "default_target_languages",
    "display_menu",
    "edit_parameter",
    "get_active_context",
    "get_macos_voices",
    "parse_arguments",
    "print_languages_in_four_columns",
    "recalculate_percentile",
    "refresh_runtime_context",
    "run_interactive_menu",
    "update_book_cover_file_in_config",
    "update_sentence_config",
]
