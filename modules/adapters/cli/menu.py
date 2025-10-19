#!/usr/bin/env python3
"""CLI adapter that orchestrates the ebook-tools pipeline."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from pydub import AudioSegment

from ... import config_manager as cfg
from ... import logging_manager as log_mgr
from ... import metadata_manager
from ... import output_formatter
from ...core import ingestion
from ...core.config import PipelineConfig, build_pipeline_config
from ...core.rendering import process_epub
from ...epub_parser import (
    DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    DEFAULT_MAX_WORDS,
)
from ...menu_interface import (
    MenuExit,
    parse_arguments,
    run_interactive_menu,
    update_book_cover_file_in_config,
)

logger = log_mgr.logger
configure_logging_level = log_mgr.configure_logging_level
resolve_file_path = cfg.resolve_file_path
initialize_environment = cfg.initialize_environment
load_configuration = cfg.load_configuration
DEFAULT_MODEL = cfg.DEFAULT_MODEL

ENTRY_SCRIPT_NAME = "main.py"


@dataclass(slots=True)
class PipelineInputs:
    """Collected parameters that drive a pipeline invocation."""

    input_file: str
    base_output_file: str
    input_language: str
    target_languages: List[str]
    sentences_per_output_file: int
    start_sentence: int
    end_sentence: Optional[int]
    stitch_full: bool
    generate_audio: bool
    audio_mode: str
    written_mode: str
    selected_voice: str
    output_html: bool
    output_pdf: bool
    generate_video: bool
    include_transliteration: bool
    tempo: float
    book_metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PipelineInputs":
        """Create :class:`PipelineInputs` from a generic mapping."""

        target_languages = list(data.get("target_languages") or [])
        if not target_languages:
            target_languages = ["Arabic"]
        return cls(
            input_file=str(data.get("input_file", "")),
            base_output_file=str(data.get("base_output_file", "")),
            input_language=str(data.get("input_language", "English")),
            target_languages=target_languages,
            sentences_per_output_file=int(data.get("sentences_per_output_file", 10)),
            start_sentence=int(data.get("start_sentence", 1)),
            end_sentence=data.get("end_sentence"),
            stitch_full=bool(data.get("stitch_full", False)),
            generate_audio=bool(data.get("generate_audio", True)),
            audio_mode=str(data.get("audio_mode", "1")),
            written_mode=str(data.get("written_mode", "4")),
            selected_voice=str(data.get("selected_voice", "gTTS")),
            output_html=bool(data.get("output_html", True)),
            output_pdf=bool(data.get("output_pdf", False)),
            generate_video=bool(data.get("generate_video", False)),
            include_transliteration=bool(
                data.get("include_transliteration", False)
            ),
            tempo=float(data.get("tempo", 1.0)),
            book_metadata=dict(data.get("book_metadata", {})),
        )


def _environment_overrides_from_args(args: Any) -> Dict[str, Any]:
    return {
        "ebooks_dir": args.ebooks_dir or os.environ.get("EBOOKS_DIR"),
        "working_dir": args.working_dir or os.environ.get("EBOOK_WORKING_DIR"),
        "output_dir": args.output_dir or os.environ.get("EBOOK_OUTPUT_DIR"),
        "tmp_dir": args.tmp_dir or os.environ.get("EBOOK_TMP_DIR"),
        "ffmpeg_path": args.ffmpeg_path or os.environ.get("FFMPEG_PATH"),
        "ollama_url": args.ollama_url or os.environ.get("OLLAMA_URL"),
        "thread_count": args.thread_count or os.environ.get("EBOOK_THREAD_COUNT"),
    }


def _ensure_runtime_defaults(config: Dict[str, Any]) -> None:
    config.setdefault("macos_reading_speed", 100)
    config.setdefault("sync_ratio", 0.9)
    config.setdefault("word_highlighting", True)
    config.setdefault("max_words", DEFAULT_MAX_WORDS)
    config.setdefault("ollama_model", DEFAULT_MODEL)
    config.setdefault(
        "split_on_comma_semicolon", DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON
    )
    if "selected_voice" not in config:
        config["selected_voice"] = "gTTS"
    if "tempo" not in config:
        config["tempo"] = 1.0
    if "generate_audio" not in config:
        config["generate_audio"] = True
    if "audio_mode" not in config:
        config["audio_mode"] = "1"
    if "written_mode" not in config:
        config["written_mode"] = "4"


def _update_config_from_inputs(config: Dict[str, Any], inputs: PipelineInputs) -> None:
    config.update(
        {
            "input_file": inputs.input_file,
            "base_output_file": inputs.base_output_file,
            "input_language": inputs.input_language,
            "target_languages": inputs.target_languages,
            "sentences_per_output_file": inputs.sentences_per_output_file,
            "start_sentence": inputs.start_sentence,
            "end_sentence": inputs.end_sentence,
            "stitch_full": inputs.stitch_full,
            "generate_audio": inputs.generate_audio,
            "audio_mode": inputs.audio_mode,
            "written_mode": inputs.written_mode,
            "selected_voice": inputs.selected_voice,
            "output_html": inputs.output_html,
            "output_pdf": inputs.output_pdf,
            "generate_video": inputs.generate_video,
            "include_transliteration": inputs.include_transliteration,
            "tempo": inputs.tempo,
        }
    )


def _collect_pipeline_overrides(
    config: Dict[str, Any], inputs: PipelineInputs, environment_overrides: Dict[str, Any]
) -> Dict[str, Any]:
    overrides = {
        "generate_audio": inputs.generate_audio,
        "audio_mode": inputs.audio_mode,
        "selected_voice": inputs.selected_voice,
        "tempo": inputs.tempo,
        "macos_reading_speed": config.get("macos_reading_speed"),
        "sync_ratio": config.get("sync_ratio"),
        "word_highlighting": config.get("word_highlighting"),
        "max_words": config.get("max_words"),
        "split_on_comma_semicolon": config.get("split_on_comma_semicolon"),
        "debug": config.get("debug"),
        "ollama_model": config.get("ollama_model"),
        "ollama_url": environment_overrides.get("ollama_url")
        or config.get("ollama_url"),
        "ffmpeg_path": environment_overrides.get("ffmpeg_path")
        or config.get("ffmpeg_path"),
        "thread_count": environment_overrides.get("thread_count")
        or config.get("thread_count"),
        "queue_size": config.get("queue_size"),
        "pipeline_mode": config.get("pipeline_mode"),
    }
    return {key: value for key, value in overrides.items() if value is not None}


def _parse_end_sentence(raw_value: Any, start_sentence: int) -> Optional[int]:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            return None
        if value.startswith("+") or value.startswith("-"):
            try:
                return start_sentence + int(value)
            except ValueError:
                return None
        if value.isdigit():
            return int(value)
    return None


def _prepare_interactive_session(
    args: Any, environment_overrides: Dict[str, Any]
) -> Tuple[Dict[str, Any], PipelineInputs]:
    try:
        config, session_data = run_interactive_menu(
            environment_overrides, args.config, entry_script_name=ENTRY_SCRIPT_NAME
        )
    except MenuExit:
        raise
    inputs = PipelineInputs.from_mapping(session_data)
    return config, inputs


def _prepare_non_interactive_session(
    args: Any, environment_overrides: Dict[str, Any]
) -> Tuple[Dict[str, Any], PipelineInputs]:
    config = load_configuration(args.config, verbose=False)
    initialize_environment(config, environment_overrides)
    config = update_book_cover_file_in_config(
        config,
        config.get("ebooks_dir"),
        debug_enabled=config.get("debug", False),
    )

    input_file = args.input_file or config.get("input_file")
    if not input_file:
        raise ValueError(
            "An input EPUB file must be specified either via CLI or configuration."
        )

    resolved_input_path = resolve_file_path(input_file, cfg.BOOKS_DIR)
    if not resolved_input_path or not resolved_input_path.exists():
        search_hint = cfg.BOOKS_DIR or config.get("ebooks_dir")
        raise FileNotFoundError(
            f"EPUB file '{input_file}' was not found. Check the ebooks directory ({search_hint})."
        )
    input_file = str(resolved_input_path)

    input_language = args.input_language or config.get("input_language", "English")
    target_languages: List[str]
    if args.target_languages:
        target_languages = [
            entry.strip()
            for entry in args.target_languages.split(",")
            if entry.strip()
        ]
    else:
        target_languages = list(config.get("target_languages", ["Arabic"]))
    if not target_languages:
        target_languages = ["Arabic"]

    sentences_per_output_file = (
        args.sentences_per_output_file or config.get("sentences_per_output_file", 10)
    )

    base_output_file = args.base_output_file or config.get("base_output_file")
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    target_lang_str = "_".join(target_languages)
    if base_output_file:
        resolved_base = resolve_file_path(base_output_file, cfg.EBOOK_DIR)
        os.makedirs(resolved_base.parent, exist_ok=True)
        base_output_file = str(resolved_base)
    else:
        output_folder = os.path.join(cfg.EBOOK_DIR, f"{target_lang_str}_{base_name}")
        os.makedirs(output_folder, exist_ok=True)
        base_output_file = os.path.join(
            output_folder, f"{target_lang_str}_{base_name}.html"
        )

    start_sentence_value = (
        args.start_sentence
        if args.start_sentence is not None
        else config.get("start_sentence", 1)
    )
    try:
        start_sentence = int(start_sentence_value)
    except (TypeError, ValueError):
        start_sentence = 1

    end_raw = (
        args.end_sentence
        if args.end_sentence is not None
        else config.get("end_sentence")
    )
    end_sentence = _parse_end_sentence(end_raw, start_sentence)

    generate_audio = bool(config.get("generate_audio", True))
    audio_mode = str(config.get("audio_mode", "1"))
    written_mode = str(config.get("written_mode", "4"))
    selected_voice = str(config.get("selected_voice", "gTTS"))
    output_html = bool(config.get("output_html", True))
    output_pdf = bool(config.get("output_pdf", False))
    generate_video = bool(config.get("generate_video", False))
    include_transliteration = bool(config.get("include_transliteration", False))
    tempo = float(config.get("tempo", 1.0))

    if config.get("auto_metadata", True):
        metadata_manager.populate_config_metadata(config, input_file)

    book_metadata = {
        "book_title": config.get("book_title"),
        "book_author": config.get("book_author"),
        "book_year": config.get("book_year"),
        "book_summary": config.get("book_summary"),
        "book_cover_file": config.get("book_cover_file"),
    }

    inputs = PipelineInputs(
        input_file=input_file,
        base_output_file=base_output_file,
        input_language=input_language,
        target_languages=target_languages,
        sentences_per_output_file=sentences_per_output_file,
        start_sentence=start_sentence,
        end_sentence=end_sentence,
        stitch_full=bool(config.get("stitch_full", False)),
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

    return config, inputs


def run_pipeline(
    *,
    progress_tracker: Optional[Any] = None,
    stop_event: Optional[threading.Event] = None,
) -> Optional[Any]:
    """Entry point for executing the ebook processing pipeline."""

    args = parse_arguments()
    environment_overrides = _environment_overrides_from_args(args)

    try:
        if args.interactive:
            config, inputs = _prepare_interactive_session(args, environment_overrides)
        else:
            config, inputs = _prepare_non_interactive_session(args, environment_overrides)
    except MenuExit:
        logger.info("Interactive configuration cancelled by user.")
        return None
    except FileNotFoundError as exc:
        logger.error("Error: %s", exc)
        sys.exit(1)
    except ValueError as exc:
        logger.error("Error: %s", exc)
        sys.exit(1)

    if args.debug:
        config["debug"] = True

    _ensure_runtime_defaults(config)
    _update_config_from_inputs(config, inputs)

    pipeline_overrides = _collect_pipeline_overrides(
        config, inputs, environment_overrides
    )

    pipeline_config = build_pipeline_config(config, overrides=pipeline_overrides)
    pipeline_config.apply_runtime_settings()
    configure_logging_level(pipeline_config.debug)
    cfg.set_thread_count(pipeline_config.thread_count)
    cfg.set_queue_size(pipeline_config.queue_size)
    cfg.set_pipeline_mode(pipeline_config.pipeline_enabled)

    logger.info("Starting EPUB processing...")
    logger.info("Input file: %s", inputs.input_file)
    logger.info("Base output file: %s", inputs.base_output_file)
    logger.info("Input language: %s", inputs.input_language)
    logger.info("Target languages: %s", ", ".join(inputs.target_languages))
    logger.info(
        "Sentences per output file: %s", inputs.sentences_per_output_file
    )
    logger.info("Starting from sentence: %s", inputs.start_sentence)
    if inputs.end_sentence is not None:
        logger.info("Ending at sentence: %s", inputs.end_sentence)
    else:
        logger.info("Processing until end of file")

    try:
        refined_list, refined_updated = ingestion.get_refined_sentences(
            inputs.input_file,
            pipeline_config,
            force_refresh=True,
            metadata={
                "mode": "cli",
                "target_languages": inputs.target_languages,
                "max_words": pipeline_config.max_words,
            },
        )
        total_fully = len(refined_list)
        if refined_updated:
            refined_output_path = ingestion.refined_list_output_path(
                inputs.input_file, pipeline_config
            )
            logger.info("Refined sentence list written to: %s", refined_output_path)

        (
            written_blocks,
            all_audio_segments,
            batch_video_files,
            base_dir,
            base_no_ext,
        ) = process_epub(
            inputs.input_file,
            inputs.base_output_file,
            inputs.input_language,
            inputs.target_languages,
            inputs.sentences_per_output_file,
            inputs.start_sentence,
            inputs.end_sentence,
            pipeline_config.generate_audio,
            pipeline_config.audio_mode,
            inputs.written_mode,
            inputs.output_html,
            inputs.output_pdf,
            refined_list=refined_list,
            generate_video=inputs.generate_video,
            include_transliteration=inputs.include_transliteration,
            book_metadata=inputs.book_metadata,
            pipeline_config=pipeline_config,
            progress_tracker=progress_tracker,
            stop_event=stop_event,
        )

        if stop_event and stop_event.is_set():
            logger.info(
                "Shutdown request acknowledged; skipping remaining post-processing steps."
            )

        if inputs.stitch_full and not (stop_event and stop_event.is_set()):
            final_sentence = (
                inputs.start_sentence + len(written_blocks) - 1
                if written_blocks
                else inputs.start_sentence
            )
            stitched_basename = output_formatter.compute_stitched_basename(
                inputs.input_file, inputs.target_languages
            )
            range_fragment = output_formatter.format_sentence_range(
                inputs.start_sentence, final_sentence, total_fully
            )
            output_formatter.stitch_full_output(
                base_dir,
                inputs.start_sentence,
                final_sentence,
                stitched_basename,
                written_blocks,
                inputs.target_languages[0],
                total_fully,
                output_html=inputs.output_html,
                output_pdf=inputs.output_pdf,
                epub_title=f"Stitched Translation: {range_fragment} {stitched_basename}",
            )
            if pipeline_config.generate_audio and all_audio_segments:
                stitched_audio = AudioSegment.empty()
                for segment in all_audio_segments:
                    stitched_audio += segment
                stitched_audio_filename = os.path.join(
                    base_dir,
                    f"{range_fragment}_{stitched_basename}.mp3",
                )
                stitched_audio.export(
                    stitched_audio_filename, format="mp3", bitrate="320k"
                )
            if inputs.generate_video and batch_video_files:
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
                logger.info(
                    "Stitched video slide output saved to: %s", final_video_path
                )
        elif inputs.stitch_full and stop_event and stop_event.is_set():
            logger.info("Skipping stitched outputs due to shutdown request.")

        logger.info("Processing complete.")
        return None
    except Exception as exc:
        logger.error("An error occurred: %s", exc)
        return None


__all__ = ["run_pipeline", "PipelineInputs", "PipelineConfig"]
