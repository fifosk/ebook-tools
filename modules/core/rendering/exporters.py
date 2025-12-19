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
from modules.audio.tts import SILENCE_DURATION_MS, get_voice_display_name
from modules.config.loader import get_rendering_config
from modules.core.rendering.constants import LANGUAGE_CODES
from modules.core.rendering.timeline import (
    SentenceTimingSpec,
    build_dual_track_timings,
    build_word_events,
)
from modules.render.context import RenderBatchContext
from modules.render.output_writer import DeferredBatchWriter
from modules.video.api import VideoService
from modules.video.slides import SlideRenderOptions
from modules.audio.highlight import _get_audio_metadata, timeline
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


def serialize_sentence_chunk(sentence_meta: Mapping[str, Any]) -> Dict[str, Any]:
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

    word_events = build_word_events(sentence_meta)

    chunk_entry: Dict[str, Any] = {
        "sentence_id": sentence_id_str,
        "text": text_str,
        "t0": t0,
        "t1": t1,
        "timing": {"t0": t0, "t1": t1},
    }
    if word_events:
        chunk_entry["timingTracks"] = {"translation": word_events}

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
        tracks["trans"] = translation_segments
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


class BatchExporter:
    """Persist batch outputs for written, audio, and optional video artifacts."""

    def __init__(self, context: BatchExportContext) -> None:
        self._context = context
        self._video_service = VideoService(
            backend=context.video_backend,
            backend_settings=context.video_backend_settings,
        )

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

        timeline_options = timeline.TimelineBuildOptions(
            sync_ratio=self._context.sync_ratio,
            word_highlighting=self._context.word_highlighting,
            highlight_granularity=self._context.highlight_granularity,
        )
        timeline_result = timeline.build(block, audio_segment, timeline_options)

        events_payload: List[Dict[str, object]] = [
            {
                "duration": event.duration,
                "original_index": event.original_index,
                "translation_index": event.translation_index,
                "transliteration_index": event.transliteration_index,
            }
            for event in timeline_result.events
        ]
        raw_timeline_duration = sum(event.duration for event in timeline_result.events)
        if audio_segment is not None:
            audio_duration = float(audio_segment.duration_seconds)
        else:
            audio_duration = raw_timeline_duration
        if audio_duration <= 0 and raw_timeline_duration > 0:
            audio_duration = raw_timeline_duration

        original_tokens = _tokenize_words(original_text)
        translation_units = _split_translation_units(header, translation_text)
        transliteration_tokens = _tokenize_words(transliteration_text)

        payload: Dict[str, object] = {
            "sentence_number": sentence_number,
            "original": {
                "text": original_text,
                "tokens": original_tokens,
            },
            "timeline": events_payload,
            "highlight_granularity": timeline_result.effective_granularity,
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
        payload["origWords"] = list(original_tokens)
        payload["transWords"] = list(translation_units)

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
        meta_payload.setdefault(
            "text",
            meta_payload.get("text") or translation_text or original_text,
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

        pause_before_source = meta_payload.get("pause_before_ms")
        if pause_before_source is None:
            pause_before_source = meta_payload.get("pauseBeforeMs")
        pause_after_source = meta_payload.get("pause_after_ms")
        if pause_after_source is None:
            pause_after_source = meta_payload.get("pauseAfterMs")
        pause_before_ms = max(_coerce_pause_ms(pause_before_source), 0)
        pause_after_ms = max(_coerce_pause_ms(pause_after_source), 0)
        meta_payload["pause_before_ms"] = pause_before_ms
        meta_payload["pause_after_ms"] = pause_after_ms

        chunk_entry = serialize_sentence_chunk(meta_payload)
        payload["sentence_id"] = chunk_entry["sentence_id"]
        payload["text"] = chunk_entry["text"]
        payload["t0"] = chunk_entry["t0"]
        payload["t1"] = chunk_entry["t1"]
        payload["timing"] = chunk_entry["timing"]
        if "timingTracks" in chunk_entry:
            payload["timingTracks"] = chunk_entry["timingTracks"]
        payload["word_tokens"] = list(meta_payload.get("word_tokens") or [])
        highlighting_summary = chunk_entry.get("highlighting_summary", {})
        if not isinstance(highlighting_summary, Mapping):
            highlighting_summary = {}
        payload["charWeighted"] = {
            "enabled": bool(highlighting_summary.get("char_weighted")),
            "punctuationBoost": bool(highlighting_summary.get("punctuation_weighting")),
        }
        policy_value = chunk_entry.get("highlighting_policy") or highlighting_summary.get("policy")
        payload["word_timing"] = {
            "policy": policy_value,
            "source": highlighting_summary.get("source"),
            "char_weighted_enabled": bool(highlighting_summary.get("char_weighted")),
            "punctuation_boost": bool(highlighting_summary.get("punctuation_weighting")),
        }
        payload["pause_before_ms"] = pause_before_ms
        payload["pause_after_ms"] = pause_after_ms
        payload["pauseBeforeMs"] = pause_before_ms
        payload["pauseAfterMs"] = pause_after_ms

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
            slide_duration = max(float(end_gate_value) - float(start_gate_value), 0.0)
            payload["slide_duration"] = slide_duration
            payload["slideDuration"] = slide_duration
            payload.setdefault("start_gate", float(start_gate_value))
            payload.setdefault("end_gate", float(end_gate_value))
            payload.setdefault("startGate", float(start_gate_value))
            payload.setdefault("endGate", float(end_gate_value))

        image_payload = meta_payload.get("image")
        if isinstance(image_payload, Mapping):
            payload["image"] = dict(image_payload)
        image_path = meta_payload.get("image_path") or meta_payload.get("imagePath")
        if isinstance(image_path, str) and image_path.strip():
            trimmed = image_path.strip()
            payload["image_path"] = trimmed
            payload["imagePath"] = trimmed

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
        combined_track_available = False
        orig_track_segments: Optional[List[AudioSegment]] = None
        trans_track_segments: Optional[List[AudioSegment]] = None
        silence_ms = max(int(SILENCE_DURATION_MS), 0)
        silence = AudioSegment.silent(duration=silence_ms)
        silence_seconds = silence_ms / 1000.0 if silence_ms > 0 else 0.0
        if request.generate_audio:
            if request.audio_tracks:
                audio_track_segments = {
                    key: list(segments)
                    for key, segments in request.audio_tracks.items()
                    if segments
                }
            elif audio_segments:
                derived_tracks = _derive_audio_tracks_from_segments(audio_segments)
                if derived_tracks:
                    audio_track_segments = {
                        key: list(segments)
                        for key, segments in derived_tracks.items()
                    }
            orig_track_segments = audio_track_segments.get("orig")
            trans_track_segments = audio_track_segments.get("trans")
            combined_track_available = bool(orig_track_segments and trans_track_segments)
            if orig_track_segments and trans_track_segments:
                combined_segments: List[AudioSegment] = []
                max_len = max(len(orig_track_segments), len(trans_track_segments))
                for index in range(max_len):
                    merged = AudioSegment.silent(duration=0)
                    if index < len(orig_track_segments):
                        segment = orig_track_segments[index]
                        if segment:
                            merged += segment
                    if index < len(orig_track_segments) and index < len(trans_track_segments):
                        merged += silence
                    if index < len(trans_track_segments):
                        segment = trans_track_segments[index]
                        if segment:
                            merged += segment
                    if index < max_len - 1:
                        merged += silence
                    combined_segments.append(merged)
                if combined_segments:
                    audio_track_segments["orig_trans"] = combined_segments
        video_blocks: List[str] = list(request.video_blocks)
        sentence_payloads: List[Dict[str, object]] = []
        sentence_specs: List[SentenceTimingSpec] = []
        chunk_timing_tracks: Dict[str, List[Dict[str, Any]]] = {
            "translation": [],
            "mix": [],
        }

        if orig_track_segments is None and audio_track_segments:
            orig_track_segments = audio_track_segments.get("orig")
        if trans_track_segments is None and audio_track_segments:
            trans_track_segments = audio_track_segments.get("trans")
        max_track_len = max(
            len(orig_track_segments) if orig_track_segments else 0,
            len(trans_track_segments) if trans_track_segments else 0,
        )
        translation_gate_cursor = 0.0
        mix_gate_cursor = 0.0

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
            if combined_track_available and original_phase > 0 and translation_phase > 0 and silence_seconds > 0:
                gap_before_translation = silence_seconds
            if combined_track_available and offset < max_track_len - 1 and silence_seconds > 0 and (
                original_phase > 0 or translation_phase > 0
            ):
                gap_after_translation = silence_seconds
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
            pause_before_source = metadata.get("pause_before_ms")
            if pause_before_source is None:
                pause_before_source = metadata.get("pauseBeforeMs")
            pause_after_source = metadata.get("pause_after_ms")
            if pause_after_source is None:
                pause_after_source = metadata.get("pauseAfterMs")
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
            sentence_mix_total = original_phase + gap_before + translation_duration_value + gap_after

            mix_start_gate = round(mix_gate_cursor, 6)
            mix_end_gate = round(max(mix_start_gate + sentence_mix_total, mix_start_gate), 6)
            translation_start_gate = round(mix_start_gate + original_phase + gap_before, 6)
            translation_end_gate = round(max(translation_start_gate + translation_duration_value, translation_start_gate), 6)

            mix_gate_cursor = mix_end_gate
            translation_gate_cursor = translation_end_gate

            metadata["start_gate"] = translation_start_gate
            metadata["end_gate"] = translation_end_gate
            metadata["startGate"] = translation_start_gate
            metadata["endGate"] = translation_end_gate
            metadata["mix_start_gate"] = mix_start_gate
            metadata["mix_end_gate"] = mix_end_gate
            sentence_payloads.append(metadata)
            translation_entry = metadata.get("translation") or {}
            original_entry = metadata.get("original") or {}
            spec = SentenceTimingSpec(
                    sentence_idx=sentence_number,
                    original_text=str(original_entry.get("text") or ""),
                    translation_text=str(translation_entry.get("text") or ""),
                    original_words=list(original_entry.get("tokens") or []),
                    translation_words=list(translation_entry.get("tokens") or []),
                    word_tokens=metadata.get("word_tokens"),
                    translation_duration=translation_duration_value,
                    original_duration=float(phase_data.get("original") or 0.0),
                    gap_before_translation=float(phase_data.get("gap") or 0.0),
                    gap_after_translation=float(phase_data.get("tail") or 0.0),
                    char_weighted_enabled=bool(word_timing_meta.get("char_weighted_enabled")),
                    punctuation_boost=bool(word_timing_meta.get("punctuation_boost")),
                    policy=word_timing_meta.get("policy"),
                    source=word_timing_meta.get("source"),
                    start_gate=translation_start_gate,
                    end_gate=translation_end_gate,
                    pause_before_ms=pause_before_ms,
                    pause_after_ms=pause_after_ms,
                )
            sentence_specs.append(spec)
            spec.mix_start_gate = mix_start_gate
            spec.mix_end_gate = mix_end_gate

            timing_tracks = metadata.get("timingTracks")
            if isinstance(timing_tracks, Mapping):
                for track_name, buffer in chunk_timing_tracks.items():
                    token_entries = timing_tracks.get(track_name)
                    if not isinstance(token_entries, list):
                        continue
                    for entry in token_entries:
                        if not isinstance(entry, Mapping):
                            continue
                        token_copy = dict(entry)
                        token_copy.setdefault("sentenceIdx", sentence_number)
                        if track_name == "translation":
                            token_copy.setdefault("lane", "trans")
                        else:
                            token_copy.setdefault("lane", token_copy.get("lane") or "mix")
                        buffer.append(token_copy)

        track_artifacts: Dict[str, Dict[str, Any]] = {}

        exportable_tracks: Dict[str, List[AudioSegment]] = {
            key: list(segments)
            for key, segments in audio_track_segments.items()
            if key != "orig"
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

            if request.generate_audio and exportable_tracks:
                for track_key, segments in exportable_tracks.items():
                    if not segments:
                        continue
                    combined_track = AudioSegment.empty()
                    for segment in segments:
                        if segment:
                            combined_track += segment
                    suffix = "trans" if track_key == "trans" else track_key
                    audio_filename = writer.work_dir / f"{range_fragment}_{self._context.base_name}_{suffix}.mp3"
                    combined_track.export(str(audio_filename), format="mp3", bitrate="320k")
                    staged_audio = writer.stage(audio_filename)
                    staged_path = Path(staged_audio)
                    relative_path = self._job_relative_path(staged_path)
                    normalized_key = "translation" if track_key in {"trans", "translation"} else track_key
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
                    if track_key == "trans":
                        artifacts.setdefault("audio", relative_path)
                    else:
                        artifacts[f"audio_{track_key}"] = relative_path
                translation_entry = track_artifacts.get("translation") or track_artifacts.get("trans")
                translation_path = translation_entry.get("path") if isinstance(translation_entry, Mapping) else None
                if translation_path:
                    artifacts.setdefault("audio", translation_path)

            if request.generate_audio and audio_segments and "audio" not in artifacts:
                combined = AudioSegment.empty()
                for segment in audio_segments:
                    combined += segment
                audio_filename = writer.work_dir / f"{range_fragment}_{self._context.base_name}.mp3"
                combined.export(str(audio_filename), format="mp3", bitrate="320k")
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

            if request.generate_video and audio_segments and video_blocks:
                video_output = av_gen.render_video_slides(
                    video_blocks,
                    audio_segments,
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
        mix_duration_fallback = max(
            (float(getattr(spec, "mix_end_gate", getattr(spec, "end_gate", 0.0)) or 0.0) for spec in sentence_specs),
            default=0.0,
        )
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

        track_durations = {
            "mix": _duration_for("orig_trans", mix_duration_fallback),
            "translation": _duration_for("translation", translation_duration_fallback),
        }
        timing_tracks: Dict[str, List[Dict[str, Any]]] = {}
        if sentence_specs:
            timing_tracks = build_dual_track_timings(
                sentence_specs,
                mix_duration=track_durations["mix"],
                translation_duration=track_durations["translation"],
            )
        else:
            timing_tracks = {
                "mix": [dict(token) for token in chunk_timing_tracks["mix"]],
                "translation": [dict(token) for token in chunk_timing_tracks["translation"]],
            }

        return BatchExportResult(
            chunk_id=chunk_id,
            start_sentence=request.start_sentence,
            end_sentence=request.end_sentence,
            range_fragment=range_fragment,
            artifacts=artifacts,
            sentences=sentence_payloads,
            audio_tracks=track_artifacts,
            timing_tracks=timing_tracks,
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
        voice_name=voice_name,
        slide_render_options=slide_render_options,
        template_name=template_name,
        video_backend=video_backend,
        video_backend_settings=video_backend_settings,
    )
    return BatchExporter(context)
