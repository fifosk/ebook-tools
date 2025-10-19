#!/usr/bin/env python3
from __future__ import annotations

import os
import threading
from typing import Optional

from . import config_manager as cfg
from . import logging_manager as log_mgr
from . import metadata_manager
from .epub_parser import DEFAULT_MAX_WORDS
from .menu_interface import (
    MenuExit,
    parse_arguments,
    run_interactive_menu,
    update_book_cover_file_in_config,
)
from .progress_tracker import ProgressTracker
from .services.pipeline_service import (
    PipelineInput,
    PipelineRequest,
    run_pipeline as run_pipeline_service,
)

logger = log_mgr.logger
configure_logging_level = log_mgr.configure_logging_level
resolve_file_path = cfg.resolve_file_path
build_runtime_context = cfg.build_runtime_context
load_configuration = cfg.load_configuration
DEFAULT_MODEL = cfg.DEFAULT_MODEL

ENTRY_SCRIPT_NAME = "main.py"

def run_pipeline(
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
):
    """Entry point for executing the ebook processing pipeline."""

    args = parse_arguments()
    config: dict = {}
    pipeline_input: Optional[PipelineInput] = None

    environment_overrides = {
        "ebooks_dir": args.ebooks_dir or os.environ.get("EBOOKS_DIR"),
        "working_dir": args.working_dir or os.environ.get("EBOOK_WORKING_DIR"),
        "output_dir": args.output_dir or os.environ.get("EBOOK_OUTPUT_DIR"),
        "tmp_dir": args.tmp_dir or os.environ.get("EBOOK_TMP_DIR"),
        "ffmpeg_path": args.ffmpeg_path or os.environ.get("FFMPEG_PATH"),
        "ollama_url": args.ollama_url or os.environ.get("OLLAMA_URL"),
        "thread_count": args.thread_count or os.environ.get("EBOOK_THREAD_COUNT"),
    }

    context: Optional[cfg.RuntimeContext] = None

    if args.interactive:
        try:
            config, pipeline_input = run_interactive_menu(
                environment_overrides,
                args.config,
                entry_script_name=ENTRY_SCRIPT_NAME,
            )
        except MenuExit:
            logger.info("Interactive configuration cancelled by user.")
            return None
        context = cfg.get_runtime_context(None)
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
    else:
        config = load_configuration(args.config, verbose=False)
        context = build_runtime_context(config, environment_overrides)
        cfg.set_runtime_context(context)
        config = update_book_cover_file_in_config(
            config,
            config.get("ebooks_dir"),
            debug_enabled=config.get("debug", False),
        )

        input_file = args.input_file or config.get("input_file")
        if not input_file:
            logger.error(
                "Error: An input EPUB file must be specified either via CLI or configuration."
            )
            sys.exit(1)

        resolved_input_path = resolve_file_path(input_file, context.books_dir)
        if not resolved_input_path or not resolved_input_path.exists():
            search_hint = str(context.books_dir)
            logger.error(
                "Error: EPUB file '%s' was not found. Check the ebooks directory (%s).",
                input_file,
                search_hint,
            )
            sys.exit(1)
        input_file = str(resolved_input_path)

        input_language = args.input_language or config.get("input_language", "English")
        target_languages = config.get("target_languages", ["Arabic"])
        if args.target_languages:
            target_languages = [
                x.strip() for x in args.target_languages.split(",") if x.strip()
            ]
        if not target_languages:
            target_languages = ["Arabic"]

        sentences_per_output_file = (
            args.sentences_per_output_file
            or config.get("sentences_per_output_file", 10)
        )

        base_output_file = args.base_output_file or config.get("base_output_file")
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        target_lang_str = "_".join(target_languages)
        if base_output_file:
            resolved_base = resolve_file_path(base_output_file, context.output_dir)
            os.makedirs(resolved_base.parent, exist_ok=True)
            base_output_file = str(resolved_base)
        else:
            output_folder = os.path.join(
                context.output_dir, f"{target_lang_str}_{base_name}"
            )
            os.makedirs(output_folder, exist_ok=True)
            base_output_file = os.path.join(
                output_folder, f"{target_lang_str}_{base_name}.html"
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

        end_sentence = None
        end_arg = (
            args.end_sentence
            if args.end_sentence is not None
            else config.get("end_sentence")
        )
        if isinstance(end_arg, str):
            end_arg = end_arg.strip()
            if end_arg.startswith("+") or end_arg.startswith("-"):
                try:
                    end_sentence = start_sentence + int(end_arg)
                except ValueError:
                    end_sentence = None
            elif end_arg.isdigit():
                end_sentence = int(end_arg)
        elif isinstance(end_arg, int):
            end_sentence = end_arg

        stitch_full = config.get("stitch_full", False)
        generate_audio = config.get("generate_audio", True)
        audio_mode = config.get("audio_mode", "1")
        written_mode = config.get("written_mode", "4")
        selected_voice = config.get("selected_voice", "gTTS")
        config.setdefault("selected_voice", selected_voice)
        output_html = config.get("output_html", True)
        output_pdf = config.get("output_pdf", False)
        generate_video = config.get("generate_video", False)
        include_transliteration = config.get("include_transliteration", False)
        tempo = config.get("tempo", 1.0)
        config["tempo"] = tempo
        config.setdefault("macos_reading_speed", 100)
        config.setdefault("sync_ratio", 0.9)
        config.setdefault("word_highlighting", True)
        config.setdefault("max_words", config.get("max_words", DEFAULT_MAX_WORDS))

        if config.get("auto_metadata", True):
            metadata_manager.populate_config_metadata(config, input_file)

        book_metadata = {
            "book_title": config.get("book_title"),
            "book_author": config.get("book_author"),
            "book_year": config.get("book_year"),
            "book_summary": config.get("book_summary"),
            "book_cover_file": config.get("book_cover_file"),
        }

        pipeline_input = PipelineInput(
            input_file=input_file,
            base_output_file=base_output_file,
            input_language=input_language,
            target_languages=target_languages,
            sentences_per_output_file=sentences_per_output_file,
            start_sentence=start_sentence,
            end_sentence=end_sentence,
            stitch_full=stitch_full,
            generate_audio=generate_audio,
            audio_mode=audio_mode,
            written_mode=written_mode,
            selected_voice=selected_voice,
            output_html=output_html,
            output_pdf=output_pdf,
            generate_video=generate_video,
            include_transliteration=include_transliteration,
            tempo=tempo,
            book_metadata=book_metadata,
        )

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
        "ffmpeg_path": environment_overrides.get("ffmpeg_path")
        or config.get("ffmpeg_path"),
        "thread_count": config.get("thread_count")
        or environment_overrides.get("thread_count"),
        "queue_size": config.get("queue_size"),
        "pipeline_mode": config.get("pipeline_mode"),
    }

    if pipeline_input is None:
        logger.error("Pipeline input could not be constructed.")
        return None

    if context is None:
        context = build_runtime_context(config, environment_overrides)

    request = PipelineRequest(
        config=config,
        context=context,
        environment_overrides=environment_overrides,
        pipeline_overrides=pipeline_overrides,
        inputs=pipeline_input,
        progress_tracker=progress_tracker,
        stop_event=stop_event,
    )

    response = run_pipeline_service(request)
    if not response.success and not args.interactive:
        return None
    return response


if __name__ == "__main__":
    run_pipeline()
