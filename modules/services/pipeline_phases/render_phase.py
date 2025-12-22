"""Rendering and stitching helpers for the pipeline."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pydub import AudioSegment

from ... import logging_manager as log_mgr
from ... import output_formatter
from ...core.rendering import RenderPhaseRequest, process_epub
from ...video.api import VideoService
from ..pipeline_types import (
    ConfigPhaseResult,
    MetadataPhaseResult,
    RenderResult,
    StitchingArtifacts,
)

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from ..pipeline_service import PipelineRequest
    from ...progress_tracker import ProgressTracker

logger = log_mgr.logger


def execute_render_phase(
    request: "PipelineRequest",
    config_result: ConfigPhaseResult,
    metadata_result: MetadataPhaseResult,
    tracker: "ProgressTracker" | None,
) -> RenderResult:
    """Render ebook outputs for ``request``."""

    render_request = RenderPhaseRequest(
        pipeline_config=config_result.pipeline_config,
        input_file=request.inputs.input_file,
        base_output_file=request.inputs.base_output_file,
        input_language=request.inputs.input_language,
        target_languages=request.inputs.target_languages,
        sentences_per_file=request.inputs.sentences_per_output_file,
        start_sentence=request.inputs.start_sentence,
        end_sentence=request.inputs.end_sentence,
        generate_audio=config_result.generate_audio,
        audio_mode=config_result.audio_mode,
        written_mode=request.inputs.written_mode,
        output_html=request.inputs.output_html,
        output_pdf=request.inputs.output_pdf,
        refined_sentences=metadata_result.ingestion.refined_sentences,
        generate_video=request.inputs.generate_video,
        generate_images=bool(getattr(request.inputs, "add_images", False)),
        include_transliteration=request.inputs.include_transliteration,
        book_metadata=metadata_result.metadata.as_dict(),
    )
    (
        written_blocks,
        all_audio_segments,
        batch_video_files,
        base_dir,
        base_no_ext,
    ) = process_epub(
        render_request,
        progress_tracker=request.progress_tracker,
        stop_event=request.stop_event,
        translation_pool=request.translation_pool,
    )

    if tracker is not None:
        tracker.publish_progress(
            {
                "stage": "rendering",
                "message": "Rendering phase completed.",
            }
        )

    return RenderResult(
        written_blocks=written_blocks,
        audio_segments=all_audio_segments,
        batch_video_files=batch_video_files,
        base_dir=base_dir,
        base_output_stem=base_no_ext,
    )


def build_stitching_artifacts(
    request: "PipelineRequest",
    config_result: ConfigPhaseResult,
    metadata_result: MetadataPhaseResult,
    render_result: RenderResult,
) -> StitchingArtifacts:
    """Create stitched ebook, audio, and video artifacts if requested."""

    if not request.inputs.stitch_full or not render_result.base_dir:
        return StitchingArtifacts()

    final_sentence = (
        request.inputs.start_sentence + len(render_result.written_blocks) - 1
        if render_result.written_blocks
        else request.inputs.start_sentence
    )
    stitched_basename = output_formatter.compute_stitched_basename(
        request.inputs.input_file, request.inputs.target_languages
    )
    range_fragment = output_formatter.format_sentence_range(
        request.inputs.start_sentence,
        final_sentence,
        metadata_result.ingestion.total_sentences,
    )
    documents = output_formatter.stitch_full_output(
        render_result.base_dir,
        request.inputs.start_sentence,
        final_sentence,
        stitched_basename,
        render_result.written_blocks,
        request.inputs.target_languages[0],
        metadata_result.ingestion.total_sentences,
        output_html=request.inputs.output_html,
        output_pdf=request.inputs.output_pdf,
        epub_title=f"Stitched Translation: {range_fragment} {stitched_basename}",
    )

    audio_segments = render_result.audio_segments or []
    audio_path_result: str | None = None
    if config_result.generate_audio and audio_segments:
        stitched_audio = AudioSegment.empty()
        for seg in audio_segments:
            stitched_audio += seg
        audio_path_result = os.path.join(
            render_result.base_dir,
            f"{range_fragment}_{stitched_basename}.mp3",
        )
        raw_bitrate = getattr(config_result.pipeline_config, "audio_bitrate_kbps", None)
        try:
            bitrate_kbps = int(raw_bitrate)
        except (TypeError, ValueError):
            bitrate_kbps = 0
        if bitrate_kbps > 0:
            stitched_audio.export(
                audio_path_result,
                format="mp3",
                bitrate=f"{bitrate_kbps}k",
            )
        else:
            stitched_audio.export(audio_path_result, format="mp3")

    video_path_result: str | None = None
    if request.inputs.generate_video and render_result.batch_video_files:
        logger.info(
            "Generating stitched video slide output by concatenating batch video files...",
            extra={
                "event": "pipeline.stitching.video.start",
                "console_suppress": True,
            },
        )
        video_path_result = os.path.join(
            render_result.base_dir,
            f"{range_fragment}_{stitched_basename}_stitched.mp4",
        )
        service = VideoService(
            backend=config_result.pipeline_config.video_backend,
            backend_settings=config_result.pipeline_config.video_backend_settings,
        )
        service.concatenate(render_result.batch_video_files, video_path_result)
        logger.info(
            "Stitched video slide output saved",
            extra={
                "event": "pipeline.stitching.video.complete",
                "attributes": {"path": video_path_result},
                "console_suppress": True,
            },
        )

    return StitchingArtifacts(
        documents=documents,
        audio_path=audio_path_result,
        video_path=video_path_result,
    )
