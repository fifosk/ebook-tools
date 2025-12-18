from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from pydub import AudioSegment

from .. import config_manager as cfg
from ..audio.backends import get_default_backend_name
from ..config.loader import get_rendering_config
from ..config_manager import RuntimeContext
from .. import llm_client_manager, translation_engine
from ..llm_client import LLMClient, create_client
from ..epub_parser import (
    DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    DEFAULT_MAX_WORDS,
)
from ..video.slides import SlideRenderOptions


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _coerce_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_optional_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


@dataclass(slots=True)
class PipelineConfig:
    """Container describing all runtime options for the ebook pipeline."""

    context: RuntimeContext
    working_dir: Path
    output_dir: Optional[Path]
    tmp_dir: Path
    books_dir: Path
    default_working_relative: Path = field(default_factory=lambda: cfg.DEFAULT_WORKING_RELATIVE)
    derived_runtime_dirname: str = field(default_factory=lambda: cfg.DERIVED_RUNTIME_DIRNAME)
    derived_refined_filename_template: str = field(
        default_factory=lambda: cfg.DERIVED_REFINED_FILENAME_TEMPLATE
    )
    ollama_model: str = field(default_factory=lambda: cfg.DEFAULT_MODEL)
    ollama_url: str = field(default_factory=lambda: cfg.DEFAULT_OLLAMA_URL)
    llm_source: str = field(default_factory=cfg.get_llm_source)
    local_ollama_url: str = field(default_factory=cfg.get_local_ollama_url)
    cloud_ollama_url: str = field(default_factory=cfg.get_cloud_ollama_url)
    ffmpeg_path: Optional[str] = None
    thread_count: int = field(default_factory=cfg.get_thread_count)
    queue_size: int = field(default_factory=cfg.get_queue_size)
    pipeline_enabled: bool = field(default_factory=cfg.is_pipeline_mode)
    max_words: int = field(default=DEFAULT_MAX_WORDS)
    split_on_comma_semicolon: bool = field(
        default=DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON
    )
    debug: bool = False
    generate_audio: bool = True
    audio_mode: str = "1"
    selected_voice: str = "gTTS"
    voice_overrides: Mapping[str, str] = field(default_factory=dict)
    tts_backend: str = field(default_factory=get_default_backend_name)
    tts_executable_path: Optional[str] = None
    say_path: Optional[str] = None
    audio_api_base_url: Optional[str] = None
    audio_api_timeout_seconds: Optional[float] = None
    audio_api_poll_interval_seconds: Optional[float] = None
    tempo: float = 1.0
    macos_reading_speed: int = 100
    sync_ratio: float = 0.9
    word_highlighting: bool = True
    highlight_granularity: str = "word"
    char_weighted_highlighting_default: bool = False
    char_weighted_punctuation_boost: bool = False
    forced_alignment_enabled: bool = False
    forced_alignment_smoothing: float | str = "monotonic_cubic"
    alignment_backend: Optional[str] = None
    alignment_model: Optional[str] = None
    alignment_model_overrides: Optional[Mapping[str, str]] = None
    slide_parallelism: str = "off"
    slide_parallel_workers: Optional[int] = None
    prefer_pillow_simd: bool = False
    slide_render_benchmark: bool = False
    slide_template: Optional[str] = "default"
    video_backend: str = "ffmpeg"
    video_backend_settings: Mapping[str, Mapping[str, object]] = field(
        default_factory=dict
    )
    image_api_base_url: Optional[str] = field(
        default_factory=lambda: (os.environ.get("EBOOK_IMAGE_API_BASE_URL") or "").strip() or None
    )
    image_api_timeout_seconds: float = field(
        default_factory=lambda: _coerce_float(os.environ.get("EBOOK_IMAGE_API_TIMEOUT_SECONDS"), 600.0)
    )
    image_concurrency: int = field(
        default_factory=lambda: max(1, _coerce_int(os.environ.get("EBOOK_IMAGE_CONCURRENCY"), 4))
    )
    image_width: int = 512
    image_height: int = 512
    image_steps: int = 24
    image_cfg_scale: float = 7.0
    image_sampler_name: Optional[str] = None
    image_prompt_context_sentences: int = 2
    image_seed_with_previous_image: bool = False
    ollama_api_key: Optional[str] = None
    translation_client: LLMClient = field(init=False, repr=False)

    def resolved_working_dir(self) -> Path:
        """Return the working directory, falling back to defaults when unset."""

        return self.working_dir

    def resolved_output_dir(self) -> Optional[Path]:
        """Return the configured ebook output directory as a :class:`Path`."""

        return self.output_dir

    def resolved_tmp_dir(self) -> Optional[Path]:
        """Return the configured temporary directory as a :class:`Path`."""

        return self.tmp_dir

    def resolved_books_dir(self) -> Optional[Path]:
        """Return the configured books directory as a :class:`Path`."""

        return self.books_dir

    def ensure_runtime_dir(self) -> Path:
        """Ensure the runtime artifact directory exists and return it."""

        runtime_dir = self.resolved_working_dir() / self.derived_runtime_dirname
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir

    def apply_runtime_settings(self) -> None:
        """Propagate configuration to dependent subsystems."""

        llm_client_manager.configure_default_client(
            model=self.ollama_model,
            api_url=self.ollama_url,
            debug=self.debug,
            api_key=self.ollama_api_key,
            llm_source=self.llm_source,
            local_api_url=self.local_ollama_url,
            cloud_api_url=self.cloud_ollama_url,
            cloud_api_key=self.ollama_api_key,
        )
        self.translation_client = create_client(
            model=self.ollama_model,
            api_url=self.ollama_url,
            debug=self.debug,
            api_key=self.ollama_api_key,
            llm_source=self.llm_source,
            local_api_url=self.local_ollama_url,
            cloud_api_url=self.cloud_ollama_url,
            cloud_api_key=self.ollama_api_key,
        )
        if self.video_backend:
            os.environ["EBOOK_VIDEO_BACKEND"] = self.video_backend
            get_rendering_config.cache_clear()
        ffmpeg_path = self.ffmpeg_path or self.context.ffmpeg_path
        if ffmpeg_path:
            AudioSegment.converter = ffmpeg_path
        if self.audio_api_base_url:
            os.environ["EBOOK_AUDIO_API_BASE_URL"] = self.audio_api_base_url
        else:
            os.environ.pop("EBOOK_AUDIO_API_BASE_URL", None)
        if self.audio_api_timeout_seconds is not None:
            os.environ["EBOOK_AUDIO_API_TIMEOUT_SECONDS"] = str(
                float(self.audio_api_timeout_seconds)
            )
        else:
            os.environ.pop("EBOOK_AUDIO_API_TIMEOUT_SECONDS", None)
        if self.audio_api_poll_interval_seconds is not None:
            os.environ["EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS"] = str(
                float(self.audio_api_poll_interval_seconds)
            )
        else:
            os.environ.pop("EBOOK_AUDIO_API_POLL_INTERVAL_SECONDS", None)

    def get_slide_render_options(self) -> SlideRenderOptions:
        """Return rendering options used for sentence slide generation."""

        return SlideRenderOptions(
            parallelism=self.slide_parallelism,
            workers=self.slide_parallel_workers,
            prefer_pillow_simd=self.prefer_pillow_simd,
            benchmark_rendering=self.slide_render_benchmark,
        )


def _select_value(
    name: str,
    config: Mapping[str, Any],
    overrides: Mapping[str, Any],
    default: Any,
) -> Any:
    if name in overrides and overrides[name] is not None:
        return overrides[name]
    value = config.get(name)
    if value is None:
        return default
    return value


def build_pipeline_config(
    context: RuntimeContext,
    config: Optional[Mapping[str, Any]] = None,
    overrides: Optional[Mapping[str, Any]] = None,
) -> PipelineConfig:
    """Construct a :class:`PipelineConfig` from configuration sources."""

    config = config or {}
    overrides = overrides or {}

    working_dir = context.working_dir
    output_dir: Optional[Path] = context.output_dir
    tmp_dir = context.tmp_dir
    books_dir = context.books_dir

    max_words = _coerce_int(
        _select_value("max_words", config, overrides, DEFAULT_MAX_WORDS),
        DEFAULT_MAX_WORDS,
    )
    split_on_comma_semicolon = _coerce_bool(
        _select_value(
            "split_on_comma_semicolon",
            config,
            overrides,
            DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
        ),
        DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    )
    debug = _coerce_bool(_select_value("debug", config, overrides, False), False)
    generate_audio = _coerce_bool(
        _select_value("generate_audio", config, overrides, True),
        True,
    )
    audio_mode = str(_select_value("audio_mode", config, overrides, "1") or "1")
    selected_voice = (
        str(_select_value("selected_voice", config, overrides, "gTTS") or "gTTS")
    )
    raw_voice_overrides = _select_value("voice_overrides", config, overrides, {})
    if isinstance(raw_voice_overrides, Mapping):
        voice_overrides = {
            str(key).strip(): str(value).strip()
            for key, value in raw_voice_overrides.items()
            if isinstance(key, str)
            and isinstance(value, str)
            and str(key).strip()
            and str(value).strip()
        }
    else:
        voice_overrides = {}
    default_tts_backend = get_default_backend_name()
    raw_tts_backend = _select_value("tts_backend", config, overrides, default_tts_backend)
    if isinstance(raw_tts_backend, str):
        candidate_tts_backend = raw_tts_backend.strip()
        if not candidate_tts_backend:
            tts_backend = default_tts_backend
        elif candidate_tts_backend.lower() == "auto":
            tts_backend = get_default_backend_name()
        else:
            tts_backend = candidate_tts_backend
    else:
        tts_backend = default_tts_backend
    raw_tts_executable = _normalize_optional_str(
        _select_value("tts_executable_path", config, overrides, None)
    )
    raw_say_path = _normalize_optional_str(
        _select_value("say_path", config, overrides, None)
    )
    tts_executable_path = raw_tts_executable or raw_say_path
    say_path = raw_say_path or tts_executable_path
    audio_api_base_url = _normalize_optional_str(
        _select_value("audio_api_base_url", config, overrides, None)
    )
    raw_audio_api_timeout = _select_value(
        "audio_api_timeout_seconds", config, overrides, None
    )
    if raw_audio_api_timeout is None:
        audio_api_timeout_seconds: Optional[float] = None
    else:
        audio_api_timeout_seconds = max(0.0, _coerce_float(raw_audio_api_timeout, 60.0))
    raw_audio_api_poll = _select_value(
        "audio_api_poll_interval_seconds", config, overrides, None
    )
    if raw_audio_api_poll is None:
        audio_api_poll_interval_seconds: Optional[float] = None
    else:
        audio_api_poll_interval_seconds = max(0.0, _coerce_float(raw_audio_api_poll, 1.0))
    tempo = _coerce_float(_select_value("tempo", config, overrides, 1.0), 1.0)
    macos_reading_speed = _coerce_int(
        _select_value("macos_reading_speed", config, overrides, 100),
        100,
    )
    sync_ratio = _coerce_float(
        _select_value("sync_ratio", config, overrides, 0.9),
        0.9,
    )
    word_highlighting = _coerce_bool(
        _select_value("word_highlighting", config, overrides, True),
        True,
    )
    raw_highlight_granularity = _select_value(
        "highlight_granularity", config, overrides, "word"
    )
    if isinstance(raw_highlight_granularity, str):
        highlight_granularity = raw_highlight_granularity.strip().lower()
    else:
        highlight_granularity = "word"
    if highlight_granularity not in {"word", "char"}:
        highlight_granularity = "word"

    char_weighted_highlighting_default = _coerce_bool(
        _select_value("char_weighted_highlighting_default", config, overrides, False),
        False,
    )
    char_weighted_punctuation_boost = _coerce_bool(
        _select_value("char_weighted_punctuation_boost", config, overrides, False),
        False,
    )

    raw_parallelism = _select_value("slide_parallelism", config, overrides, "off")
    if isinstance(raw_parallelism, str):
        slide_parallelism = raw_parallelism.strip().lower()
    else:
        slide_parallelism = "off"

    raw_parallel_workers = _select_value("slide_parallel_workers", config, overrides, None)
    if raw_parallel_workers is None:
        slide_parallel_workers: Optional[int] = None
    else:
        slide_parallel_workers = max(1, _coerce_int(raw_parallel_workers, 1))

    prefer_pillow_simd = _coerce_bool(
        _select_value("prefer_pillow_simd", config, overrides, False), False
    )
    slide_render_benchmark = _coerce_bool(
        _select_value("slide_render_benchmark", config, overrides, False), False
    )
    raw_template = _select_value("slide_template", config, overrides, "default")
    if isinstance(raw_template, str):
        normalized_template = raw_template.strip()
        slide_template = normalized_template or "default"
    elif raw_template is None:
        slide_template = None
    else:
        slide_template = "default"

    raw_video_backend = _select_value("video_backend", config, overrides, "ffmpeg")
    if isinstance(raw_video_backend, str):
        video_backend = raw_video_backend.strip() or "ffmpeg"
    else:
        video_backend = "ffmpeg"

    raw_video_backend_settings = _select_value(
        "video_backend_settings", config, overrides, {}
    )
    if isinstance(raw_video_backend_settings, Mapping):
        video_backend_settings = {
            str(key): value
            for key, value in raw_video_backend_settings.items()
            if isinstance(key, str) and isinstance(value, Mapping)
        }
    else:
        video_backend_settings = {}

    image_api_base_url = _normalize_optional_str(
        _select_value(
            "image_api_base_url",
            config,
            overrides,
            (os.environ.get("EBOOK_IMAGE_API_BASE_URL") or "").strip() or None,
        )
    )
    image_api_timeout_seconds = max(
        1.0,
        _coerce_float(
            _select_value(
                "image_api_timeout_seconds",
                config,
                overrides,
                os.environ.get("EBOOK_IMAGE_API_TIMEOUT_SECONDS") or 600.0,
            ),
            600.0,
        ),
    )
    image_concurrency = max(
        1,
        _coerce_int(
            _select_value(
                "image_concurrency",
                config,
                overrides,
                os.environ.get("EBOOK_IMAGE_CONCURRENCY") or 4,
            ),
            4,
        ),
    )
    image_width = max(64, _coerce_int(_select_value("image_width", config, overrides, 512), 512))
    image_height = max(64, _coerce_int(_select_value("image_height", config, overrides, 512), 512))
    image_steps = max(1, _coerce_int(_select_value("image_steps", config, overrides, 24), 24))
    image_cfg_scale = max(
        0.0,
        _coerce_float(_select_value("image_cfg_scale", config, overrides, 7.0), 7.0),
    )
    image_sampler_name = _normalize_optional_str(
        _select_value("image_sampler_name", config, overrides, None)
    )
    image_prompt_context_sentences = max(
        0,
        _coerce_int(
            _select_value("image_prompt_context_sentences", config, overrides, 2),
            2,
        ),
    )
    image_prompt_context_sentences = min(image_prompt_context_sentences, 50)
    image_seed_with_previous_image = _coerce_bool(
        _select_value("image_seed_with_previous_image", config, overrides, False),
        False,
    )

    forced_alignment_enabled = _coerce_bool(
        _select_value("forced_alignment_enabled", config, overrides, False), False
    )
    raw_forced_alignment_smoothing = _select_value(
        "forced_alignment_smoothing", config, overrides, "monotonic_cubic"
    )
    if isinstance(raw_forced_alignment_smoothing, str):
        forced_alignment_smoothing = (
            raw_forced_alignment_smoothing.strip().lower() or "monotonic_cubic"
        )
    else:
        try:
            forced_alignment_smoothing = float(raw_forced_alignment_smoothing)
        except (TypeError, ValueError):
            forced_alignment_smoothing = "monotonic_cubic"

    raw_alignment_backend = _select_value("alignment_backend", config, overrides, None)
    if raw_alignment_backend is None:
        raw_alignment_backend = _select_value("forced_alignment_backend", config, overrides, None)
    if isinstance(raw_alignment_backend, str):
        alignment_backend = raw_alignment_backend.strip() or None
    else:
        alignment_backend = None

    raw_alignment_model = _select_value("alignment_model", config, overrides, None)
    if raw_alignment_model is None:
        raw_alignment_model = _select_value("forced_alignment_model", config, overrides, None)
    if isinstance(raw_alignment_model, str):
        alignment_model = raw_alignment_model.strip() or None
    else:
        alignment_model = None

    raw_alignment_overrides = _select_value(
        "alignment_model_overrides", config, overrides, None
    )
    if raw_alignment_overrides is None:
        raw_alignment_overrides = _select_value(
            "forced_alignment_model_overrides", config, overrides, None
        )
    if isinstance(raw_alignment_overrides, Mapping):
        alignment_model_overrides = {
            str(key).strip().lower(): str(value).strip()
            for key, value in raw_alignment_overrides.items()
            if isinstance(key, str) and isinstance(value, str) and str(value).strip()
        } or None
    else:
        alignment_model_overrides = None

    raw_llm_source = _select_value("llm_source", config, overrides, context.llm_source)
    if isinstance(raw_llm_source, str):
        normalized_source = raw_llm_source.strip().lower()
        if normalized_source not in cfg.VALID_LLM_SOURCES:
            normalized_source = cfg.DEFAULT_LLM_SOURCE
    else:
        normalized_source = context.llm_source

    llm_source = normalized_source

    local_ollama_url_default = context.local_ollama_url
    cloud_ollama_url_default = context.cloud_ollama_url

    local_ollama_url = str(
        _select_value("ollama_local_url", config, overrides, local_ollama_url_default)
        or local_ollama_url_default
    )
    cloud_ollama_url = str(
        _select_value("ollama_cloud_url", config, overrides, cloud_ollama_url_default)
        or cloud_ollama_url_default
    )

    ollama_model = str(
        _select_value("ollama_model", config, overrides, cfg.DEFAULT_MODEL)
        or cfg.DEFAULT_MODEL
    )

    if llm_source == "cloud":
        ollama_url_default = cloud_ollama_url or context.ollama_url
    else:
        ollama_url_default = local_ollama_url or context.ollama_url

    ollama_url = str(
        _select_value("ollama_url", config, overrides, ollama_url_default)
        or ollama_url_default
    )
    ollama_api_key: Optional[str] = None
    api_key_override = overrides.get("ollama_api_key")
    if api_key_override:
        ollama_api_key = str(api_key_override)
    else:
        settings = cfg.get_settings()
        secret = settings.ollama_api_key
        ollama_api_key = secret.get_secret_value() if secret is not None else None
    raw_ffmpeg = _select_value(
        "ffmpeg_path", config, overrides, context.ffmpeg_path or cfg.DEFAULT_FFMPEG_PATH
    )
    ffmpeg_path = str(raw_ffmpeg) if raw_ffmpeg else None

    thread_override = overrides.get("thread_count")
    if thread_override is not None:
        thread_count = max(1, _coerce_int(thread_override, context.thread_count))
    else:
        thread_count = context.thread_count

    queue_override = overrides.get("queue_size")
    if queue_override is not None:
        queue_size = max(1, _coerce_int(queue_override, context.queue_size))
    else:
        queue_size = context.queue_size

    pipeline_override = overrides.get("pipeline_mode")
    if pipeline_override is not None:
        pipeline_enabled = _coerce_bool(pipeline_override, context.pipeline_enabled)
    else:
        pipeline_enabled = context.pipeline_enabled

    return PipelineConfig(
        context=context,
        working_dir=Path(working_dir),
        output_dir=Path(output_dir) if output_dir is not None else None,
        tmp_dir=Path(tmp_dir),
        books_dir=Path(books_dir),
        max_words=max_words,
        split_on_comma_semicolon=split_on_comma_semicolon,
        debug=debug,
        generate_audio=generate_audio,
        audio_mode=audio_mode,
        selected_voice=selected_voice,
        voice_overrides=voice_overrides,
        tts_backend=tts_backend,
        tts_executable_path=tts_executable_path,
        say_path=say_path,
        audio_api_base_url=audio_api_base_url,
        audio_api_timeout_seconds=audio_api_timeout_seconds,
        audio_api_poll_interval_seconds=audio_api_poll_interval_seconds,
        tempo=tempo,
        macos_reading_speed=macos_reading_speed,
        sync_ratio=sync_ratio,
        word_highlighting=word_highlighting,
        highlight_granularity=highlight_granularity,
        char_weighted_highlighting_default=char_weighted_highlighting_default,
        char_weighted_punctuation_boost=char_weighted_punctuation_boost,
        forced_alignment_enabled=forced_alignment_enabled,
        forced_alignment_smoothing=forced_alignment_smoothing,
        alignment_backend=alignment_backend,
        alignment_model=alignment_model,
        alignment_model_overrides=alignment_model_overrides,
        slide_parallelism=slide_parallelism,
        slide_parallel_workers=slide_parallel_workers,
        prefer_pillow_simd=prefer_pillow_simd,
        slide_render_benchmark=slide_render_benchmark,
        slide_template=slide_template,
        video_backend=video_backend,
        video_backend_settings=video_backend_settings,
        image_api_base_url=image_api_base_url,
        image_api_timeout_seconds=image_api_timeout_seconds,
        image_concurrency=image_concurrency,
        image_width=image_width,
        image_height=image_height,
        image_steps=image_steps,
        image_cfg_scale=image_cfg_scale,
        image_sampler_name=image_sampler_name,
        image_prompt_context_sentences=image_prompt_context_sentences,
        image_seed_with_previous_image=image_seed_with_previous_image,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        llm_source=llm_source,
        local_ollama_url=local_ollama_url,
        cloud_ollama_url=cloud_ollama_url,
        ffmpeg_path=ffmpeg_path,
        thread_count=thread_count,
        queue_size=queue_size,
        pipeline_enabled=pipeline_enabled,
        ollama_api_key=ollama_api_key,
    )
