"""Media export helpers for the rendering pipeline."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from PIL import Image
from pydub import AudioSegment

from modules import audio_video_generator as av_gen
from modules import config_manager as cfg
from modules import output_formatter
from modules.audio.tts import get_voice_display_name
from modules.config.loader import get_rendering_config
from modules.core.config import DEFAULT_AUDIO_BITRATE_KBPS
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.core.rendering.timeline import (
    SentenceTimingSpec,
    build_separate_track_timings,
    build_word_events,
    scale_timing_to_audio_duration,
)
from modules.render.context import RenderBatchContext
from modules.render.output_writer import DeferredBatchWriter
from modules.video.api import VideoService
from modules.video.slides import SlideRenderOptions
from modules.audio.highlight import _get_audio_metadata
from modules.text import split_highlight_tokens


def _parse_sentence_block(block: str) -> tuple[str, str, str, str]:
    lines = block.split("\n")
    header = lines[0].strip() if lines else ""
    body_lines = [line.strip() for line in lines[1:] if line.strip()]

    original = body_lines[0] if body_lines else ""
    translation = body_lines[1] if len(body_lines) > 1 else ""
    transliteration = body_lines[2] if len(body_lines) > 2 else ""

    return header, original, translation, transliteration


def _split_translation_units(header: str, translation: str) -> List[str]:
    if not translation:
        return []
    tokens = split_highlight_tokens(translation)
    if tokens:
        return tokens
    return [translation]


def _tokenize_words(text: str) -> List[str]:
    return split_highlight_tokens(text)


def _segment_duration(segment: Optional[AudioSegment]) -> float:
    """Return ``segment.duration_seconds`` as a positive float."""

    if segment is None:
        return 0.0
    duration = getattr(segment, "duration_seconds", 0.0)
    try:
        return max(float(duration), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _is_estimated_policy(policy: str) -> bool:
    return policy.strip().lower().startswith("estimated")


def _resolve_highlighting_policy(
    sentence_specs: Sequence[SentenceTimingSpec],
) -> Optional[str]:
    fallback: Optional[str] = None
    for spec in sentence_specs:
        for candidate in (spec.policy, spec.original_policy):
            if not isinstance(candidate, str):
                continue
            normalized = candidate.strip()
            if not normalized:
                continue
            if _is_estimated_policy(normalized):
                return normalized
            if fallback is None:
                fallback = normalized
    return fallback


_COMPACT_SENTENCE_DROP_KEYS = {
    "charWeighted",
    "highlighting_policy",
    "highlighting_summary",
    "highlight_granularity",
    "imagePath",
    "origWords",
    "originalPauseAfterMs",
    "originalPauseBeforeMs",
    "originalWordTokens",
    "original_highlighting_policy",
    "original_highlighting_summary",
    "original_pause_after_ms",
    "original_pause_before_ms",
    "original_word_tokens",
    "pauseAfterMs",
    "pauseBeforeMs",
    "pause_after_ms",
    "pause_before_ms",
    "slide_duration",
    "slideDuration",
    "timing",
    "timeline",
    "timingTracks",
    "transWords",
    "word_timing",
    "word_tokens",
}


def _compact_sentence_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    compact: Dict[str, Any] = {}
    for key, value in payload.items():
        if key in _COMPACT_SENTENCE_DROP_KEYS:
            continue
        compact[key] = value
    return compact


def serialize_sentence_chunk(
    sentence_meta: Mapping[str, Any],
    *,
    include_timing_tracks: bool = True,
    include_top_level_text: bool = True,
) -> Dict[str, Any]:
    """
    Normalise sentence-level metadata for chunk payloads.

    Builds a backward-compatible structure that keeps sentence timing while
    exposing detailed word-level tracks when available.
    """

    if not isinstance(sentence_meta, Mapping):
        raise TypeError("sentence_meta must be a mapping")

    sentence_id = (
        sentence_meta.get("id")
        or sentence_meta.get("sentence_id")
        or sentence_meta.get("sentence_number")
        or ""
    )
    sentence_id_str = str(sentence_id) if sentence_id is not None else ""
    if not sentence_id_str:
        sentence_number_val = sentence_meta.get("sentence_number")
        if sentence_number_val is not None:
            sentence_id_str = str(sentence_number_val)

    text_value = sentence_meta.get("text")
    text_str = str(text_value) if text_value is not None else ""

    try:
        t0 = round(float(sentence_meta.get("t0", 0.0)), 3)
    except (TypeError, ValueError):
        t0 = 0.0

    duration_candidate = sentence_meta.get("t1", sentence_meta.get("duration", 0.0))
    try:
        t1 = round(float(duration_candidate), 3)
    except (TypeError, ValueError):
        t1 = t0
    if t1 < t0:
        t1 = t0

    timing_tracks_payload: Dict[str, Any] = {}
    if include_timing_tracks:
        word_events = build_word_events(sentence_meta)
        if word_events:
            timing_tracks_payload["translation"] = word_events
        original_tokens = sentence_meta.get("original_word_tokens")
        if original_tokens is None:
            original_tokens = sentence_meta.get("originalWordTokens")
        if isinstance(original_tokens, Sequence):
            original_events = build_word_events({"word_tokens": original_tokens})
            if original_events:
                timing_tracks_payload["original"] = original_events

    chunk_entry: Dict[str, Any] = {
        "sentence_id": sentence_id_str,
        "t0": t0,
        "t1": t1,
        "timing": {"t0": t0, "t1": t1},
    }
    if include_top_level_text:
        chunk_entry["text"] = text_str
    if timing_tracks_payload:
        chunk_entry["timingTracks"] = timing_tracks_payload

    policy_candidate = sentence_meta.get("highlighting_policy") or sentence_meta.get(
        "alignment_policy"
    )
    normalized_policy: Optional[str] = None
    if isinstance(policy_candidate, str):
        normalized_policy = policy_candidate.strip() or None
    summary_candidate = sentence_meta.get("highlighting_summary")
    summary_payload: Dict[str, Any] = {}
    if isinstance(summary_candidate, Mapping):
        raw_policy = summary_candidate.get("policy")
        if isinstance(raw_policy, str) and raw_policy.strip():
            summary_payload["policy"] = raw_policy.strip()
        elif normalized_policy:
            summary_payload["policy"] = normalized_policy
        tempo_value = summary_candidate.get("tempo")
        try:
            summary_payload["tempo"] = float(tempo_value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
        tokens_value = summary_candidate.get("tokens")
        if tokens_value is None:
            tokens_value = summary_candidate.get("token_count")
        token_count: Optional[int] = None
        try:
            token_count = int(tokens_value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            token_count = None
        if token_count is not None:
            summary_payload["tokens"] = token_count
            summary_payload.setdefault("token_count", token_count)
        duration_value = summary_candidate.get("duration") or summary_candidate.get("t1")
        try:
            summary_payload["duration"] = round(float(duration_value), 6)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
        source_value = summary_candidate.get("source") or summary_candidate.get("alignment_source")
        if isinstance(source_value, str) and source_value.strip():
            summary_payload["source"] = source_value.strip()
        method_value = summary_candidate.get("method") or summary_candidate.get("strategy")
        if isinstance(method_value, str) and method_value.strip():
            summary_payload["method"] = method_value.strip()
        char_weighted_flag = summary_candidate.get("char_weighted")
        if isinstance(char_weighted_flag, bool):
            summary_payload["char_weighted"] = char_weighted_flag
        elif isinstance(char_weighted_flag, str):
            normalized = char_weighted_flag.strip().lower()
            if normalized in {"1", "true", "yes"}:
                summary_payload["char_weighted"] = True
        punctuation_flag = summary_candidate.get("punctuation_weighting")
        if isinstance(punctuation_flag, bool):
            summary_payload["punctuation_weighting"] = punctuation_flag
        alignment_model = summary_candidate.get("alignment_model")
        if isinstance(alignment_model, str) and alignment_model.strip():
            summary_payload["alignment_model"] = alignment_model.strip()
    if normalized_policy:
        chunk_entry["highlighting_policy"] = normalized_policy
        summary_payload.setdefault("policy", normalized_policy)
    if summary_payload:
        chunk_entry["highlighting_summary"] = summary_payload

    return chunk_entry


def _slice_audio_region(audio: AudioSegment, *, start: float, duration: float) -> AudioSegment:
    """Return a subsection of ``audio`` starting at ``start`` seconds with ``duration`` seconds."""

    if not isinstance(audio, AudioSegment):
        return AudioSegment.silent(duration=0)
    if duration <= 0:
        return audio[:0]
    total_ms = len(audio)
    start_ms = int(round(max(start, 0.0) * 1000))
    if start_ms >= total_ms:
        return audio[:0]
    end_ms = int(round((max(start, 0.0) + duration) * 1000))
    end_ms = max(start_ms, min(end_ms, total_ms))
    if end_ms <= start_ms:
        return audio[:0]
    return audio[start_ms:end_ms]


def _derive_audio_tracks_from_segments(
    segments: Sequence[AudioSegment],
) -> Dict[str, List[AudioSegment]]:
    """Split sentence-level audio into original and translation tracks when possible."""

    if not segments:
        return {}

    original_segments: List[AudioSegment] = []
    translation_segments: List[AudioSegment] = []
    has_original_audio = False
    has_translation_audio = False

    for segment in segments:
        if not isinstance(segment, AudioSegment):
            empty = AudioSegment.silent(duration=0)
            original_segments.append(empty)
            translation_segments.append(empty)
            continue

        metadata = _get_audio_metadata(segment)
        base_empty = segment[:0]
        original_part = base_empty
        translation_part = base_empty

        if metadata is None or not getattr(metadata, "parts", None):
            translation_part += segment
            if len(segment) > 0:
                has_translation_audio = True
        else:
            for part in metadata.parts:
                duration = getattr(part, "duration", 0.0) or 0.0
                if duration <= 0:
                    continue
                start_offset = getattr(part, "start_offset", 0.0) or 0.0
                if part.kind == "original":
                    slice_audio = _slice_audio_region(segment, start=start_offset, duration=duration)
                    if len(slice_audio) > 0:
                        has_original_audio = True
                    original_part += slice_audio
                elif part.kind == "translation":
                    slice_audio = _slice_audio_region(segment, start=start_offset, duration=duration)
                    if len(slice_audio) > 0:
                        has_translation_audio = True
                    translation_part += slice_audio

        original_segments.append(original_part)
        translation_segments.append(translation_part)

    tracks: Dict[str, List[AudioSegment]] = {}
    if has_original_audio:
        tracks["orig"] = original_segments
    if has_translation_audio:
        tracks["translation"] = translation_segments
    return tracks


@dataclass(frozen=True)
class BatchExportContext:
    """Static context shared across batch exports."""

    base_dir: str
    base_name: str
    cover_image: Optional[Image.Image]
    book_author: str
    book_title: str
    global_cumulative_word_counts: Sequence[int]
    total_book_words: int
    macos_reading_speed: float
    input_language: str
    total_sentences: int
    tempo: float
    sync_ratio: float
    word_highlighting: bool
    highlight_granularity: str
    selected_voice: str
    voice_name: str
    slide_render_options: Optional[SlideRenderOptions]
    template_name: Optional[str]
    video_backend: str
    video_backend_settings: Mapping[str, Mapping[str, object]]
    audio_bitrate_kbps: Optional[int] = None


@dataclass(frozen=True)
class BatchExportRequest:
    """User-controlled options and dynamic content for a batch export."""

    start_sentence: int
    end_sentence: int
    written_blocks: Sequence[str]
    target_language: str
    output_html: bool
    output_pdf: bool
    generate_audio: bool
    audio_segments: Sequence[AudioSegment]
    generate_video: bool
    video_blocks: Sequence[str]
    sentence_metadata: Sequence[Mapping[str, Any]] = field(default_factory=list)
    voice_metadata: Mapping[str, Mapping[str, Sequence[str]]] = field(
        default_factory=dict
    )
    audio_tracks: Mapping[str, Sequence[AudioSegment]] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchExportResult:
    """Description of artifacts generated for a single batch export."""

    chunk_id: str
    start_sentence: int
    end_sentence: int
    range_fragment: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    sentences: List[Dict[str, object]] = field(default_factory=list)
    audio_tracks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    timing_tracks: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    highlighting_policy: Optional[str] = None
    timing_version: str = "2"
    timing_validation: Dict[str, Any] = field(default_factory=dict)


class BatchExporter:
    """Persist batch outputs for written, audio, and optional video artifacts."""

    def __init__(self, context: BatchExportContext) -> None:
        self._context = context
        self._video_service = VideoService(
            backend=context.video_backend,
            backend_settings=context.video_backend_settings,
        )

    def _resolve_audio_bitrate(self) -> Optional[str]:
        raw_value = getattr(self._context, "audio_bitrate_kbps", None)
        if raw_value is None:
            bitrate_kbps = DEFAULT_AUDIO_BITRATE_KBPS
        else:
            try:
                bitrate_kbps = int(raw_value)
            except (TypeError, ValueError):
                bitrate_kbps = DEFAULT_AUDIO_BITRATE_KBPS
        if bitrate_kbps <= 0:
            bitrate_kbps = DEFAULT_AUDIO_BITRATE_KBPS
        return f"{bitrate_kbps}k"

    def _job_relative_path(self, candidate: Path) -> str:
        path_obj = candidate
        base_dir_path = Path(self._context.base_dir)
        for parent in base_dir_path.parents:
            if parent.name.lower() == "media" and parent.parent != parent:
                try:
                    relative = path_obj.relative_to(parent.parent)
                except ValueError:
                    continue
                if relative.as_posix():
                    return relative.as_posix()
        job_root_candidates = list(base_dir_path.parents[:4])
        job_root_candidates.append(base_dir_path)
        for root_candidate in job_root_candidates:
            try:
                relative = path_obj.relative_to(root_candidate)
            except ValueError:
                continue
            if relative.as_posix():
                return relative.as_posix()
        return path_obj.name

    def _build_sentence_metadata(
        self,
        *,
        block: str,
        audio_segment: Optional[AudioSegment],
        sentence_number: int,
        original_phase_duration: float = 0.0,
        translation_phase_duration: float = 0.0,
        gap_before_translation: float = 0.0,
        gap_after_translation: float = 0.0,
        word_meta: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, object]:
        header, original_text, translation_text, transliteration_text = _parse_sentence_block(block)

        if audio_segment is not None:
            audio_duration = float(audio_segment.duration_seconds)
        else:
            audio_duration = 0.0

        original_tokens = _tokenize_words(original_text)
        translation_units = _split_translation_units(header, translation_text)
        transliteration_tokens = _tokenize_words(transliteration_text)
        if audio_duration <= 0:
            fallback_tokens = max(
                len(original_tokens),
                len(translation_units),
                len(transliteration_tokens),
            )
            if fallback_tokens > 0:
                audio_duration = fallback_tokens * 0.35
            else:
                audio_duration = 0.5

        payload: Dict[str, object] = {
            "sentence_number": sentence_number,
            "original": {
                "text": original_text,
                "tokens": original_tokens,
            },
            "total_duration": audio_duration,
        }

        if translation_text:
            payload["translation"] = {
                "text": translation_text,
                "tokens": translation_units,
            }
        else:
            payload["translation"] = None

        if transliteration_text:
            payload["transliteration"] = {
                "text": transliteration_text,
                "tokens": transliteration_tokens,
            }
        else:
            payload["transliteration"] = None

        payload["counts"] = {
            "original": len(original_tokens),
            "translation": len(translation_units),
            "transliteration": len(transliteration_tokens),
        }

        phase_payload: Dict[str, float] = {}
        if original_phase_duration > 0:
            phase_payload["original"] = float(original_phase_duration)
        if gap_before_translation > 0:
            phase_payload["gap"] = float(gap_before_translation)
        if translation_phase_duration > 0:
            phase_payload["translation"] = float(translation_phase_duration)
        if gap_after_translation > 0:
            phase_payload["tail"] = float(gap_after_translation)
        if phase_payload:
            payload["phase_durations"] = phase_payload

        meta_payload: Dict[str, Any]
        if isinstance(word_meta, Mapping):
            meta_payload = dict(word_meta)
        else:
            meta_payload = {}
        meta_payload.setdefault("sentence_number", sentence_number)
        meta_payload.setdefault(
            "id",
            str(meta_payload.get("sentence_number", sentence_number)),
        )
        meta_payload.setdefault("t0", meta_payload.get("t0", 0.0))
        if "word_tokens" not in meta_payload or not meta_payload.get("word_tokens"):
            tokens_attr = getattr(audio_segment, "word_tokens", None) if audio_segment is not None else None
            if isinstance(tokens_attr, Sequence):
                meta_payload["word_tokens"] = list(tokens_attr)
        if "t1" not in meta_payload:
            meta_payload["t1"] = round(audio_duration, 6)
        else:
            try:
                meta_payload["t1"] = round(float(meta_payload["t1"]), 6)
            except (TypeError, ValueError):
                meta_payload["t1"] = round(audio_duration, 6)
        def _coerce_pause_ms(raw_value: object) -> int:
            try:
                return int(round(float(raw_value)))
            except (TypeError, ValueError):
                return 0

        pause_before_source = meta_payload.get("pauseBeforeMs")
        if pause_before_source is None:
            pause_before_source = meta_payload.get("pause_before_ms")
        pause_after_source = meta_payload.get("pauseAfterMs")
        if pause_after_source is None:
            pause_after_source = meta_payload.get("pause_after_ms")
        pause_before_ms = max(_coerce_pause_ms(pause_before_source), 0)
        pause_after_ms = max(_coerce_pause_ms(pause_after_source), 0)
        meta_payload["pauseBeforeMs"] = pause_before_ms
        meta_payload["pauseAfterMs"] = pause_after_ms

        chunk_entry = serialize_sentence_chunk(meta_payload, include_timing_tracks=False, include_top_level_text=False)
        payload["sentence_id"] = chunk_entry["sentence_id"]
        payload["t0"] = chunk_entry["t0"]
        payload["t1"] = chunk_entry["t1"]
        payload["word_tokens"] = list(meta_payload.get("word_tokens") or [])
        original_tokens = meta_payload.get("original_word_tokens")
        if original_tokens is None:
            original_tokens = meta_payload.get("originalWordTokens")
        if isinstance(original_tokens, Sequence):
            payload["originalWordTokens"] = list(original_tokens)
        highlighting_summary = chunk_entry.get("highlighting_summary", {})
        if not isinstance(highlighting_summary, Mapping):
            highlighting_summary = {}
        policy_value = chunk_entry.get("highlighting_policy") or highlighting_summary.get("policy")
        payload["word_timing"] = {
            "policy": policy_value,
            "source": highlighting_summary.get("source"),
            "char_weighted_enabled": bool(highlighting_summary.get("char_weighted")),
            "punctuation_boost": bool(highlighting_summary.get("punctuation_weighting")),
        }
        payload["pauseBeforeMs"] = pause_before_ms
        payload["pauseAfterMs"] = pause_after_ms

        original_summary = meta_payload.get("original_highlighting_summary")
        if isinstance(original_summary, Mapping):
            payload["original_highlighting_summary"] = dict(original_summary)
        original_policy = meta_payload.get("original_highlighting_policy")
        if isinstance(original_policy, str) and original_policy.strip():
            payload["original_highlighting_policy"] = original_policy.strip()

        original_pause_before_source = meta_payload.get("originalPauseBeforeMs")
        if original_pause_before_source is None:
            original_pause_before_source = meta_payload.get("original_pause_before_ms")
        original_pause_after_source = meta_payload.get("originalPauseAfterMs")
        if original_pause_after_source is None:
            original_pause_after_source = meta_payload.get("original_pause_after_ms")
        if original_pause_before_source is not None or original_pause_after_source is not None:
            original_pause_before_ms = max(_coerce_pause_ms(original_pause_before_source), 0)
            original_pause_after_ms = max(_coerce_pause_ms(original_pause_after_source), 0)
            payload["originalPauseBeforeMs"] = original_pause_before_ms
            payload["originalPauseAfterMs"] = original_pause_after_ms

        # Prefer any previously-computed gate metadata but fall back to the
        # synthesized timing block so downstream code has consistent values.
        start_gate_value = meta_payload.get("start_gate")
        if start_gate_value is None:
            start_gate_value = meta_payload.get("startGate")
        end_gate_value = meta_payload.get("end_gate")
        if end_gate_value is None:
            end_gate_value = meta_payload.get("endGate")
        if start_gate_value is None or end_gate_value is None:
            timing_block = chunk_entry.get("timing")
            if isinstance(timing_block, Mapping):
                if start_gate_value is None:
                    start_gate_value = timing_block.get("t0")
                if end_gate_value is None:
                    end_gate_value = timing_block.get("t1")

        if isinstance(start_gate_value, (int, float)) and isinstance(end_gate_value, (int, float)):
            payload.setdefault("startGate", float(start_gate_value))
            payload.setdefault("endGate", float(end_gate_value))

        original_start_gate = meta_payload.get("original_start_gate")
        if original_start_gate is None:
            original_start_gate = meta_payload.get("originalStartGate")
        original_end_gate = meta_payload.get("original_end_gate")
        if original_end_gate is None:
            original_end_gate = meta_payload.get("originalEndGate")
        if isinstance(original_start_gate, (int, float)) and isinstance(original_end_gate, (int, float)):
            payload.setdefault("originalStartGate", float(original_start_gate))
            payload.setdefault("originalEndGate", float(original_end_gate))

        image_payload = meta_payload.get("image")
        if isinstance(image_payload, Mapping):
            payload["image"] = dict(image_payload)
        image_path = meta_payload.get("image_path") or meta_payload.get("imagePath")
        if isinstance(image_path, str) and image_path.strip():
            payload["imagePath"] = image_path.strip()

        return payload

    @staticmethod
    def _format_voice_lines(
        metadata: Mapping[str, Mapping[str, Sequence[str]]]
    ) -> list[str]:
        lines: list[str] = []
        role_labels = {
            "source": "Source Voice",
            "translation": "Translation Voice",
        }
        for role, languages in metadata.items():
            if not isinstance(languages, Mapping):
                continue
            label = role_labels.get(role)
            if label is None:
                continue
            for language, voices in languages.items():
                if isinstance(voices, Sequence):
                    ordered = list(dict.fromkeys(str(voice).strip() for voice in voices if voice))
                    if not ordered:
                        continue
                    voice_list = ", ".join(ordered)
                else:
                    voice_list = str(voices).strip()
                    if not voice_list:
                        continue
                suffix = f" ({language})" if language else ""
                lines.append(f"{label}{suffix}: {voice_list}")
        return lines

    def export(self, request: BatchExportRequest) -> BatchExportResult:
        """Write batch outputs and return a description of created files."""

        range_fragment = output_formatter.format_sentence_range(
            request.start_sentence,
            request.end_sentence,
            self._context.total_sentences,
        )

        chunk_id = f"{range_fragment}_{self._context.base_name}"

        voice_lines = self._format_voice_lines(request.voice_metadata)
        voice_display = "\n".join(voice_lines) if voice_lines else self._context.voice_name

        config = get_rendering_config()
        runtime_context = cfg.get_runtime_context(None)
        ramdisk_enabled = config.ramdisk_enabled
        ramdisk_path = config.ramdisk_path
        if runtime_context is not None:
            candidate = Path(ramdisk_path)
            if not candidate.is_absolute():
                candidate = runtime_context.tmp_dir / candidate
            ramdisk_path = str(candidate)
            ramdisk_enabled = ramdisk_enabled and runtime_context.is_tmp_ramdisk
        manifest_context = {
            "batch_id": f"{range_fragment}_{self._context.base_name}",
            "ramdisk_enabled": ramdisk_enabled,
            "ramdisk_path": ramdisk_path,
        }
        media_context = {
            "text": {"range_fragment": range_fragment},
            "audio": {"range_fragment": range_fragment},
            "video": {
                "range_fragment": range_fragment,
                "voice_name": voice_display,
                "voice_lines": voice_lines,
            },
        }
        batch_context = RenderBatchContext(manifest=manifest_context, media=media_context)
        writer = DeferredBatchWriter(Path(self._context.base_dir), batch_context)

        artifacts: Dict[str, str] = {}
        audio_segments: List[AudioSegment] = (
            list(request.audio_segments) if request.generate_audio else []
        )
        audio_track_segments: Dict[str, List[AudioSegment]] = {}
        orig_track_segments: Optional[List[AudioSegment]] = None
        trans_track_segments: Optional[List[AudioSegment]] = None
        if request.generate_audio:
            if request.audio_tracks:
                normalized_tracks: Dict[str, List[AudioSegment]] = {}
                for key, segments in request.audio_tracks.items():
                    if not segments:
                        continue
                    normalized_key = str(key).strip().lower()
                    if normalized_key in {"trans"}:
                        normalized_key = "translation"
                    elif normalized_key in {"original"}:
                        normalized_key = "orig"
                    if normalized_key:
                        normalized_tracks[normalized_key] = list(segments)
                audio_track_segments = normalized_tracks
            elif audio_segments:
                derived_tracks = _derive_audio_tracks_from_segments(audio_segments)
                if derived_tracks:
                    audio_track_segments = {
                        key: list(segments)
                        for key, segments in derived_tracks.items()
                    }
            orig_track_segments = audio_track_segments.get("orig")
            trans_track_segments = (
                audio_track_segments.get("translation") or audio_track_segments.get("trans")
            )
        video_blocks: List[str] = list(request.video_blocks)
        sentence_payloads: List[Dict[str, object]] = []
        sentence_specs: List[SentenceTimingSpec] = []

        if orig_track_segments is None and audio_track_segments:
            orig_track_segments = audio_track_segments.get("orig")
        if trans_track_segments is None and audio_track_segments:
            trans_track_segments = (
                audio_track_segments.get("translation") or audio_track_segments.get("trans")
            )
        translation_gate_cursor = 0.0
        original_gate_cursor = 0.0

        for offset, block in enumerate(video_blocks):
            sentence_number = request.start_sentence + offset
            audio_segment = audio_segments[offset] if offset < len(audio_segments) else None
            gap_before_translation = 0.0
            gap_after_translation = 0.0
            original_segment = (
                orig_track_segments[offset]
                if orig_track_segments and offset < len(orig_track_segments)
                else None
            )
            translation_segment = (
                trans_track_segments[offset]
                if trans_track_segments and offset < len(trans_track_segments)
                else None
            )
            original_phase = _segment_duration(original_segment)
            translation_phase = _segment_duration(translation_segment)
            word_meta_entry: Optional[Mapping[str, Any]] = None
            if offset < len(request.sentence_metadata):
                candidate_meta = request.sentence_metadata[offset]
                if isinstance(candidate_meta, Mapping):
                    word_meta_entry = candidate_meta
            metadata = self._build_sentence_metadata(
                block=block,
                audio_segment=audio_segment,
                sentence_number=sentence_number,
                original_phase_duration=original_phase,
                translation_phase_duration=translation_phase,
                gap_before_translation=gap_before_translation,
                gap_after_translation=gap_after_translation,
                word_meta=word_meta_entry,
            )
            measured_duration = _segment_duration(translation_segment)
            if measured_duration <= 0:
                measured_duration = _segment_duration(audio_segment)
            if measured_duration <= 0:
                try:
                    measured_duration = max(
                        float(metadata.get("total_duration") or metadata.get("t1") or 0.0),
                        0.0,
                    )
                except (TypeError, ValueError):
                    measured_duration = 0.0
            phase_data = metadata.get("phase_durations")
            if not isinstance(phase_data, Mapping):
                phase_data = {}
            word_timing_meta = metadata.get("word_timing")
            if not isinstance(word_timing_meta, Mapping):
                word_timing_meta = {}
            pause_before_source = metadata.get("pauseBeforeMs")
            if pause_before_source is None:
                pause_before_source = metadata.get("pause_before_ms")
            pause_after_source = metadata.get("pauseAfterMs")
            if pause_after_source is None:
                pause_after_source = metadata.get("pause_after_ms")
            try:
                pause_before_ms = float(pause_before_source)
            except (TypeError, ValueError):
                pause_before_ms = 0.0
            try:
                pause_after_ms = float(pause_after_source)
            except (TypeError, ValueError):
                pause_after_ms = 0.0
            translation_duration_value = float(
                phase_data.get("translation")
                or metadata.get("total_duration")
                or metadata.get("t1")
                or 0.0
            )
            if measured_duration > 0:
                translation_duration_value = measured_duration
            original_phase = float(phase_data.get("original") or 0.0)
            gap_before = float(phase_data.get("gap") or 0.0)
            gap_after = float(phase_data.get("tail") or 0.0)

            original_start_gate = round(original_gate_cursor, 6)
            original_end_gate = round(max(original_start_gate + original_phase, original_start_gate), 6)
            translation_start_gate = round(translation_gate_cursor, 6)
            translation_end_gate = round(
                max(translation_start_gate + translation_duration_value, translation_start_gate), 6
            )

            original_gate_cursor = original_end_gate
            translation_gate_cursor = translation_end_gate

            metadata["startGate"] = translation_start_gate
            metadata["endGate"] = translation_end_gate
            metadata["originalStartGate"] = original_start_gate
            metadata["originalEndGate"] = original_end_gate
            translation_entry = metadata.get("translation") or {}
            original_entry = metadata.get("original") or {}
            original_summary = metadata.get("original_highlighting_summary")
            if not isinstance(original_summary, Mapping):
                original_summary = {}
            original_policy = metadata.get("original_highlighting_policy") or original_summary.get("policy")
            original_source = original_summary.get("source")
            spec = SentenceTimingSpec(
                    sentence_idx=sentence_number,
                    original_text=str(original_entry.get("text") or ""),
                    translation_text=str(translation_entry.get("text") or ""),
                    original_words=list(original_entry.get("tokens") or []),
                    translation_words=list(translation_entry.get("tokens") or []),
                    word_tokens=metadata.get("word_tokens"),
                    original_word_tokens=metadata.get("originalWordTokens")
                    or metadata.get("original_word_tokens"),
                    translation_duration=translation_duration_value,
                    original_duration=float(phase_data.get("original") or 0.0),
                    gap_before_translation=float(phase_data.get("gap") or 0.0),
                    gap_after_translation=float(phase_data.get("tail") or 0.0),
                    char_weighted_enabled=bool(word_timing_meta.get("char_weighted_enabled")),
                    punctuation_boost=bool(word_timing_meta.get("punctuation_boost")),
                    policy=word_timing_meta.get("policy"),
                    source=word_timing_meta.get("source"),
                    original_policy=original_policy,
                    original_source=original_source,
                    start_gate=translation_start_gate,
                    end_gate=translation_end_gate,
                    original_start_gate=original_start_gate,
                    original_end_gate=original_end_gate,
                    pause_before_ms=pause_before_ms,
                    pause_after_ms=pause_after_ms,
                    original_pause_before_ms=float(
                        metadata.get("originalPauseBeforeMs")
                        or metadata.get("original_pause_before_ms")
                        or 0.0
                    ),
                    original_pause_after_ms=float(
                        metadata.get("originalPauseAfterMs")
                        or metadata.get("original_pause_after_ms")
                        or 0.0
                    ),
                )
            sentence_specs.append(spec)
            sentence_payloads.append(_compact_sentence_payload(metadata))

        track_artifacts: Dict[str, Dict[str, Any]] = {}

        exportable_tracks: Dict[str, List[AudioSegment]] = {
            key: list(segments)
            for key, segments in audio_track_segments.items()
            if segments
        }

        try:
            document_paths = output_formatter.export_batch_documents(
                str(writer.work_dir),
                self._context.base_name,
                request.start_sentence,
                request.end_sentence,
                list(request.written_blocks),
                request.target_language,
                self._context.total_sentences,
                output_html=request.output_html,
                output_pdf=request.output_pdf,
            )
            for kind, created_path in document_paths.items():
                staged_path = writer.stage(Path(created_path))
                artifacts[kind] = str(staged_path)

            audio_bitrate = self._resolve_audio_bitrate()
            if request.generate_audio and exportable_tracks:
                for track_key, segments in exportable_tracks.items():
                    if not segments:
                        continue
                    combined_track = AudioSegment.empty()
                    for segment in segments:
                        if segment:
                            combined_track += segment
                    normalized_key = "translation" if track_key in {"trans", "translation"} else track_key
                    suffix = "trans" if normalized_key == "translation" else normalized_key
                    audio_filename = writer.work_dir / f"{range_fragment}_{self._context.base_name}_{suffix}.mp3"
                    if audio_bitrate:
                        combined_track.export(str(audio_filename), format="mp3", bitrate=audio_bitrate)
                    else:
                        combined_track.export(str(audio_filename), format="mp3")
                    staged_audio = writer.stage(audio_filename)
                    staged_path = Path(staged_audio)
                    relative_path = self._job_relative_path(staged_path)
                    duration_value = getattr(combined_track, "duration_seconds", 0.0) or 0.0
                    sample_rate = getattr(combined_track, "frame_rate", None)
                    if isinstance(sample_rate, (int, float)) and sample_rate > 0:
                        sample_rate_value = int(sample_rate)
                    else:
                        sample_rate_value = 44100
                    track_artifacts[normalized_key] = {
                        "path": relative_path,
                        "duration": round(float(duration_value), 6) if duration_value else 0.0,
                        "sampleRate": sample_rate_value,
                    }
                    if normalized_key == "translation":
                        artifacts.setdefault("audio", relative_path)
                    else:
                        artifacts[f"audio_{normalized_key}"] = relative_path
                translation_entry = track_artifacts.get("translation") or track_artifacts.get("trans")
                translation_path = translation_entry.get("path") if isinstance(translation_entry, Mapping) else None
                if translation_path:
                    artifacts.setdefault("audio", translation_path)

            if request.generate_audio and audio_segments and "audio" not in artifacts:
                combined = AudioSegment.empty()
                for segment in audio_segments:
                    combined += segment
                audio_filename = writer.work_dir / f"{range_fragment}_{self._context.base_name}.mp3"
                if audio_bitrate:
                    combined.export(str(audio_filename), format="mp3", bitrate=audio_bitrate)
                else:
                    combined.export(str(audio_filename), format="mp3")
                staged_audio = writer.stage(audio_filename)
                staged_path = Path(staged_audio)
                relative_path = self._job_relative_path(staged_path)
                artifacts["audio"] = relative_path
                duration_value = getattr(combined, "duration_seconds", 0.0) or 0.0
                sample_rate = getattr(combined, "frame_rate", None)
                if isinstance(sample_rate, (int, float)) and sample_rate > 0:
                    sample_rate_value = int(sample_rate)
                else:
                    sample_rate_value = 44100
                track_artifacts.setdefault(
                    "translation",
                    {
                        "path": relative_path,
                        "duration": round(float(duration_value), 6) if duration_value else 0.0,
                        "sampleRate": sample_rate_value,
                    },
                )

            video_audio_segments = audio_segments if audio_segments else (orig_track_segments or [])
            if request.generate_video and video_audio_segments and video_blocks:
                video_output = av_gen.render_video_slides(
                    video_blocks,
                    video_audio_segments,
                    str(writer.work_dir),
                    request.start_sentence,
                    request.end_sentence,
                    self._context.base_name,
                    self._context.cover_image,
                    self._context.book_author,
                    self._context.book_title,
                    list(self._context.global_cumulative_word_counts),
                    self._context.total_book_words,
                    self._context.macos_reading_speed,
                    self._context.input_language,
                    self._context.total_sentences,
                    self._context.tempo,
                    self._context.sync_ratio,
                    self._context.word_highlighting,
                    self._context.highlight_granularity,
                    voice_display,
                    slide_render_options=self._context.slide_render_options,
                    template_name=self._context.template_name,
                    video_service=self._video_service,
                    voice_lines=voice_lines,
                )
                video_path = Path(video_output)
                video_path = writer.stage(video_path)
                artifacts["video"] = str(video_path)

            writer.commit()
        except Exception:
            writer.rollback()
            raise

        translation_duration_fallback = sum(spec.translation_duration for spec in sentence_specs)
        original_duration_fallback = sum(spec.original_duration for spec in sentence_specs)
        def _duration_for(track_key: str, fallback: float) -> float:
            entry = track_artifacts.get(track_key)
            if isinstance(entry, Mapping):
                try:
                    raw_value = float(entry.get("duration", 0.0))
                except (TypeError, ValueError):
                    raw_value = 0.0
                if raw_value > 0:
                    return max(raw_value, fallback)
            return fallback

        # Get actual audio durations from exported tracks
        def _actual_duration_for(track_key: str) -> float:
            entry = track_artifacts.get(track_key)
            if isinstance(entry, Mapping):
                try:
                    return max(float(entry.get("duration", 0.0)), 0.0)
                except (TypeError, ValueError):
                    pass
            return 0.0

        actual_original_duration = _actual_duration_for("orig")
        actual_translation_duration = _actual_duration_for("translation")

        # Expected durations from sentence specs (used to build timing)
        expected_original_duration = original_duration_fallback
        expected_translation_duration = translation_duration_fallback

        # Use actual duration for track_durations if available, otherwise fallback
        track_durations = {
            "original": actual_original_duration if actual_original_duration > 0 else original_duration_fallback,
            "translation": actual_translation_duration if actual_translation_duration > 0 else translation_duration_fallback,
        }

        timing_tracks: Dict[str, List[Dict[str, Any]]] = {}
        timing_validation: Dict[str, Any] = {}
        highlighting_policy = _resolve_highlighting_policy(sentence_specs) if sentence_specs else None

        if sentence_specs:
            # Use chunk-local indices for multi-sentence chunks so the frontend
            # can correctly map timing data to displayed sentences
            raw_timing_tracks = build_separate_track_timings(
                sentence_specs,
                original_duration=expected_original_duration,
                translation_duration=expected_translation_duration,
                use_local_indices=True,
            )

            # Scale timing tracks to match actual audio duration if there's a mismatch
            # This ensures the frontend doesn't need to apply scaling at runtime
            original_tokens = raw_timing_tracks.get("original", [])
            translation_tokens = raw_timing_tracks.get("translation", [])

            if actual_original_duration > 0 and original_tokens:
                scaled_original, original_validation = scale_timing_to_audio_duration(
                    original_tokens,
                    expected_original_duration,
                    actual_original_duration,
                )
                timing_tracks["original"] = scaled_original
                timing_validation["original"] = original_validation
            else:
                timing_tracks["original"] = original_tokens
                timing_validation["original"] = {
                    "expected_duration": round(expected_original_duration, 6),
                    "actual_duration": round(actual_original_duration, 6),
                    "scaling_applied": False,
                }

            if actual_translation_duration > 0 and translation_tokens:
                scaled_translation, translation_validation = scale_timing_to_audio_duration(
                    translation_tokens,
                    expected_translation_duration,
                    actual_translation_duration,
                )
                timing_tracks["translation"] = scaled_translation
                timing_validation["translation"] = translation_validation
            else:
                timing_tracks["translation"] = translation_tokens
                timing_validation["translation"] = {
                    "expected_duration": round(expected_translation_duration, 6),
                    "actual_duration": round(actual_translation_duration, 6),
                    "scaling_applied": False,
                }
        else:
            timing_tracks = {"original": [], "translation": []}

        return BatchExportResult(
            chunk_id=chunk_id,
            start_sentence=request.start_sentence,
            end_sentence=request.end_sentence,
            range_fragment=range_fragment,
            artifacts=artifacts,
            sentences=sentence_payloads,
            audio_tracks=track_artifacts,
            timing_tracks=timing_tracks,
            highlighting_policy=highlighting_policy,
            timing_version="2",
            timing_validation=timing_validation,
        )


def build_exporter(
    *,
    base_dir: str,
    base_name: str,
    cover_img: Optional[Image.Image],
    book_author: str,
    book_title: str,
    global_cumulative_word_counts: Sequence[int],
    total_book_words: int,
    macos_reading_speed: float,
    input_language: str,
    total_sentences: int,
    tempo: float,
    sync_ratio: float,
    word_highlighting: bool,
    highlight_granularity: str,
    selected_voice: str,
    primary_target_language: str,
    audio_bitrate_kbps: Optional[int] = None,
    slide_render_options: Optional[SlideRenderOptions],
    template_name: Optional[str],
    video_backend: str,
    video_backend_settings: Mapping[str, Mapping[str, object]],
) -> BatchExporter:
    """Construct a :class:`BatchExporter` for the provided pipeline context."""

    voice_name = get_voice_display_name(
        selected_voice,
        primary_target_language,
        LANGUAGE_CODES,
    )

    context = BatchExportContext(
        base_dir=base_dir,
        base_name=base_name,
        cover_image=cover_img,
        book_author=book_author,
        book_title=book_title,
        global_cumulative_word_counts=list(global_cumulative_word_counts),
        total_book_words=total_book_words,
        macos_reading_speed=macos_reading_speed,
        input_language=input_language,
        total_sentences=total_sentences,
        tempo=tempo,
        sync_ratio=sync_ratio,
        word_highlighting=word_highlighting,
        highlight_granularity=highlight_granularity,
        selected_voice=selected_voice,
        audio_bitrate_kbps=audio_bitrate_kbps,
        voice_name=voice_name,
        slide_render_options=slide_render_options,
        template_name=template_name,
        video_backend=video_backend,
        video_backend_settings=video_backend_settings,
    )
    return BatchExporter(context)
