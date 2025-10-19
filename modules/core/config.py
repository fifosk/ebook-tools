from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from pydub import AudioSegment

from .. import config_manager as cfg
from ..config_manager import RuntimeContext
from .. import translation_engine
from ..llm_client import LLMClient, create_client
from ..epub_parser import (
    DEFAULT_EXTEND_SPLIT_WITH_COMMA_SEMICOLON,
    DEFAULT_MAX_WORDS,
)


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
    tempo: float = 1.0
    macos_reading_speed: int = 100
    sync_ratio: float = 0.9
    word_highlighting: bool = True
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

        translation_engine.configure_default_client(
            model=self.ollama_model, api_url=self.ollama_url, debug=self.debug
        )
        self.translation_client = create_client(
            model=self.ollama_model, api_url=self.ollama_url, debug=self.debug
        )
        ffmpeg_path = self.ffmpeg_path or self.context.ffmpeg_path
        if ffmpeg_path:
            AudioSegment.converter = ffmpeg_path


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

    ollama_model = str(
        _select_value("ollama_model", config, overrides, cfg.DEFAULT_MODEL)
        or cfg.DEFAULT_MODEL
    )
    ollama_url_default = context.ollama_url
    ollama_url = str(
        _select_value("ollama_url", config, overrides, ollama_url_default)
        or ollama_url_default
    )
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
        tempo=tempo,
        macos_reading_speed=macos_reading_speed,
        sync_ratio=sync_ratio,
        word_highlighting=word_highlighting,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        ffmpeg_path=ffmpeg_path,
        thread_count=thread_count,
        queue_size=queue_size,
        pipeline_enabled=pipeline_enabled,
    )
