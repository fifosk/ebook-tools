#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import threading
from typing import Optional

from pydub import AudioSegment

from . import config_manager as cfg
from . import logging_manager as log_mgr
from . import metadata_manager
from .core.config import build_pipeline_config
from .core import ingestion
from .core.rendering import process_epub
from .core.translation import transliterate_sentence, translate_sentence_simple
from .epub_parser import DEFAULT_MAX_WORDS
from .menu_interface import (
    MenuExit,
    parse_arguments,
    run_interactive_menu,
    update_book_cover_file_in_config,
)
from .progress_tracker import ProgressTracker
from . import output_formatter

logger = log_mgr.logger
configure_logging_level = log_mgr.configure_logging_level
resolve_file_path = cfg.resolve_file_path
initialize_environment = cfg.initialize_environment
load_configuration = cfg.load_configuration
DEFAULT_MODEL = cfg.DEFAULT_MODEL

ENTRY_SCRIPT_NAME = "main.py"

def run_pipeline(
    *,
    progress_tracker: Optional[ProgressTracker] = None,
    stop_event: Optional[threading.Event] = None,
):
    """Entry point for executing the ebook processing pipeline."""
    global OLLAMA_MODEL, DEBUG, SELECTED_VOICE, MAX_WORDS, EXTEND_SPLIT_WITH_COMMA_SEMICOLON
    global MACOS_READING_SPEED, SYNC_RATIO, WORD_HIGHLIGHTING, TEMPO

    args = parse_arguments()
    config: dict = {}

    environment_overrides = {
        "ebooks_dir": args.ebooks_dir or os.environ.get("EBOOKS_DIR"),
        "working_dir": args.working_dir or os.environ.get("EBOOK_WORKING_DIR"),
        "output_dir": args.output_dir or os.environ.get("EBOOK_OUTPUT_DIR"),
        "tmp_dir": args.tmp_dir or os.environ.get("EBOOK_TMP_DIR"),
        "ffmpeg_path": args.ffmpeg_path or os.environ.get("FFMPEG_PATH"),
        "ollama_url": args.ollama_url or os.environ.get("OLLAMA_URL"),
        "thread_count": args.thread_count or os.environ.get("EBOOK_THREAD_COUNT"),
    }

    if args.interactive:
        try:
            config, interactive_results = run_interactive_menu(
                environment_overrides,
                args.config,
                entry_script_name=ENTRY_SCRIPT_NAME,
            )
        except MenuExit:
            logger.info("Interactive configuration cancelled by user.")
            return None
        (
            input_file,
            base_output_file,
            input_language,
            target_languages,
            sentences_per_output_file,
            start_sentence,
            end_sentence,
            stitch_full,
            generate_audio,
            audio_mode,
            written_mode,
            selected_voice,
            output_html,
            output_pdf,
            generate_video,
            include_transliteration,
            tempo,
            book_metadata,
        ) = interactive_results

        selected_voice = config.get("selected_voice", selected_voice)
        config["selected_voice"] = selected_voice
        tempo = config.get("tempo", tempo)
        config["tempo"] = tempo
        generate_audio = config.get("generate_audio", generate_audio)
        config["generate_audio"] = generate_audio
        audio_mode = config.get("audio_mode", audio_mode)
        config["audio_mode"] = audio_mode
        written_mode = config.get("written_mode", written_mode)
        config["written_mode"] = written_mode
        output_html = config.get("output_html", output_html)
        config["output_html"] = output_html
        output_pdf = config.get("output_pdf", output_pdf)
        config["output_pdf"] = output_pdf
        generate_video = config.get("generate_video", generate_video)
        config["generate_video"] = generate_video
        include_transliteration = config.get(
            "include_transliteration", include_transliteration
        )
        config["include_transliteration"] = include_transliteration
        config.setdefault("macos_reading_speed", 100)
        config.setdefault("sync_ratio", 0.9)
        config.setdefault("word_highlighting", True)
        config.setdefault("max_words", DEFAULT_MAX_WORDS)
        config.setdefault("ollama_model", DEFAULT_MODEL)

        if config.get("auto_metadata", True) and input_file:
            metadata_manager.populate_config_metadata(config, input_file)
            book_metadata = {
                "book_title": config.get("book_title"),
                "book_author": config.get("book_author"),
                "book_year": config.get("book_year"),
                "book_summary": config.get("book_summary"),
                "book_cover_file": config.get("book_cover_file"),
            }
        else:
            book_metadata = book_metadata or {}
    else:
        config = load_configuration(args.config, verbose=False)
        initialize_environment(config, environment_overrides)
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

        resolved_input_path = resolve_file_path(input_file, cfg.BOOKS_DIR)
        if not resolved_input_path or not resolved_input_path.exists():
            search_hint = cfg.BOOKS_DIR or config.get("ebooks_dir")
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
            resolved_base = resolve_file_path(base_output_file, cfg.EBOOK_DIR)
            os.makedirs(resolved_base.parent, exist_ok=True)
            base_output_file = str(resolved_base)
        else:
            output_folder = os.path.join(
                cfg.EBOOK_DIR, f"{target_lang_str}_{base_name}"
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

    if args.debug:
        config["debug"] = True

    cfg.set_thread_count(config.get("thread_count"))
    cfg.set_queue_size(config.get("queue_size"))
    cfg.set_pipeline_mode(config.get("pipeline_mode"))

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

    pipeline_config = build_pipeline_config(
        config, overrides={**environment_overrides, **pipeline_overrides}
    )
    pipeline_config.apply_runtime_settings()
    configure_logging_level(pipeline_config.debug)

    generate_audio = pipeline_config.generate_audio
    audio_mode = pipeline_config.audio_mode

    try:
        logger.info("Starting EPUB processing...")
        logger.info("Input file: %s", input_file)
        logger.info("Base output file: %s", base_output_file)
        logger.info("Input language: %s", input_language)
        logger.info("Target languages: %s", ", ".join(target_languages))
        logger.info("Sentences per output file: %s", sentences_per_output_file)
        logger.info("Starting from sentence: %s", start_sentence)
        if end_sentence is not None:
            logger.info("Ending at sentence: %s", end_sentence)
        else:
            logger.info("Processing until end of file")

        refined_list, refined_updated = ingestion.get_refined_sentences(
            input_file,
            pipeline_config,
            force_refresh=True,
            metadata={
                "mode": "cli",
                "target_languages": target_languages,
                "max_words": pipeline_config.max_words,
            },
        )
        total_fully = len(refined_list)
        if refined_updated:
            refined_output_path = ingestion.refined_list_output_path(
                input_file, pipeline_config
            )
            logger.info("Refined sentence list written to: %s", refined_output_path)
        (
            written_blocks,
            all_audio_segments,
            batch_video_files,
            base_dir,
            base_no_ext,
        ) = process_epub(
            input_file,
            base_output_file,
            input_language,
            target_languages,
            sentences_per_output_file,
            start_sentence,
            end_sentence,
            generate_audio,
            audio_mode,
            written_mode,
            output_html,
            output_pdf,
            refined_list=refined_list,
            generate_video=generate_video,
            include_transliteration=include_transliteration,
            book_metadata=book_metadata,
            pipeline_config=pipeline_config,
            progress_tracker=progress_tracker,
            stop_event=stop_event,
        )
        if stop_event and stop_event.is_set():
            logger.info("Shutdown request acknowledged; skipping remaining post-processing steps.")
        if stitch_full and not (stop_event and stop_event.is_set()):
            final_sentence = (
                start_sentence + len(written_blocks) - 1 if written_blocks else start_sentence
            )
            stitched_basename = output_formatter.compute_stitched_basename(
                input_file, target_languages
            )
            range_fragment = output_formatter.format_sentence_range(
                start_sentence, final_sentence, total_fully
            )
            output_formatter.stitch_full_output(
                base_dir,
                start_sentence,
                final_sentence,
                stitched_basename,
                written_blocks,
                target_languages[0],
                total_fully,
                output_html=output_html,
                output_pdf=output_pdf,
                epub_title=f"Stitched Translation: {range_fragment} {stitched_basename}",
            )
            if pipeline_config.generate_audio and all_audio_segments:
                stitched_audio = AudioSegment.empty()
                for seg in all_audio_segments:
                    stitched_audio += seg
                stitched_audio_filename = os.path.join(
                    base_dir,
                    f"{range_fragment}_{stitched_basename}.mp3",
                )
                stitched_audio.export(stitched_audio_filename, format="mp3", bitrate="320k")
            if generate_video and batch_video_files:
                logger.info(
                    "Generating stitched video slide output by concatenating batch video files..."
                )
                concat_list_path = os.path.join(
                    base_dir, f"concat_full_{stitched_basename}.txt"
                )
                with open(concat_list_path, "w", encoding="utf-8") as file_obj:
                    for video_file in batch_video_files:
                        file_obj.write(f"file '{video_file}'\n")
                final_video_path = os.path.join(
                    base_dir,
                    f"{range_fragment}_{stitched_basename}_stitched.mp4",
                )
                cmd_concat = [
                    "ffmpeg",
                    "-loglevel",
                    "quiet",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_list_path,
                    "-c",
                    "copy",
                    final_video_path,
                ]
                subprocess.run(cmd_concat, check=True)
                os.remove(concat_list_path)
                logger.info("Stitched video slide output saved to: %s", final_video_path)
        elif stitch_full and stop_event and stop_event.is_set():
            logger.info("Skipping stitched outputs due to shutdown request.")
        logger.info("Processing complete.")
    except Exception as exc:
        logger.error("An error occurred: %s", exc)


if __name__ == "__main__":
    run_pipeline()
