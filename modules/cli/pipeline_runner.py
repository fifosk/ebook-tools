"""Helpers that bridge CLI configuration with the ingestion pipeline."""

from __future__ import annotations

import argparse
import os
import sys
import threading
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # pragma: no cover - platform specific
    import resource
except ImportError:  # pragma: no cover - Windows fallback
    resource = None  # type: ignore[assignment]

from .. import config_manager as cfg
from .. import logging_manager as log_mgr
from .. import metadata_manager
from ..audio.backends import get_default_backend_name
from ..core import ingestion
from ..core.config import PipelineConfig, build_pipeline_config
from ..epub_parser import DEFAULT_MAX_WORDS
from ..progress_tracker import ProgressTracker
from ..services.pipeline_service import (
    PipelineInput,
    PipelineRequest,
    PipelineResponse,
    run_pipeline as run_pipeline_service,
)
from ..services.pipeline_types import PipelineMetadata
from ..shared import assets
from . import context

console_info = log_mgr.console_info
console_error = log_mgr.console_error
configure_logging_level = log_mgr.configure_logging_level
resolve_file_path = cfg.resolve_file_path
build_runtime_context = cfg.build_runtime_context
load_configuration = cfg.load_configuration

logger = log_mgr.logger

DEFAULT_MODEL = cfg.DEFAULT_MODEL
DEFAULT_TTS_BACKEND = get_default_backend_name()


def _format_limit_value(value: int) -> str:
    """Return a human readable representation of ``value`` for RLIMIT values."""

    if value < 0:
        return "unlimited"
    if resource is not None:
        infinite = getattr(resource, "RLIM_INFINITY", None)
        if infinite is not None and value == infinite:
            return "unlimited"
    return str(value)


def _resolve_slide_worker_count(
    parallelism: Optional[str], configured_workers: Optional[int], thread_count: int
) -> int:
    """Return the effective slide worker total for the supplied configuration."""

    if not parallelism:
        return 0

    normalized = str(parallelism).strip().lower()
    if normalized in {"off", "none", "disabled"}:
        return 0

    if configured_workers is None:
        return max(0, thread_count)

    with suppress(TypeError, ValueError):
        workers = int(configured_workers)
        return max(0, workers)

    return max(0, thread_count)


def _estimate_required_file_descriptors(
    *,
    thread_count: int,
    slide_workers: int,
    job_workers: int,
    queue_size: int,
) -> int:
    """Estimate the file descriptor requirement for the configured pipeline."""

    workers = max(1, thread_count) + max(0, slide_workers) + max(1, job_workers)
    queue_allowance = max(0, queue_size)
    base_allowance = 128
    per_worker_budget = workers * 16
    queue_budget = queue_allowance * 4
    safety_margin = max(64, workers * 8)
    return max(1024, base_allowance + per_worker_budget + queue_budget + safety_margin)


def _ensure_fd_limit(required: int, *, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Ensure the process soft limit for open files meets ``required`` descriptors."""

    if required <= 0:
        return

    attrs: Dict[str, Any] = {"required": required}
    if attributes:
        attrs.update(attributes)

    if resource is None:
        logger.debug(
            "resource module is unavailable; skipping file descriptor limit enforcement.",
            extra={"event": "system.fd_limits", "attributes": attrs},
        )
        return

    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.debug(
            "Unable to inspect file descriptor limit: %s", exc, extra={"event": "system.fd_limits", "attributes": attrs}
        )
        return

    attrs.update({"soft": soft, "hard": hard})
    logger.info(
        "Checking file descriptor limits",
        extra={"event": "system.fd_limits", "attributes": attrs},
    )
    console_info(
        "Checking file descriptor limits (required=%s, soft=%s, hard=%s)",
        required,
        _format_limit_value(soft),
        _format_limit_value(hard),
    )

    infinite = getattr(resource, "RLIM_INFINITY", None)
    if soft == infinite or soft >= required:
        console_info(
            "File descriptor limits already satisfy requirements (soft=%s, hard=%s).",
            _format_limit_value(soft),
            _format_limit_value(hard),
        )
        return

    new_soft = required
    new_hard = hard
    attempt_raise_hard = False
    if hard != infinite and hard < required:
        new_hard = required
        attempt_raise_hard = True

    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, new_hard))
    except (OSError, ValueError, resource.error) as exc:  # pragma: no cover - platform specific
        logger.warning(
            "Unable to raise file descriptor limit to %s: %s",
            required,
            exc,
            extra={"event": "system.fd_limits", "attributes": attrs},
        )
        if attempt_raise_hard:
            fallback_soft = min(required, hard)
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE, (fallback_soft, hard))
            except Exception as fallback_exc:  # pragma: no cover - defensive guard
                logger.debug(
                    "Fallback attempt to raise soft file descriptor limit failed: %s",
                    fallback_exc,
                    extra={"event": "system.fd_limits", "attributes": attrs},
                )

    try:
        final_soft, final_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    except Exception:  # pragma: no cover - defensive guard
        final_soft, final_hard = soft, hard

    attrs.update({"soft": final_soft, "hard": final_hard})
    logger.info(
        "Resolved file descriptor limits",
        extra={"event": "system.fd_limits", "attributes": attrs},
    )
    console_info(
        "Final file descriptor limits (soft=%s, hard=%s)",
        _format_limit_value(final_soft),
        _format_limit_value(final_hard),
    )


def _ensure_fd_capacity(
    request: PipelineRequest,
    pipeline_config: Optional[PipelineConfig] = None,
) -> None:
    """Ensure the active process can sustain the file descriptors required by the job."""

    runtime_context = request.context
    if runtime_context is None:
        runtime_context = cfg.build_runtime_context(
            request.config, request.environment_overrides
        )

    overrides: Dict[str, Any] = {**request.environment_overrides}
    overrides.update({k: v for k, v in request.pipeline_overrides.items() if v is not None})

    if pipeline_config is None:
        pipeline_config = build_pipeline_config(runtime_context, request.config, overrides=overrides)

    slide_workers = _resolve_slide_worker_count(
        pipeline_config.slide_parallelism,
        pipeline_config.slide_parallel_workers,
        pipeline_config.thread_count,
    )
    settings = cfg.get_settings()
    job_workers = max(1, int(getattr(settings, "job_max_workers", 1) or 1))
    required = _estimate_required_file_descriptors(
        thread_count=pipeline_config.thread_count,
        slide_workers=slide_workers,
        job_workers=job_workers,
        queue_size=pipeline_config.queue_size,
    )

    attributes = {
        "thread_count": pipeline_config.thread_count,
        "queue_size": pipeline_config.queue_size,
        "slide_parallelism": pipeline_config.slide_parallelism,
        "slide_parallel_workers": pipeline_config.slide_parallel_workers,
        "job_max_workers": job_workers,
    }

    _ensure_fd_limit(required, attributes=attributes)


def build_environment_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """Translate CLI arguments into runtime context overrides."""

    return {
        "ebooks_dir": args.ebooks_dir or os.environ.get("EBOOKS_DIR"),
        "working_dir": args.working_dir or os.environ.get("EBOOK_WORKING_DIR"),
        "output_dir": args.output_dir or os.environ.get("EBOOK_OUTPUT_DIR"),
        "tmp_dir": args.tmp_dir or os.environ.get("EBOOK_TMP_DIR"),
        "ffmpeg_path": args.ffmpeg_path or os.environ.get("FFMPEG_PATH"),
        "ollama_url": args.ollama_url or os.environ.get("OLLAMA_URL"),
        "llm_source": args.llm_source or os.environ.get("LLM_SOURCE"),
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
        sentences_per_output_file=config.get("sentences_per_output_file", 1),
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
        include_transliteration=config.get("include_transliteration", True),
        tempo=config.get("tempo", 1.0),
        book_metadata=PipelineMetadata.from_mapping(book_metadata),
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
        or config.get("sentences_per_output_file", 1)
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
    config.setdefault("tts_backend", DEFAULT_TTS_BACKEND)
    config.setdefault("tts_executable_path", None)
    config.setdefault("say_path", config.get("tts_executable_path"))
    config.setdefault("output_html", True)
    config.setdefault("output_pdf", False)
    config.setdefault("generate_video", False)
    config.setdefault("include_transliteration", True)
    config.setdefault("tempo", 1.0)
    config.setdefault("macos_reading_speed", 100)
    config.setdefault("sync_ratio", 0.9)
    config.setdefault("word_highlighting", True)
    config.setdefault("max_words", config.get("max_words", DEFAULT_MAX_WORDS))
    config.setdefault("ollama_model", DEFAULT_MODEL)
    config.setdefault("slide_parallelism", "off")
    config.setdefault("slide_parallel_workers", None)
    config.setdefault("prefer_pillow_simd", False)
    config.setdefault("slide_render_benchmark", False)
    config.setdefault("slide_template", "default")
    config.setdefault("video_backend", "ffmpeg")
    config.setdefault("video_backend_settings", {})

    if getattr(args, "slide_parallelism", None):
        config["slide_parallelism"] = args.slide_parallelism
    if getattr(args, "slide_parallel_workers", None) is not None:
        config["slide_parallel_workers"] = args.slide_parallel_workers
    if getattr(args, "prefer_pillow_simd", False):
        config["prefer_pillow_simd"] = True
    if getattr(args, "benchmark_slide_rendering", False):
        config["slide_render_benchmark"] = True
    if getattr(args, "template", None):
        config["slide_template"] = args.template
    if getattr(args, "video_backend", None):
        config["video_backend"] = args.video_backend
    video_backend_settings = dict(config.get("video_backend_settings") or {})
    backend_key = config.get("video_backend", "ffmpeg")
    backend_overrides = dict(video_backend_settings.get(backend_key, {}))
    if getattr(args, "video_backend_executable", None):
        backend_overrides["executable"] = args.video_backend_executable
    if getattr(args, "video_backend_loglevel", None):
        backend_overrides["loglevel"] = args.video_backend_loglevel
    presets_arg = getattr(args, "video_backend_preset", None)
    if presets_arg:
        presets = dict(backend_overrides.get("presets", {}))
        for raw_entry in presets_arg:
            if not isinstance(raw_entry, str):
                continue
            name, _, value = raw_entry.partition("=")
            name = name.strip()
            if not name:
                continue
            parts = [part.strip() for part in value.split(",") if part.strip()]
            presets[name] = parts
        if presets:
            backend_overrides["presets"] = presets
    if backend_overrides:
        video_backend_settings[backend_key] = backend_overrides
    config["video_backend_settings"] = video_backend_settings
    if getattr(args, "tts_backend", None):
        config["tts_backend"] = args.tts_backend
    if getattr(args, "tts_executable", None):
        config["tts_executable_path"] = args.tts_executable
        config["say_path"] = args.tts_executable
    if getattr(args, "say_path", None):
        config["say_path"] = args.say_path
        config["tts_executable_path"] = args.say_path

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
        pipeline_input.book_metadata = PipelineMetadata.from_mapping(
            {
                "book_title": config.get("book_title"),
                "book_author": config.get("book_author"),
                "book_year": config.get("book_year"),
                "book_summary": config.get("book_summary"),
                "book_cover_file": config.get("book_cover_file"),
            }
        )

    if args.debug:
        config["debug"] = True

    pipeline_overrides = {
        "generate_audio": config.get("generate_audio"),
        "audio_mode": config.get("audio_mode"),
        "selected_voice": config.get("selected_voice"),
        "tts_backend": config.get("tts_backend"),
        "tts_executable_path": config.get("tts_executable_path"),
        "say_path": config.get("say_path"),
        "tempo": config.get("tempo"),
        "macos_reading_speed": config.get("macos_reading_speed"),
        "sync_ratio": config.get("sync_ratio"),
        "word_highlighting": config.get("word_highlighting"),
        "max_words": config.get("max_words"),
        "split_on_comma_semicolon": config.get("split_on_comma_semicolon"),
        "debug": config.get("debug"),
        "ollama_model": config.get("ollama_model"),
        "ollama_url": config.get("ollama_url"),
        "video_backend": config.get("video_backend"),
        "video_backend_settings": config.get("video_backend_settings"),
        "ffmpeg_path": overrides.get("ffmpeg_path") or config.get("ffmpeg_path"),
        "thread_count": config.get("thread_count") or overrides.get("thread_count"),
        "queue_size": config.get("queue_size"),
        "pipeline_mode": config.get("pipeline_mode"),
        "slide_template": config.get("slide_template"),
        "slide_parallelism": config.get("slide_parallelism"),
        "slide_parallel_workers": config.get("slide_parallel_workers"),
        "prefer_pillow_simd": config.get("prefer_pillow_simd"),
        "slide_render_benchmark": config.get("slide_render_benchmark"),
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
        config.setdefault("tts_backend", DEFAULT_TTS_BACKEND)
        config.setdefault("tts_executable_path", None)
        config.setdefault("say_path", config.get("tts_executable_path"))
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
        config.setdefault("slide_parallelism", "off")
        config.setdefault("slide_parallel_workers", None)
        config.setdefault("prefer_pillow_simd", False)
        config.setdefault("slide_render_benchmark", False)
        config.setdefault("slide_template", "default")
        config.setdefault("video_backend", "ffmpeg")
        config.setdefault("video_backend_settings", {})

        if getattr(args, "template", None):
            config["slide_template"] = args.template
        if getattr(args, "video_backend", None):
            config["video_backend"] = args.video_backend
        video_backend_settings = dict(config.get("video_backend_settings") or {})
        backend_key = config.get("video_backend", "ffmpeg")
        backend_overrides = dict(video_backend_settings.get(backend_key, {}))
        if getattr(args, "video_backend_executable", None):
            backend_overrides["executable"] = args.video_backend_executable
        if getattr(args, "video_backend_loglevel", None):
            backend_overrides["loglevel"] = args.video_backend_loglevel
        presets_arg = getattr(args, "video_backend_preset", None)
        if presets_arg:
            presets = dict(backend_overrides.get("presets", {}))
            for raw_entry in presets_arg:
                if not isinstance(raw_entry, str):
                    continue
                name, _, value = raw_entry.partition("=")
                name = name.strip()
                if not name:
                    continue
                parts = [part.strip() for part in value.split(",") if part.strip()]
                presets[name] = parts
            if presets:
                backend_overrides["presets"] = presets
        if backend_overrides:
            video_backend_settings[backend_key] = backend_overrides
        config["video_backend_settings"] = video_backend_settings

        if config.get("auto_metadata", True) and pipeline_input.input_file:
            metadata_manager.populate_config_metadata(
                config, pipeline_input.input_file
            )
            pipeline_input.book_metadata = PipelineMetadata.from_mapping(
                {
                    "book_title": config.get("book_title"),
                    "book_author": config.get("book_author"),
                    "book_year": config.get("book_year"),
                    "book_summary": config.get("book_summary"),
                    "book_cover_file": config.get("book_cover_file"),
                }
            )
        else:
            if not pipeline_input.book_metadata.values:
                pipeline_input.book_metadata = PipelineMetadata()

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
            "tts_backend": config.get("tts_backend"),
            "tts_executable_path": config.get("tts_executable_path"),
            "say_path": config.get("say_path"),
            "tempo": config.get("tempo"),
            "macos_reading_speed": config.get("macos_reading_speed", 100),
            "sync_ratio": config.get("sync_ratio", 0.9),
            "word_highlighting": config.get("word_highlighting", True),
            "max_words": config.get("max_words", DEFAULT_MAX_WORDS),
            "split_on_comma_semicolon": config.get("split_on_comma_semicolon"),
            "debug": config.get("debug"),
            "ollama_model": config.get("ollama_model", DEFAULT_MODEL),
            "ollama_url": config.get("ollama_url"),
            "video_backend": config.get("video_backend"),
            "video_backend_settings": config.get("video_backend_settings"),
            "ffmpeg_path": overrides.get("ffmpeg_path") or config.get("ffmpeg_path"),
            "thread_count": config.get("thread_count") or overrides.get("thread_count"),
            "queue_size": config.get("queue_size"),
            "pipeline_mode": config.get("pipeline_mode"),
            "slide_parallelism": config.get("slide_parallelism"),
            "slide_parallel_workers": config.get("slide_parallel_workers"),
            "prefer_pillow_simd": config.get("prefer_pillow_simd"),
            "slide_render_benchmark": config.get("slide_render_benchmark"),
            "slide_template": config.get("slide_template"),
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
        _ensure_fd_capacity(request, pipeline_config)
        response = run_pipeline_service(request)
        if not response.success:
            return None
        return response

    request, config = prepare_non_interactive_run(
        args,
        progress_tracker=progress_tracker,
        stop_event=stop_event,
    )
    _ensure_fd_capacity(request)
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
