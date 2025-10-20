"""Slide rendering orchestration built on modular layout and templates."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from PIL import Image
from pydub import AudioSegment

from modules import logging_manager as log_mgr
from modules.audio.highlight import (
    HighlightEvent,
    _build_events_from_metadata,
    _build_legacy_highlight_events,
    _get_audio_metadata,
    coalesce_highlight_events,
)
from modules.audio.tts import active_tmp_dir, silence_audio_path

from .layout_engine import GlyphMetricsCache, LayoutEngine
from .slide_core import Slide
from .slide_image_renderer import SlideImageRenderer
from .slide_image_utils import (
    deserialize_cover_image,
    log_simd_preference,
    serialize_cover_image,
)
from .template_manager import TemplateManager, _parse_color

logger = log_mgr.logger


@dataclass(slots=True)
class SlideRenderOptions:
    """Options controlling how slide frames are rendered."""

    parallelism: str = "off"
    workers: Optional[int] = None
    prefer_pillow_simd: bool = False
    benchmark_rendering: bool = False


class SlideRenderProfiler:
    """Collects timing/counter statistics for slide rendering operations."""

    def __init__(self) -> None:
        self._timers: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._counters: Dict[str, int] = defaultdict(int)

    @contextmanager
    def time_block(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            count, total = self._timers[name]
            self._timers[name] = (count + 1, total + elapsed)

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    def merge(self, other: "SlideRenderProfiler") -> None:
        for key, (count, total) in other._timers.items():
            cur_count, cur_total = self._timers[key]
            self._timers[key] = (cur_count + count, cur_total + total)
        for key, value in other._counters.items():
            self._counters[key] += value

    def log_summary(self, sentence_index: int) -> None:
        if not self._timers and not self._counters:
            return
        logger.debug(
            "Slide rendering benchmark for sentence %s:",
            sentence_index,
            extra={"event": "video.slide.benchmark", "console_suppress": True},
        )
        for name, (count, total) in sorted(
            self._timers.items(), key=lambda item: item[1][1], reverse=True
        ):
            avg = total / count if count else 0.0
            logger.debug(
                "  %s -> total %.4fs across %s calls (avg %.6fs)",
                name,
                total,
                count,
                avg,
                extra={"event": f"video.slide.benchmark.{name}", "console_suppress": True},
            )
        for name, value in self._counters.items():
            logger.debug(
                "  %s -> %s",
                name,
                value,
                extra={
                    "event": f"video.slide.benchmark.counter.{name}",
                    "console_suppress": True,
                },
            )


@dataclass(slots=True)
class SlideFrameTask:
    index: int
    block: str
    duration: float
    original_highlight_index: int
    translation_highlight_index: int
    transliteration_highlight_index: int
    original_char_range: Optional[Tuple[int, int]]
    translation_char_range: Optional[Tuple[int, int]]
    transliteration_char_range: Optional[Tuple[int, int]]
    slide_size: Sequence[int]
    initial_font_size: int
    default_font_path: str
    bg_color: Sequence[int]
    cover_image_bytes: Optional[bytes]
    header_info: str
    highlight_granularity: str
    output_path: str
    template_name: Optional[str]


_GLYPH_CACHE = GlyphMetricsCache()


class SlideRenderer:
    """Render :class:`Slide` instances using JSON-defined templates."""

    def __init__(
        self,
        *,
        template_manager: Optional[TemplateManager] = None,
        layout_engine: Optional[LayoutEngine] = None,
    ) -> None:
        self._template_manager = template_manager or TemplateManager()
        self._layout_engine = layout_engine or LayoutEngine(_GLYPH_CACHE)
        self._image_renderer = SlideImageRenderer(
            template_manager=self._template_manager,
            layout_engine=self._layout_engine,
        )

    # Rendering helpers -------------------------------------------------
    def render_sentence_slide_image(
        self,
        slide: Slide,
        *,
        original_highlight_word_index: Optional[int] = None,
        translation_highlight_word_index: Optional[int] = None,
        transliteration_highlight_word_index: Optional[int] = None,
        original_highlight_char_range: Optional[Tuple[int, int]] = None,
        translation_highlight_char_range: Optional[Tuple[int, int]] = None,
        transliteration_highlight_char_range: Optional[Tuple[int, int]] = None,
        highlight_granularity: str = "word",
        slide_size: Sequence[int] = (1280, 720),
        initial_font_size: int = 50,
        default_font_path: str = "Arial.ttf",
        bg_color: Optional[Sequence[int]] = None,
        cover_img: Optional[Image.Image] = None,
        header_info: str = "",
        template_name: Optional[str] = None,
        profiler: Optional[SlideRenderProfiler] = None,
    ) -> Image.Image:
        return self._image_renderer.render_sentence_slide_image(
            slide,
            original_highlight_word_index=original_highlight_word_index,
            translation_highlight_word_index=translation_highlight_word_index,
            transliteration_highlight_word_index=transliteration_highlight_word_index,
            original_highlight_char_range=original_highlight_char_range,
            translation_highlight_char_range=translation_highlight_char_range,
            transliteration_highlight_char_range=transliteration_highlight_char_range,
            highlight_granularity=highlight_granularity,
            slide_size=slide_size,
            initial_font_size=initial_font_size,
            default_font_path=default_font_path,
            bg_color=bg_color,
            cover_img=cover_img,
            header_info=header_info,
            template_name=template_name,
            profiler=profiler,
        )

    # Video composition -------------------------------------------------
    def _render_slide_frame_local(
        self, task: SlideFrameTask, profiler: Optional[SlideRenderProfiler]
    ) -> str:
        cover_image = deserialize_cover_image(task.cover_image_bytes)
        try:
            slide = Slide.from_sentence_block(
                task.block,
                template_name=task.template_name,
            )
            image = self.render_sentence_slide_image(
                slide,
                original_highlight_word_index=task.original_highlight_index,
                translation_highlight_word_index=task.translation_highlight_index,
                transliteration_highlight_word_index=task.transliteration_highlight_index,
                original_highlight_char_range=task.original_char_range,
                translation_highlight_char_range=task.translation_char_range,
                transliteration_highlight_char_range=task.transliteration_char_range,
                highlight_granularity=task.highlight_granularity,
                slide_size=task.slide_size,
                initial_font_size=task.initial_font_size,
                default_font_path=task.default_font_path,
                bg_color=task.bg_color,
                cover_img=cover_image,
                header_info=task.header_info,
                template_name=task.template_name,
                profiler=profiler,
            )
            image.save(task.output_path)
            image.close()
        finally:
            if cover_image is not None:
                cover_image.close()
        return task.output_path

    def _render_slide_frame(self, task: SlideFrameTask) -> str:
        return self._render_slide_frame_local(task, None)

    def build_sentence_video(
        self,
        slide: Slide,
        audio_seg: AudioSegment,
        sentence_index: int,
        *,
        sync_ratio: float,
        word_highlighting: bool,
        highlight_events: Optional[Sequence[HighlightEvent]] = None,
        highlight_granularity: str = "word",
        slide_size: Sequence[int] = (1280, 720),
        initial_font_size: int = 50,
        default_font_path: Optional[str] = None,
        bg_color: Sequence[int] = (0, 0, 0),
        cover_img: Optional[Image.Image] = None,
        header_info: str = "",
        render_options: Optional[SlideRenderOptions] = None,
    ) -> str:
        if default_font_path is None:
            default_font_path = self.get_default_font_path()

        options = render_options or SlideRenderOptions()
        parallelism = (options.parallelism or "off").lower()
        if parallelism not in {"off", "auto", "thread", "process", "none"}:
            parallelism = "off"
        if parallelism == "none":
            parallelism = "off"
        log_simd_preference(options.prefer_pillow_simd)

        profiler: Optional[SlideRenderProfiler] = None
        if options.benchmark_rendering:
            if parallelism == "off":
                profiler = SlideRenderProfiler()
            else:
                logger.warning(
                    "Slide rendering benchmark requested but parallel backend '%s' is active; timing data will not be collected.",
                    parallelism,
                    extra={"event": "video.slide.benchmark.skipped"},
                )

        block = slide.metadata.get("raw_block", slide.title)
        raw_lines = block.split("\n")
        content = "\n".join(raw_lines[1:]).strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if len(lines) >= 3:
            original_seg = lines[0]
            translation_seg = lines[1]
            transliteration_seg = lines[2]
        elif len(lines) >= 2:
            original_seg = lines[0]
            translation_seg = " ".join(lines[1:])
            transliteration_seg = ""
        else:
            original_seg = translation_seg = content
            transliteration_seg = ""

        original_words = original_seg.split()
        num_original_words = len(original_words)

        header_line = raw_lines[0] if raw_lines else ""
        if "Chinese" in header_line or "Japanese" in header_line:
            translation_units: Sequence[str] = list(translation_seg)
        else:
            translation_units = translation_seg.split() or [translation_seg]
        num_translation_words = len(translation_units)

        transliteration_words = transliteration_seg.split()
        num_translit_words = len(transliteration_words)

        audio_duration = audio_seg.duration_seconds
        audio_metadata = _get_audio_metadata(audio_seg)

        if highlight_events is None:
            if not word_highlighting:
                events: Sequence[HighlightEvent] = [
                    HighlightEvent(
                        duration=max(audio_duration * sync_ratio, 0.0),
                        original_index=num_original_words,
                        translation_index=num_translation_words,
                        transliteration_index=num_translit_words,
                    )
                ]
            else:
                generated: List[HighlightEvent] = []
                if audio_metadata and audio_metadata.parts:
                    generated = _build_events_from_metadata(
                        audio_metadata,
                        sync_ratio,
                        num_original_words,
                        num_translation_words,
                        num_translit_words,
                    )
                if not generated:
                    generated = _build_legacy_highlight_events(
                        audio_duration,
                        sync_ratio,
                        original_words,
                        translation_units,
                        transliteration_words,
                    )
                events = generated
        else:
            events = list(highlight_events)

        timeline_events = [event for event in events if event.duration > 0]
        if not timeline_events:
            timeline_events = [
                HighlightEvent(
                    duration=max(audio_duration * sync_ratio, 0.0),
                    original_index=num_original_words,
                    translation_index=num_translation_words,
                    transliteration_index=num_translit_words,
                )
            ]

        has_char_steps = any(
            event.step is not None
            and event.step.char_index_start is not None
            and event.step.char_index_end is not None
            for event in timeline_events
        )
        effective_granularity = (
            "char"
            if word_highlighting and highlight_granularity == "char" and has_char_steps
            else "word"
        )

        segments = coalesce_highlight_events(timeline_events)
        video_duration = sum(segment.duration for segment in segments)
        pad_duration = max(0.0, audio_duration - video_duration)

        tmp_dir = active_tmp_dir()
        os.makedirs(tmp_dir, exist_ok=True)
        slide_size_tuple = tuple(int(value) for value in slide_size)
        if bg_color is None:
            bg_color_tuple: Tuple[int, ...] = ()
        else:
            parsed_bg = _parse_color(bg_color, default=(0, 0, 0))
            bg_color_tuple = tuple(parsed_bg)
        cover_bytes = serialize_cover_image(cover_img)

        frame_tasks: List[SlideFrameTask] = []
        for idx, segment in enumerate(segments):
            original_highlight_index = (
                min(segment.original_index, num_original_words)
                if word_highlighting
                else num_original_words
            )
            translation_highlight_index = (
                min(segment.translation_index, num_translation_words)
                if word_highlighting
                else num_translation_words
            )
            transliteration_highlight_index = (
                min(segment.transliteration_index, num_translit_words)
                if word_highlighting
                else num_translit_words
            )
            original_char_range = (
                segment.original_char_range if effective_granularity == "char" else None
            )
            translation_char_range = (
                segment.translation_char_range if effective_granularity == "char" else None
            )
            transliteration_char_range = (
                segment.transliteration_char_range if effective_granularity == "char" else None
            )
            img_path = os.path.join(tmp_dir, f"word_slide_{sentence_index}_{idx}.png")
            frame_tasks.append(
                SlideFrameTask(
                    index=idx,
                    block=block,
                    duration=segment.duration,
                    original_highlight_index=original_highlight_index,
                    translation_highlight_index=translation_highlight_index,
                    transliteration_highlight_index=transliteration_highlight_index,
                    original_char_range=original_char_range,
                    translation_char_range=translation_char_range,
                    transliteration_char_range=transliteration_char_range,
                    slide_size=slide_size_tuple,
                    initial_font_size=initial_font_size,
                    default_font_path=default_font_path,
                    bg_color=bg_color_tuple,
                    cover_image_bytes=cover_bytes,
                    header_info=header_info,
                    highlight_granularity=effective_granularity,
                    output_path=img_path,
                    template_name=slide.template_name,
                )
            )

        render_backend = parallelism
        if len(frame_tasks) <= 1:
            render_backend = "off"
        elif render_backend == "auto":
            worker_hint = options.workers or (os.cpu_count() or 1)
            render_backend = "process" if worker_hint and worker_hint > 1 else "thread"

        self._render_frames(
            frame_tasks,
            parallelism=render_backend,
            options=options,
            profiler=profiler,
        )

        word_video_files: List[str] = []
        for task in frame_tasks:
            video_path = os.path.join(tmp_dir, f"word_slide_{sentence_index}_{task.index}.mp4")
            cmd = [
                "ffmpeg",
                "-loglevel",
                "quiet",
                "-y",
                "-loop",
                "1",
                "-i",
                task.output_path,
                "-i",
                silence_audio_path(),
                "-c:v",
                "libx264",
                "-t",
                f"{task.duration:.2f}",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                "format=yuv420p",
                "-an",
                video_path,
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as exc:
                logger.error("FFmpeg error on word slide %s_%s: %s", sentence_index, task.index, exc)
            finally:
                if os.path.exists(task.output_path):
                    os.remove(task.output_path)
            word_video_files.append(video_path)

        concat_list_path = os.path.join(tmp_dir, f"concat_word_{sentence_index}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as handle:
            for video_file in word_video_files:
                handle.write(f"file '{video_file}'\n")

        sentence_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_index}.mp4")
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
            sentence_video_path,
        ]
        try:
            result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.error("FFmpeg concat error: %s", result.stderr.decode())
                raise subprocess.CalledProcessError(result.returncode, cmd_concat)
        except subprocess.CalledProcessError as exc:
            logger.error("Error concatenating word slides for sentence %s: %s", sentence_index, exc)
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

        for vf in word_video_files:
            if os.path.exists(vf):
                os.remove(vf)

        audio_temp_path = os.path.join(tmp_dir, f"sentence_audio_{sentence_index}.wav")
        audio_seg.export(audio_temp_path, format="wav")
        merged_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_index}_merged.mp4")

        cmd_merge = [
            "ffmpeg",
            "-loglevel",
            "quiet",
            "-y",
            "-i",
            sentence_video_path,
            "-i",
            audio_temp_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            merged_video_path,
        ]
        try:
            subprocess.run(cmd_merge, check=True)
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg error merging audio for sentence %s: %s", sentence_index, exc)
        finally:
            if os.path.exists(audio_temp_path):
                os.remove(audio_temp_path)
            if os.path.exists(sentence_video_path):
                os.remove(sentence_video_path)

        final_video_path = os.path.join(tmp_dir, f"sentence_slide_{sentence_index}_final.mp4")
        if pad_duration > 0:
            cmd_tpad = [
                "ffmpeg",
                "-loglevel",
                "quiet",
                "-y",
                "-i",
                merged_video_path,
                "-vf",
                f"tpad=stop_mode=clone:stop_duration={pad_duration:.2f}",
                "-af",
                f"apad=pad_dur={pad_duration:.2f}",
                final_video_path,
            ]
            try:
                subprocess.run(cmd_tpad, check=True)
            except subprocess.CalledProcessError as exc:
                logger.error("FFmpeg error applying padding for sentence %s: %s", sentence_index, exc)
            finally:
                if os.path.exists(merged_video_path):
                    os.remove(merged_video_path)
        else:
            final_video_path = merged_video_path

        if profiler is not None:
            profiler.log_summary(sentence_index)

        return final_video_path

    # Support utilities -------------------------------------------------
    def _render_frames(
        self,
        frame_tasks: Sequence[SlideFrameTask],
        *,
        parallelism: str,
        options: SlideRenderOptions,
        profiler: Optional[SlideRenderProfiler],
    ) -> None:
        if not frame_tasks:
            return

        if parallelism == "off" or len(frame_tasks) == 1:
            for task in frame_tasks:
                self._render_slide_frame_local(task, profiler)
            return

        workers = options.workers
        if workers is None or workers < 1:
            workers = os.cpu_count() or 1

        executor_cls = ThreadPoolExecutor if parallelism == "thread" else ProcessPoolExecutor
        init_kwargs = {"max_workers": workers}

        with executor_cls(**init_kwargs) as executor:
            futures = {
                executor.submit(self._render_slide_frame, task): task.index
                for task in frame_tasks
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error(
                        "Slide rendering worker failed for sentence frame %s: %s",
                        futures[future],
                        exc,
                    )

    def get_default_font_path(self) -> str:
        if sys.platform == "darwin":
            for path in [
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            ]:
                if os.path.exists(path):
                    return path
        elif sys.platform == "win32":
            path = r"C:\\Windows\\Fonts\\arialuni.ttf"
            if os.path.exists(path):
                return path
        else:
            for path in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            ]:
                if os.path.exists(path):
                    return path
        return "Arial.ttf"

__all__ = [
    "SlideRenderer",
    "SlideRenderOptions",
    "SlideRenderProfiler",
]
