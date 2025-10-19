"""Service layer for executing the ebook processing pipeline."""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydub import AudioSegment

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import output_formatter
from ..core import ingestion
from ..core.config import PipelineConfig, build_pipeline_config
from ..core.rendering import process_epub
from ..progress_tracker import ProgressTracker

logger = log_mgr.logger
configure_logging_level = log_mgr.configure_logging_level


@dataclass(slots=True)
class PipelineInput:
    """User-supplied parameters describing a pipeline execution request."""

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
    book_metadata: Dict[str, Any]


@dataclass(slots=True)
class PipelineRequest:
    """Complete description of a pipeline execution request."""

    config: Dict[str, Any]
    context: Optional[cfg.RuntimeContext]
    environment_overrides: Dict[str, Any]
    pipeline_overrides: Dict[str, Any]
    inputs: PipelineInput
    progress_tracker: Optional[ProgressTracker] = None
    stop_event: Optional[threading.Event] = None


@dataclass(slots=True)
class PipelineResponse:
    """Result of running the ebook processing pipeline."""

    success: bool
    pipeline_config: Optional[PipelineConfig] = None
    refined_sentences: Optional[List[str]] = None
    refined_updated: bool = False
    written_blocks: Optional[List[str]] = None
    audio_segments: Optional[List[AudioSegment]] = None
    batch_video_files: Optional[List[str]] = None
    base_dir: Optional[str] = None
    base_output_stem: Optional[str] = None
    stitched_documents: Dict[str, str] = field(default_factory=dict)
    stitched_audio_path: Optional[str] = None
    stitched_video_path: Optional[str] = None


def run_pipeline(request: PipelineRequest) -> PipelineResponse:
    """Execute the ebook pipeline for the provided :class:`PipelineRequest`."""

    context = request.context or cfg.build_runtime_context(
        request.config, request.environment_overrides
    )
    cfg.set_runtime_context(context)

    pipeline_config: Optional[PipelineConfig] = None
    stitched_audio_path: Optional[str] = None
    stitched_video_path: Optional[str] = None
    stitched_documents: Dict[str, str] = {}
    tracker = request.progress_tracker

    try:
        overrides = {**request.environment_overrides, **request.pipeline_overrides}
        pipeline_config = build_pipeline_config(context, request.config, overrides=overrides)
        pipeline_config.apply_runtime_settings()
        configure_logging_level(pipeline_config.debug)

        inputs = request.inputs
        generate_audio = pipeline_config.generate_audio
        audio_mode = pipeline_config.audio_mode

        if tracker is not None:
            tracker.publish_start(
                {
                    "stage": "initialization",
                    "input_file": inputs.input_file,
                    "target_languages": tuple(inputs.target_languages),
                }
            )

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
        if tracker is not None:
            tracker.publish_progress(
                {
                    "stage": "ingestion",
                    "message": "Sentence ingestion complete.",
                    "total_sentences": total_fully,
                }
            )
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
            generate_audio,
            audio_mode,
            inputs.written_mode,
            inputs.output_html,
            inputs.output_pdf,
            refined_list=refined_list,
            generate_video=inputs.generate_video,
            include_transliteration=inputs.include_transliteration,
            book_metadata=inputs.book_metadata,
            pipeline_config=pipeline_config,
            progress_tracker=request.progress_tracker,
            stop_event=request.stop_event,
        )

        if tracker is not None:
            tracker.publish_progress(
                {
                    "stage": "rendering",
                    "message": "Rendering phase completed.",
                }
            )

        if request.stop_event and request.stop_event.is_set():
            logger.info(
                "Shutdown request acknowledged; skipping remaining post-processing steps."
            )
            if tracker is not None:
                tracker.publish_progress(
                    {
                        "stage": "shutdown",
                        "message": "Stop event acknowledged in pipeline.",
                    }
                )
        elif inputs.stitch_full:
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
            stitched_documents = output_formatter.stitch_full_output(
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
                for seg in all_audio_segments:
                    stitched_audio += seg
                stitched_audio_path = os.path.join(
                    base_dir,
                    f"{range_fragment}_{stitched_basename}.mp3",
                )
                stitched_audio.export(
                    stitched_audio_path, format="mp3", bitrate="320k"
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
                stitched_video_path = os.path.join(
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
                    stitched_video_path,
                ]
                subprocess.run(cmd_concat, check=True)
                os.remove(concat_list_path)
                logger.info(
                    "Stitched video slide output saved to: %s", stitched_video_path
                )
        logger.info("Processing complete.")
        return PipelineResponse(
            success=True,
            pipeline_config=pipeline_config,
            refined_sentences=refined_list,
            refined_updated=refined_updated,
            written_blocks=written_blocks,
            audio_segments=all_audio_segments,
            batch_video_files=batch_video_files,
            base_dir=base_dir,
            base_output_stem=base_no_ext,
            stitched_documents=stitched_documents,
            stitched_audio_path=stitched_audio_path,
            stitched_video_path=stitched_video_path,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("An error occurred: %s", exc)
        if tracker is not None:
            tracker.record_error(exc, {"stage": "pipeline"})
            tracker.mark_finished(reason="pipeline error", forced=True)
        return PipelineResponse(success=False, pipeline_config=pipeline_config)
    finally:
        if context is not None:
            try:
                cfg.cleanup_environment(context)
            except Exception as cleanup_exc:  # pragma: no cover - defensive logging
                logger.debug(
                    "Failed to clean up temporary workspace: %s", cleanup_exc
                )
        cfg.clear_runtime_context()
