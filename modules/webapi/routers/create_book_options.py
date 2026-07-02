"""Creation option defaults shared by Web and Apple generated-book clients."""

from __future__ import annotations

from typing import Any

from modules.epub_parser import normalize_sentence_splitter_mode, sentence_splitter_version_for_mode
from modules.images.style_templates import resolve_image_style_template
from modules.language_constants import LANGUAGE_CODES

from ..schemas.create_book import (
    BookCreationDefaults,
    BookCreationGeneratedSourceDefaults,
    BookCreationOptionsResponse,
    BookCreationPipelineDefaults,
    BookCreationSentenceBounds,
    BookCreationSentenceSplitterCapabilities,
    BookCreationSentenceSplitterMode,
    BookCreationSubtitleDefaults,
    BookCreationYoutubeDubDefaults,
)

_DEFAULT_SENTENCE_COUNT = 30
_MIN_SENTENCE_COUNT = 1
_MAX_SENTENCE_COUNT = 500
_DEFAULT_INPUT_LANGUAGE = "English"
_DEFAULT_OUTPUT_LANGUAGE = "Arabic"
_DEFAULT_AUTHOR = "Me"
_DEFAULT_VOICE = "gTTS"
_DEFAULT_SUBTITLE_WORKER_COUNT = 10
_DEFAULT_SUBTITLE_BATCH_SIZE = 20
_DEFAULT_SUBTITLE_ASS_EMPHASIS_SCALE = 1.3
_DEFAULT_YOUTUBE_ORIGINAL_MIX_PERCENT = 5.0
_DEFAULT_YOUTUBE_TARGET_HEIGHT = 480
_SUPPORTED_BOOK_LANGUAGES = tuple(LANGUAGE_CODES.keys())
_SUPPORTED_BOOK_VOICES = ["gTTS", "macOS", "edge-tts"]


def _coerce_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_float(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_bool(value: object, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return fallback


def _coerce_text(value: object, fallback: str) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return fallback


def _config_value(config: dict[str, Any], *keys: str) -> object:
    for key in keys:
        value = config.get(key)
        if value is not None:
            return value
    return None


def _clamp_int(value: int, minimum: int, maximum: int | None = None) -> int:
    resolved = max(minimum, value)
    if maximum is not None:
        resolved = min(maximum, resolved)
    return resolved


def _build_subtitle_defaults(config: dict[str, Any]) -> BookCreationSubtitleDefaults:
    return BookCreationSubtitleDefaults(
        worker_count=_clamp_int(
            _coerce_int(
                _config_value(config, "subtitle_worker_count", "worker_count"),
                _DEFAULT_SUBTITLE_WORKER_COUNT,
            ),
            1,
            32,
        ),
        batch_size=_clamp_int(
            _coerce_int(
                _config_value(config, "subtitle_batch_size", "batch_size"),
                _DEFAULT_SUBTITLE_BATCH_SIZE,
            ),
            1,
            500,
        ),
        translation_batch_size=_clamp_int(
            _coerce_int(
                _config_value(config, "subtitle_translation_batch_size", "translation_batch_size"),
                10,
            ),
            1,
            50,
        ),
        ass_font_size=_clamp_int(
            _coerce_int(_config_value(config, "subtitle_ass_font_size", "ass_font_size"), 56),
            12,
            120,
        ),
        ass_emphasis_scale=max(
            1.0,
            min(
                2.5,
                _coerce_float(
                    _config_value(config, "subtitle_ass_emphasis_scale", "ass_emphasis_scale"),
                    _DEFAULT_SUBTITLE_ASS_EMPHASIS_SCALE,
                ),
            ),
        ),
    )


def _build_youtube_dub_defaults(config: dict[str, Any]) -> BookCreationYoutubeDubDefaults:
    target_height = _coerce_int(
        _config_value(config, "youtube_dub_target_height", "youtube_target_height", "target_height"),
        _DEFAULT_YOUTUBE_TARGET_HEIGHT,
    )
    if target_height not in {320, 480, 720}:
        target_height = _DEFAULT_YOUTUBE_TARGET_HEIGHT
    return BookCreationYoutubeDubDefaults(
        original_mix_percent=max(
            0.0,
            min(
                100.0,
                _coerce_float(
                    _config_value(
                        config,
                        "youtube_dub_original_mix_percent",
                        "youtube_original_mix_percent",
                        "original_mix_percent",
                    ),
                    _DEFAULT_YOUTUBE_ORIGINAL_MIX_PERCENT,
                ),
            ),
        ),
        flush_sentences=_clamp_int(
            _coerce_int(
                _config_value(config, "youtube_dub_flush_sentences", "youtube_flush_sentences", "flush_sentences"),
                10,
            ),
            1,
            200,
        ),
        translation_batch_size=_clamp_int(
            _coerce_int(
                _config_value(
                    config,
                    "youtube_dub_translation_batch_size",
                    "youtube_translation_batch_size",
                    "translation_batch_size",
                ),
                10,
            ),
            1,
            50,
        ),
        split_batches=_coerce_bool(
            _config_value(config, "youtube_dub_split_batches", "youtube_split_batches", "split_batches"),
            True,
        ),
        stitch_batches=_coerce_bool(
            _config_value(config, "youtube_dub_stitch_batches", "youtube_stitch_batches", "stitch_batches"),
            True,
        ),
        target_height=target_height,
        preserve_aspect_ratio=_coerce_bool(
            _config_value(
                config,
                "youtube_dub_preserve_aspect_ratio",
                "youtube_preserve_aspect_ratio",
                "preserve_aspect_ratio",
            ),
            True,
        ),
    )


def _normalize_image_prompt_pipeline(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"visual_canon", "visual-canon", "canon"}:
            return "visual_canon"
    return "prompt_plan"


def _build_generated_source_defaults(config: dict[str, Any]) -> BookCreationGeneratedSourceDefaults:
    style_value = _config_value(config, "image_style_template")
    style_template = resolve_image_style_template(style_value or "wireframe").template_id
    return BookCreationGeneratedSourceDefaults(
        add_images=_coerce_bool(config.get("add_images"), False),
        image_prompt_pipeline=_normalize_image_prompt_pipeline(config.get("image_prompt_pipeline")),
        image_style_template=style_template,
        image_prompt_context_sentences=min(
            50,
            max(0, _coerce_int(config.get("image_prompt_context_sentences"), 0)),
        ),
        image_width=str(max(64, _coerce_int(config.get("image_width"), 256))),
        image_height=str(max(64, _coerce_int(config.get("image_height"), 256))),
    )


def _normalize_creation_target_languages(config: dict[str, Any]) -> list[str]:
    values = config.get("target_languages")
    candidates: list[object]
    if isinstance(values, list):
        candidates = list(values)
    elif isinstance(values, str):
        candidates = values.split(",")
    else:
        candidates = [config.get("output_language")]

    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        value = candidate.strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)

    return result or [_DEFAULT_OUTPUT_LANGUAGE]


def _build_creation_options(config: dict[str, Any]) -> BookCreationOptionsResponse:
    selected_voice = _coerce_text(config.get("selected_voice"), _DEFAULT_VOICE)
    input_language = _coerce_text(config.get("input_language"), _DEFAULT_INPUT_LANGUAGE)
    target_languages = _normalize_creation_target_languages(config)
    output_language = target_languages[0]

    return BookCreationOptionsResponse(
        sentence_bounds=BookCreationSentenceBounds(
            min=_MIN_SENTENCE_COUNT,
            max=_MAX_SENTENCE_COUNT,
            default=_DEFAULT_SENTENCE_COUNT,
        ),
        defaults=BookCreationDefaults(
            author=_DEFAULT_AUTHOR,
            input_language=input_language,
            output_language=output_language,
            target_languages=target_languages,
            output_languages=target_languages,
            voice=selected_voice,
        ),
        pipeline_defaults=BookCreationPipelineDefaults(
            sentences_per_output_file=max(1, _coerce_int(config.get("sentences_per_output_file"), 10)),
            stitch_full=_coerce_bool(config.get("stitch_full"), False),
            audio_mode=_coerce_text(config.get("audio_mode"), "4"),
            audio_bitrate_kbps=max(32, _coerce_int(config.get("audio_bitrate_kbps"), 96)),
            written_mode=_coerce_text(config.get("written_mode"), "4"),
            selected_voice=selected_voice,
            generate_audio=_coerce_bool(config.get("generate_audio"), True),
            output_html=_coerce_bool(config.get("output_html"), False),
            output_pdf=_coerce_bool(config.get("output_pdf"), False),
            include_transliteration=_coerce_bool(config.get("include_transliteration"), True),
            translation_provider=_coerce_text(config.get("translation_provider"), "llm"),
            translation_batch_size=max(1, _coerce_int(config.get("translation_batch_size"), 10)),
            transliteration_mode=_coerce_text(config.get("transliteration_mode"), "default"),
            sentence_splitter_mode=normalize_sentence_splitter_mode(
                _coerce_text(config.get("sentence_splitter_mode"), "regex")
            ),
            enable_lookup_cache=_coerce_bool(config.get("enable_lookup_cache"), True),
            lookup_cache_batch_size=max(1, _coerce_int(config.get("lookup_cache_batch_size"), 10)),
            tempo=max(0.1, _coerce_float(config.get("tempo"), 1.0)),
        ),
        sentence_splitter_capabilities=BookCreationSentenceSplitterCapabilities(
            default_mode="regex",
            supported_modes=[
                BookCreationSentenceSplitterMode(
                    id="regex",
                    label="Regex (stable)",
                    cache_version=sentence_splitter_version_for_mode("regex"),
                    stable=True,
                ),
                BookCreationSentenceSplitterMode(
                    id="modern",
                    label="Modern (opt-in)",
                    cache_version=sentence_splitter_version_for_mode("modern"),
                    stable=False,
                ),
            ],
            comparison_metric_fields=[
                "normalized_text_preserved",
                "contiguous_text_preserved",
                "matched_sentence_count",
                "unmatched_sentence_count",
                "unmatched_sentence_indices",
                "skipped_text_character_count",
                "trailing_text_character_count",
                "tiny_fragment_count",
                "max_words_per_segment",
            ],
        ),
        generated_source_defaults=_build_generated_source_defaults(config),
        subtitle_defaults=_build_subtitle_defaults(config),
        youtube_dub_defaults=_build_youtube_dub_defaults(config),
        supported_input_languages=list(_SUPPORTED_BOOK_LANGUAGES),
        supported_output_languages=list(_SUPPORTED_BOOK_LANGUAGES),
        supported_voices=list(dict.fromkeys([selected_voice, *_SUPPORTED_BOOK_VOICES])),
    )
