"""Helpers that bridge CLI configuration with the ingestion pipeline."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import argparse

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import metadata_manager
from ..core import ingestion
from ..core.config import build_pipeline_config
from ..epub_parser import DEFAULT_MAX_WORDS
from ..progress_tracker import ProgressTracker
from ..services.pipeline_service import (
    PipelineInput,
    PipelineRequest,
    PipelineResponse,
    run_pipeline as run_pipeline_service,
)
from ..shared import assets
from . import context

console_info = log_mgr.console_info
console_error = log_mgr.console_error
configure_logging_level = log_mgr.configure_logging_level
resolve_file_path = cfg.resolve_file_path
build_runtime_context = cfg.build_runtime_context
load_configuration = cfg.load_configuration

DEFAULT_MODEL = cfg.DEFAULT_MODEL


def build_environment_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """Translate CLI arguments into runtime context overrides."""

    return {
        "ebooks_dir": args.ebooks_dir or os.environ.get("EBOOKS_DIR"),
        "working_dir": args.working_dir or os.environ.get("EBOOK_WORKING_DIR"),
        "output_dir": args.output_dir or os.environ.get("EBOOK_OUTPUT_DIR"),
        "tmp_dir": args.tmp_dir or os.environ.get("EBOOK_TMP_DIR"),
        "ffmpeg_path": args.ffmpeg_path or os.environ.get("FFMPEG_PATH"),
        "ollama_url": args.ollama_url or os.environ.get("OLLAMA_URL"),
        "thread_count": args.thread_count or os.environ.get("EBOOK_THREAD_COUNT"),
    }


def build_pipeline_configuration(
    config: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None
):
    """Return an up-to-date pipeline configuration for ``config``."""

    overrides = overrides or {}
    active_context = context.get_active_context(None)
    if active_context is None:
        active_context = context.refresh_runtime_context(config, overrides)
    pipeline_config = build_pipeline_config(active_context, config)
    return pipeline_config, active_context


def load_refined_sentences(
    input_file: str,
    config: Dict[str, Any],
    overrides: Optional[Dict[str, Any]] = None,
    *,
    force_refresh: bool = False,
) -> Tuple[List[str], bool]:
    """Load or refresh the refined sentence cache for ``input_file``."""

    overrides = overrides or {}
    pipeline_config, _ = build_pipeline_configuration(config, overrides)
    refined, refreshed = ingestion.get_refined_sentences(
        input_file,
        pipeline_config,
        force_refresh=force_refresh,
        metadata={"mode": "interactive"},
    )
    return refined, refreshed


def _resolve_input_path(
    input_file: str,
    active_context: cfg.RuntimeContext,
) -> Path:
    resolved_input_path = resolve_file_path(input_file, active_context.books_dir)
    if not resolved_input_path or not resolved_input_path.exists():
        search_hint = str(active_context.books_dir)
        console_error(
            "Error: EPUB file '%s' was not found. Check the ebooks directory (%s).",
            input_file,
            search_hint,
        )
        sys.exit(1)
    return resolved_input_path


def _normalise_target_languages(
    raw_targets: Optional[str], existing: List[str]
) -> List[str]:
    if raw_targets:
        targets = [x.strip() for x in raw_targets.split(",") if x.strip()]
        if targets:
            return targets
    return existing or context.default_target_languages()


def _build_pipeline_input(
    config: Dict[str, Any],
    input_file: str,
    base_output_file: str,
    target_languages: List[str],
    start_sentence: int,
    end_sentence: Optional[int],
) -> PipelineInput:
    book_metadata = {
        "book_title": config.get("book_title"),
        "book_author": config.get("book_author"),
        "book_year": config.get("book_year"),
        "book_summary": config.get("book_summary"),
        "book_cover_file": config.get("book_cover_file"),
    }
    return PipelineInput(
        input_file=input_file,
        base_output_file=base_output_file,
        input_language=config.get("input_language", context.default_language()),
        target_languages=target_languages,
        sentences_per_output_file=config.get("sentences_per_output_file", 10),
        start_sentence=start_sentence,
        end_sentence=end_sentence,
        stitch_full=config.get("stitch_full", False),
        generate_audio=config.get("generate_audio", True),
        audio_mode=config.get("audio_mode", assets.DEFAULT_ASSET_VALUES.get("audio_mode", "1")),
        written_mode=config.get(
            "written_mode", assets.DEFAULT_ASSET_VALUES.get("written_mode", "4")
        ),
        selected_voice=config.get("selected_voice", "gTTS"),
        output_html=config.get("output_html", True),
        output_pdf=config.get("output_pdf", False),
        generate_video=config.get("generate_video", False),
        include_transliteration=config.get("include_transliteration", False),
        tempo=config.get("tempo", 1.0),
        book_metadata=book_metadata,
    )


def _calculate_end_sentence(
    config: Dict[str, Any], start_sentence: int, candidate: Optional[str | int]
) -> Optional[int]:
    if candidate is None:
        return None
    if isinstance(candidate, int):
        return candidate
    if isinstance(candidate, str):
        trimmed = candidate.strip()
        if not trimmed:
            return None
        if trimmed.startswith("+") or trimmed.startswith("-"):
            try:
                return start_sentence + int(trimmed)
            except ValueError:
                return None
        if trimmed.isdigit():
            return int(trimmed)
    return None


def _prepare_output_path(
    base_output_file: Optional[str],
    target_languages: Sequence[str],
    input_file: str,
    active_context: cfg.RuntimeContext,
) -> str:
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    target_lang_str = "_".join(target_languages)
    if base_output_file:
        resolved_base = resolve_file_path(base_output_file, active_context.output_dir)
        os.makedirs(resolved_base.parent, exist_ok=True)
        return str(resolved_base)
    output_folder = os.path.join(
        active_context.output_dir, f"{target_lang_str}_{base_name}"
    )
    os.makedirs(output_folder, exist_ok=True)
    return os.path.join(output_folder, f"{target_lang_str}_{base_name}.html")


def prepare_non_interactive_run(
    args: argparse.Namespace,
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
) -> Tuple[PipelineRequest, Dict[str, Any]]:
    """Build a :class:`PipelineRequest` for non-interactive execution."""

    config = load_configuration(args.config, verbose=False)
    overrides = build_environment_overrides(args)
    context.refresh_runtime_context(config, overrides)
    config = context.update_book_cover_file_in_config(
        config,
        config.get("ebooks_dir"),
        debug_enabled=config.get("debug", False),
    )

    input_file = args.input_file or config.get("input_file")
    if not input_file:
        console_error(
            "Error: An input EPUB file must be specified either via CLI or configuration."
        )
        sys.exit(1)

    active_context = context.get_active_context(None)
    if active_context is None:
        active_context = build_runtime_context(config, overrides)
        cfg.set_runtime_context(active_context)

    resolved_input_path = _resolve_input_path(input_file, active_context)
    input_file = str(resolved_input_path)

    config.setdefault("input_language", context.default_language())
    if args.input_language:
        config["input_language"] = args.input_language

    config.setdefault(
        "target_languages", context.default_target_languages()
    )
    config["target_languages"] = _normalise_target_languages(
        args.target_languages, config.get("target_languages", [])
    )

    config["sentences_per_output_file"] = (
        args.sentences_per_output_file
        or config.get("sentences_per_output_file", 10)
    )

    base_output_file = _prepare_output_path(
        args.base_output_file or config.get("base_output_file"),
        config["target_languages"],
        input_file,
        active_context,
    )

    start_sentence = (
        args.start_sentence
        if args.start_sentence is not None
        else config.get("start_sentence", 1)
    )
    try:
        start_sentence = int(start_sentence)
    except (TypeError, ValueError):
        start_sentence = 1

    end_candidate = (
        args.end_sentence if args.end_sentence is not None else config.get("end_sentence")
    )
    end_sentence = _calculate_end_sentence(config, start_sentence, end_candidate)

    config.setdefault("stitch_full", False)
    config.setdefault("generate_audio", True)
    config.setdefault("audio_mode", assets.DEFAULT_ASSET_VALUES.get("audio_mode", "1"))
    config.setdefault("written_mode", assets.DEFAULT_ASSET_VALUES.get("written_mode", "4"))
    config.setdefault("selected_voice", "gTTS")
    config.setdefault("output_html", True)
    config.setdefault("output_pdf", False)
    config.setdefault("generate_video", False)
    config.setdefault("include_transliteration", False)
    config.setdefault("tempo", 1.0)
    config.setdefault("macos_reading_speed", 100)
    config.setdefault("sync_ratio", 0.9)
    config.setdefault("word_highlighting", True)
    config.setdefault("max_words", config.get("max_words", DEFAULT_MAX_WORDS))
    config.setdefault("ollama_model", DEFAULT_MODEL)

    pipeline_input = _build_pipeline_input(
        config,
        input_file,
        base_output_file,
        config["target_languages"],
        start_sentence,
        end_sentence,
    )

    if config.get("auto_metadata", True):
        metadata_manager.populate_config_metadata(config, input_file)
        pipeline_input.book_metadata = {
            "book_title": config.get("book_title"),
            "book_author": config.get("book_author"),
            "book_year": config.get("book_year"),
            "book_summary": config.get("book_summary"),
            "book_cover_file": config.get("book_cover_file"),
        }

    if args.debug:
        config["debug"] = True

    pipeline_overrides = {
        "generate_audio": config.get("generate_audio"),
        "audio_mode": config.get("audio_mode"),
        "selected_voice": config.get("selected_voice"),
        "tempo": config.get("tempo"),
        "macos_reading_speed": config.get("macos_reading_speed"),
        "sync_ratio": config.get("sync_ratio"),
        "word_highlighting": config.get("word_highlighting"),
        "max_words": config.get("max_words"),
        "split_on_comma_semicolon": config.get("split_on_comma_semicolon"),
        "debug": config.get("debug"),
        "ollama_model": config.get("ollama_model"),
        "ollama_url": config.get("ollama_url"),
        "ffmpeg_path": overrides.get("ffmpeg_path") or config.get("ffmpeg_path"),
        "thread_count": config.get("thread_count") or overrides.get("thread_count"),
        "queue_size": config.get("queue_size"),
        "pipeline_mode": config.get("pipeline_mode"),
    }

    request = PipelineRequest(
        config=config,
        context=active_context,
        environment_overrides=overrides,
        pipeline_overrides=pipeline_overrides,
        inputs=pipeline_input,
        progress_tracker=progress_tracker,
        stop_event=stop_event,
    )
    return request, config


def run_pipeline_from_args(
    args: argparse.Namespace,
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
) -> Optional[PipelineResponse]:
    """Execute the pipeline using an already parsed ``args`` namespace."""

    overrides = build_environment_overrides(args)

    if getattr(args, "interactive", False):
        from .interactive import MenuExit, run_interactive_menu

        try:
            config, pipeline_input = run_interactive_menu(
                overrides,
                args.config,
                entry_script_name="main.py",
            )
        except MenuExit:
            console_info("Interactive configuration cancelled by user.")
            return None

        config.setdefault("selected_voice", pipeline_input.selected_voice)
        config.setdefault("tempo", pipeline_input.tempo)
        config.setdefault("generate_audio", pipeline_input.generate_audio)
        config.setdefault("audio_mode", pipeline_input.audio_mode)
        config.setdefault("written_mode", pipeline_input.written_mode)
        config.setdefault("output_html", pipeline_input.output_html)
        config.setdefault("output_pdf", pipeline_input.output_pdf)
        config.setdefault("generate_video", pipeline_input.generate_video)
        config.setdefault(
            "include_transliteration", pipeline_input.include_transliteration
        )
        config.setdefault("macos_reading_speed", 100)
        config.setdefault("sync_ratio", 0.9)
        config.setdefault("word_highlighting", True)
        config.setdefault("max_words", DEFAULT_MAX_WORDS)
        config.setdefault("ollama_model", DEFAULT_MODEL)

        if config.get("auto_metadata", True) and pipeline_input.input_file:
            metadata_manager.populate_config_metadata(
                config, pipeline_input.input_file
            )
            pipeline_input.book_metadata = {
                "book_title": config.get("book_title"),
                "book_author": config.get("book_author"),
                "book_year": config.get("book_year"),
                "book_summary": config.get("book_summary"),
                "book_cover_file": config.get("book_cover_file"),
            }
        else:
            pipeline_input.book_metadata = pipeline_input.book_metadata or {}

        active_context = context.get_active_context(None)
        if active_context is None:
            active_context = build_runtime_context(config, overrides)
            cfg.set_runtime_context(active_context)

        pipeline_config = build_pipeline_config(active_context, config)
        pipeline_config.apply_runtime_settings()
        configure_logging_level(pipeline_config.debug)

        pipeline_overrides = {
            "generate_audio": config.get("generate_audio"),
            "audio_mode": config.get("audio_mode"),
            "selected_voice": config.get("selected_voice"),
            "tempo": config.get("tempo"),
            "macos_reading_speed": config.get("macos_reading_speed", 100),
            "sync_ratio": config.get("sync_ratio", 0.9),
            "word_highlighting": config.get("word_highlighting", True),
            "max_words": config.get("max_words", DEFAULT_MAX_WORDS),
            "split_on_comma_semicolon": config.get("split_on_comma_semicolon"),
            "debug": config.get("debug"),
            "ollama_model": config.get("ollama_model", DEFAULT_MODEL),
            "ollama_url": config.get("ollama_url"),
            "ffmpeg_path": overrides.get("ffmpeg_path") or config.get("ffmpeg_path"),
            "thread_count": config.get("thread_count") or overrides.get("thread_count"),
            "queue_size": config.get("queue_size"),
            "pipeline_mode": config.get("pipeline_mode"),
        }

        request = PipelineRequest(
            config=config,
            context=active_context,
            environment_overrides=overrides,
            pipeline_overrides=pipeline_overrides,
            inputs=pipeline_input,
            progress_tracker=progress_tracker,
            stop_event=stop_event,
        )
        response = run_pipeline_service(request)
        if not response.success:
            return None
        return response

    request, config = prepare_non_interactive_run(
        args,
        progress_tracker=progress_tracker,
        stop_event=stop_event,
    )
    response = run_pipeline_service(request)
    if not response.success and not getattr(args, "interactive", False):
        return None
    return response


__all__ = [
    "build_environment_overrides",
    "build_pipeline_configuration",
    "load_refined_sentences",
    "prepare_non_interactive_run",
    "run_pipeline_from_args",
]
