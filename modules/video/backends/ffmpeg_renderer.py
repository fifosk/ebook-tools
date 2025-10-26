"""FFmpeg-backed video renderer implementation."""

from __future__ import annotations

import os
from typing import Iterable, Mapping, MutableMapping, Sequence

from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules import output_formatter
from modules.audio.tts import silence_audio_path
from modules.media.command_runner import run_command
from modules.video.slides import prepare_sentence_frames

from .base import BaseVideoRenderer, VideoRenderOptions

logger = log_mgr.logger

DEFAULT_FRAME_PRESET: Sequence[str] = (
    "-c:v",
    "libx264",
    "-pix_fmt",
    "yuv420p",
    "-vf",
    "format=yuv420p",
    "-an",
)
DEFAULT_CONCAT_PRESET: Sequence[str] = ("-c", "copy")
DEFAULT_MERGE_PRESET: Sequence[str] = ("-c:v", "copy", "-c:a", "aac")


class FFmpegVideoRenderer(BaseVideoRenderer):
    """Render slide videos locally using FFmpeg."""

    def __init__(
        self,
        *,
        executable: str = "ffmpeg",
        loglevel: str = "quiet",
        presets: Mapping[str, Iterable[str] | str] | None = None,
        frame_builder=prepare_sentence_frames,
        command_runner=run_command,
    ) -> None:
        self._frame_builder = frame_builder
        self._run_external = command_runner
        self._executable = executable
        self._loglevel = loglevel
        self._presets = self._normalise_presets(presets or {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def render_slides(
        self,
        slides: Sequence[str],
        audio_tracks: Sequence[AudioSegment],
        output_path: str,
        options: VideoRenderOptions,
    ) -> str:
        if len(slides) != len(audio_tracks):
            raise ValueError("Number of slides must match number of audio tracks")

        if not slides:
            raise ValueError("At least one slide is required to render a video")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        range_fragment = output_formatter.format_sentence_range(
            options.batch_start,
            options.batch_end,
            options.total_sentences or len(slides),
        )
        logger.info(
            "Generating video slide set for sentences %s to %s...",
            options.batch_start,
            options.batch_end,
            extra={
                "event": "video.render.batch.start",
                "attributes": {"range": range_fragment, "backend": "ffmpeg"},
            },
        )

        sentence_videos: list[str] = []

        for index, (block, audio_seg) in enumerate(
            zip(slides, audio_tracks), start=options.batch_start
        ):
            header_info = self._build_header_info(block, index, options)
            frame_batch = self._frame_builder(
                block,
                audio_seg,
                index,
                sync_ratio=options.sync_ratio,
                word_highlighting=options.word_highlighting,
                highlight_granularity=options.highlight_granularity,
                slide_size=options.slide_size,
                initial_font_size=options.initial_font_size,
                default_font_path=options.default_font_path,
                bg_color=options.bg_color,
                cover_img=options.cover_image,
                header_info=header_info,
                render_options=options.slide_render_options,
                template_name=options.template_name,
            )

            sentence_video = self._render_sentence(
                audio_seg,
                index,
                frame_batch,
                cleanup=options.cleanup,
            )
            sentence_videos.append(sentence_video)

        final_video = self.concatenate(sentence_videos, output_path)

        if options.cleanup:
            for path in sentence_videos:
                self._safe_remove(path)

        logger.info(
            "Final stitched video slide output saved to: %s",
            final_video,
            extra={
                "event": "video.render.batch.complete",
                "attributes": {"path": final_video, "backend": "ffmpeg"},
            },
        )
        return final_video

    def concatenate(self, video_paths: Sequence[str], output_path: str) -> str:
        if not video_paths:
            raise ValueError("No video files provided for concatenation")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        concat_list_path = f"{output_path}.concat.txt"
        with open(concat_list_path, "w", encoding="utf-8") as handle:
            for video_file in video_paths:
                handle.write(f"file '{video_file}'\n")

        command = [
            self._executable,
            "-loglevel",
            self._loglevel,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
        ]
        command.extend(self._preset("concat", DEFAULT_CONCAT_PRESET))
        command.append(output_path)

        try:
            self._run_command(command)
        finally:
            self._safe_remove(concat_list_path)

        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _render_sentence(
        self,
        audio_seg: AudioSegment,
        sentence_number: int,
        frame_batch,
        *,
        cleanup: bool,
    ) -> str:
        frame_tasks = list(frame_batch.frame_tasks)
        if not frame_tasks:
            raise ValueError("No frame tasks produced for sentence rendering")

        tmp_dir = os.path.dirname(frame_tasks[0].output_path)
        os.makedirs(tmp_dir, exist_ok=True)

        word_video_files: list[str] = []
        for task in frame_tasks:
            word_video_path = os.path.join(
                tmp_dir, f"word_slide_{sentence_number}_{task.index}.mp4"
            )
            command = [
                self._executable,
                "-loglevel",
                self._loglevel,
                "-y",
                "-loop",
                "1",
                "-i",
                task.output_path,
                "-i",
                silence_audio_path(),
                "-t",
                f"{task.duration:.2f}",
            ]
            command.extend(self._preset("frame", DEFAULT_FRAME_PRESET))
            command.append(word_video_path)

            self._run_command(command)

            if os.path.exists(task.output_path):
                self._safe_remove(task.output_path)

            word_video_files.append(word_video_path)

        concat_list_path = os.path.join(tmp_dir, f"concat_word_{sentence_number}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as handle:
            for video_file in word_video_files:
                handle.write(f"file '{video_file}'\n")

        sentence_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_number}.mp4")
        concat_command = [
            self._executable,
            "-loglevel",
            self._loglevel,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
        ]
        concat_command.extend(self._preset("concat", DEFAULT_CONCAT_PRESET))
        concat_command.append(sentence_video_path)

        try:
            self._run_command(concat_command)
        finally:
            self._safe_remove(concat_list_path)
            if cleanup:
                for video_file in word_video_files:
                    self._safe_remove(video_file)

        audio_temp_path = os.path.join(tmp_dir, f"sentence_audio_{sentence_number}.wav")
        audio_seg.export(audio_temp_path, format="wav")
        merged_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_number}_merged.mp4")

        merge_command = [
            self._executable,
            "-loglevel",
            self._loglevel,
            "-y",
            "-i",
            sentence_video_path,
            "-i",
            audio_temp_path,
        ]
        merge_command.extend(self._preset("merge", DEFAULT_MERGE_PRESET))
        merge_command.append(merged_video_path)

        try:
            self._run_command(merge_command)
        finally:
            self._safe_remove(audio_temp_path)
            if cleanup:
                self._safe_remove(sentence_video_path)

        final_video_path = os.path.join(
            tmp_dir, f"sentence_slide_{sentence_number}_final.mp4"
        )

        if frame_batch.pad_duration > 0:
            pad_command = [
                self._executable,
                "-loglevel",
                self._loglevel,
                "-y",
                "-i",
                merged_video_path,
                "-vf",
                f"tpad=stop_mode=clone:stop_duration={frame_batch.pad_duration:.2f}",
                "-af",
                f"apad=pad_dur={frame_batch.pad_duration:.2f}",
            ]
            pad_command.extend(self._preset("pad", ()))
            pad_command.append(final_video_path)

            try:
                self._run_command(pad_command)
            finally:
                if cleanup:
                    self._safe_remove(merged_video_path)
        else:
            final_video_path = merged_video_path

        return final_video_path

    def _run_command(self, command: Sequence[str]) -> None:
        logger.debug(
            "Executing FFmpeg command", extra={"event": "video.render.ffmpeg", "cmd": command}
        )
        self._run_external(command)

    def _preset(self, name: str, fallback: Sequence[str]) -> list[str]:
        preset = self._presets.get(name)
        if preset is None:
            return list(fallback)
        if isinstance(preset, str):
            return [preset]
        return [str(part) for part in preset]

    @staticmethod
    def _normalise_presets(
        presets: Mapping[str, Iterable[str] | str]
    ) -> MutableMapping[str, Iterable[str] | str]:
        normalised: MutableMapping[str, Iterable[str] | str] = {}
        for key, value in presets.items():
            if not key:
                continue
            normalised[str(key)] = value
        return normalised

    @staticmethod
    def _safe_remove(path: str) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            return
        except OSError as exc:  # pragma: no cover - best effort cleanup
            logger.debug(
                "Failed to remove temporary file %s: %s",
                path,
                exc,
                extra={"event": "video.render.cleanup"},
            )

    def _build_header_info(
        self,
        block: str,
        sentence_number: int,
        options: VideoRenderOptions,
    ) -> str:
        total_sentences = options.total_sentences or 0
        header_tokens = block.split("\n")[0].split(" - ")
        target_lang = header_tokens[0].strip() if header_tokens else ""
        progress_percentage = (
            (sentence_number / total_sentences) * 100 if total_sentences else 0
        )
        remaining_time_str = self._estimate_remaining_time(sentence_number, options)
        tempo = options.tempo if options.tempo is not None else 1.0
        voice_lines = list(options.voice_lines)
        if not voice_lines and options.voice_name:
            voice_lines.append(f"Voice: {options.voice_name}")
        voice_block = "".join(f"{line}\n" for line in voice_lines)
        return (
            f"Book: {options.book_title} | Author: {options.book_author}\n"
            f"Source Language: {options.input_language} | Target: {target_lang} | Speed: {tempo}\n"
            f"{voice_block}"
            f"Sentence: {sentence_number}/{total_sentences or '?'} | Progress: {progress_percentage:.2f}% | Remaining: {remaining_time_str}"
        )

    def _estimate_remaining_time(
        self, sentence_number: int, options: VideoRenderOptions
    ) -> str:
        counts = options.cumulative_word_counts
        total_words = options.total_word_count
        speed = options.macos_reading_speed
        if (
            not counts
            or total_words is None
            or speed in (None, 0)
            or sentence_number - 1 >= len(counts)
        ):
            return "00:00:00"

        words_processed = counts[sentence_number - 1]
        remaining_words = max(0, total_words - words_processed)
        est_seconds = int(remaining_words * 60 / speed)
        hours = est_seconds // 3600
        minutes = (est_seconds % 3600) // 60
        seconds = est_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


__all__ = ["FFmpegVideoRenderer"]
