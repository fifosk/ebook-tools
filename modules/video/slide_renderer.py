"""Slide rendering orchestration built on modular layout and templates."""

from __future__ import annotations

import os
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
from modules.audio.highlight import HighlightEvent, coalesce_highlight_events, timeline
from modules.audio.tts import active_tmp_dir

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


@dataclass(slots=True)
class SentenceFrameBatch:
    """Container describing rendered slide frames for a single sentence."""

    frame_tasks: Sequence[SlideFrameTask]
    pad_duration: float
    profiler: Optional[SlideRenderProfiler]


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

    def prepare_sentence_frames(
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
    ) -> SentenceFrameBatch:
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

        audio_duration = audio_seg.duration_seconds
        timeline_options = timeline.TimelineBuildOptions(
            sync_ratio=sync_ratio,
            word_highlighting=word_highlighting,
            highlight_granularity=highlight_granularity,
            events=highlight_events,
        )
        timeline_result = timeline.build(block, audio_seg, timeline_options)

        timeline_events = timeline_result.events
        effective_granularity = timeline_result.effective_granularity
        num_original_words = timeline_result.original_word_count
        num_translation_words = timeline_result.translation_word_count
        num_translit_words = timeline_result.transliteration_word_count

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

        if profiler is not None:
            profiler.log_summary(sentence_index)

        return SentenceFrameBatch(
            frame_tasks=tuple(frame_tasks),
            pad_duration=pad_duration,
            profiler=profiler,
        )

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
    "SentenceFrameBatch",
    "SlideRenderer",
    "SlideRenderOptions",
    "SlideRenderProfiler",
]
