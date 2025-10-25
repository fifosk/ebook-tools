"""FFmpeg-backed implementation of the :class:`VideoRenderer` protocol."""
from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Sequence, Tuple

from PIL import Image
from pydub import AudioSegment

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules import output_formatter
from modules.audio.highlight import timeline
from modules.video.slides import SlideRenderOptions, build_sentence_video

from .base import VideoRenderer

logger = log_mgr.logger


class FFmpegVideoRenderer(VideoRenderer):
    """Render slide videos locally using FFmpeg."""

    def render_slides(
        self,
        text_blocks: Sequence[str],
        audio_segments: Sequence[AudioSegment],
        output_dir: str,
        batch_start: int,
        batch_end: int,
        base_no_ext: str,
        cover_img: Optional[Image.Image],
        book_author: str,
        book_title: str,
        cumulative_word_counts: Sequence[int],
        total_word_count: int,
        macos_reading_speed: int,
        input_language: str,
        total_sentences: int,
        tempo: float,
        sync_ratio: float,
        word_highlighting: bool,
        highlight_granularity: str,
        slide_render_options: Optional[SlideRenderOptions] = None,
        cleanup: bool = True,
        slide_size: Sequence[int] = (1280, 720),
        initial_font_size: int = 60,
        bg_color: Optional[Sequence[int]] = None,
        template_name: Optional[str] = None,
    ) -> str:
        logger.info(
            "Generating video slide set for sentences %s to %s...", batch_start, batch_end
        )
        tasks = list(enumerate(zip(text_blocks, audio_segments)))
        worker_count = max(1, min(cfg.get_thread_count(), len(tasks)))
        ordered_results: list[Optional[str]] = [None] * len(tasks)

        def _render_sentence(index: int, block: str, audio_seg: AudioSegment) -> str:
            sentence_number = batch_start + index
            words_processed = cumulative_word_counts[sentence_number - 1]
            remaining_words = total_word_count - words_processed
            if macos_reading_speed > 0:
                est_seconds = int(remaining_words * 60 / macos_reading_speed)
            else:
                est_seconds = 0
            hours = est_seconds // 3600
            minutes = (est_seconds % 3600) // 60
            seconds = est_seconds % 60
            remaining_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            header_tokens = block.split("\n")[0].split(" - ")
            target_lang = header_tokens[0].strip() if header_tokens else ""
            progress_percentage = (
                (sentence_number / total_sentences) * 100 if total_sentences else 0
            )
            header_info = (
                f"Book: {book_title} | Author: {book_author}\n"
                f"Source Language: {input_language} | Target: {target_lang} | Speed: {tempo}\n"
                f"Sentence: {sentence_number}/{total_sentences} | Progress: {progress_percentage:.2f}% | Remaining: {remaining_time_str}"
            )

            local_cover = cover_img.copy() if cover_img else None

            timeline_result = timeline.build(
                block,
                audio_seg,
                timeline.TimelineBuildOptions(
                    sync_ratio=sync_ratio,
                    word_highlighting=word_highlighting,
                    highlight_granularity=highlight_granularity,
                ),
            )

            return build_sentence_video(
                block,
                audio_seg,
                sentence_number,
                sync_ratio=sync_ratio,
                word_highlighting=word_highlighting,
                highlight_events=timeline_result.events,
                highlight_granularity=timeline_result.effective_granularity,
                slide_size=slide_size,
                initial_font_size=initial_font_size,
                bg_color=bg_color,
                cover_img=local_cover,
                header_info=header_info,
                render_options=slide_render_options,
                template_name=template_name,
            )

        if worker_count == 1:
            for idx, (block, audio_seg) in tasks:
                try:
                    ordered_results[idx] = _render_sentence(idx, block, audio_seg)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error(
                        "Error generating sentence video for sentence %s: %s",
                        batch_start + idx,
                        exc,
                    )
        else:
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_map = {
                    executor.submit(_render_sentence, idx, block, audio_seg): idx
                    for idx, (block, audio_seg) in tasks
                }
                for future in as_completed(future_map):
                    idx = future_map[future]
                    try:
                        ordered_results[idx] = future.result()
                    except Exception as exc:  # pylint: disable=broad-except
                        logger.error(
                            "Error generating sentence video for sentence %s: %s",
                            batch_start + idx,
                            exc,
                        )

        sentence_video_files = [path for path in ordered_results if path]
        range_fragment = output_formatter.format_sentence_range(
            batch_start, batch_end, total_sentences
        )
        concat_list_path = os.path.join(output_dir, f"concat_{range_fragment}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as handle:
            for video_file in sentence_video_files:
                handle.write(f"file '{video_file}'\n")

        final_video_path = os.path.join(output_dir, f"{range_fragment}_{base_no_ext}.mp4")
        cmd_concat: Tuple[str, ...] = (
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
        )
        try:
            result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.error("FFmpeg final concat error: %s", result.stderr.decode())
                raise subprocess.CalledProcessError(result.returncode, cmd_concat)
        except subprocess.CalledProcessError as exc:
            logger.error("Error concatenating sentence slides: %s", exc)
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

        logger.info("Final stitched video slide output saved to: %s", final_video_path)

        if cleanup:
            for video_file in sentence_video_files:
                if os.path.exists(video_file):
                    os.remove(video_file)

        return final_video_path


__all__ = ["FFmpegVideoRenderer"]
