from __future__ import annotations

import os
import statistics
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from modules.subtitles.models import SubtitleColorPalette
from modules.subtitles.render import CueTextRenderer, _SubtitleFileWriter
from modules.transliteration import TransliterationService

from .common import _TARGET_DUB_HEIGHT, _AssDialogue, logger
from .dialogues import _merge_overlapping_dialogues, _parse_dialogues
from .language import _language_uses_non_latin, _normalize_rtl_word_order
from .subtitle_render import render_ass_for_block
from .video_utils import (
    _concat_video_segments,
    _concat_video_segments_copy,
    _concat_video_segments_ts_copy,
    _downscale_video,
    _probe_duration_seconds,
    _segments_safe_for_stream_copy_concat,
)
from .webvtt import _write_webvtt

_STITCHED_SUFFIX = ".full"


def _resolve_stitched_output_path(base_output: Path) -> Path:
    suffix = base_output.suffix or ".mp4"
    base_name = f"{base_output.stem}{_STITCHED_SUFFIX}{suffix}"
    candidate = base_output.with_name(base_name)
    if candidate.exists():
        validity = _is_stitched_video_valid(candidate)
        # If the existing stitched output is known-bad (frozen video), overwrite it in-place
        # so downstream clients keep the stable `.full` filename.
        if validity is False:
            return candidate
    counter = 2
    while candidate.exists():
        candidate = base_output.with_name(f"{base_output.stem}{_STITCHED_SUFFIX}-{counter}{suffix}")
        counter += 1
    return candidate


def _validate_stitched_video(video_path: Path) -> None:
    """
    Best-effort validation for stitched MP4 playback correctness.

    Some MP4 stream-copy concat runs can yield a file whose video timestamps stop advancing
    part-way through (audio continues, video appears frozen). Detect this cheaply by probing
    frame timestamps near the end of the file.
    """

    duration = _probe_duration_seconds(video_path)
    if duration <= 1.0:
        return
    probe_start = max(0.0, duration - 15.0)
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    result = subprocess.run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_frames",
            "-read_intervals",
            f"{probe_start}%+3",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "csv=p=0",
            str(video_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe validation failed (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
        )
    timestamps: List[float] = []
    for line in result.stdout.decode(errors="ignore").splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        try:
            timestamps.append(float(candidate))
        except Exception:
            continue
    if len(timestamps) < 10:
        raise RuntimeError(f"Stitched video validation failed: only {len(timestamps)} frames probed")
    deltas = [b - a for a, b in zip(timestamps, timestamps[1:]) if b > a]
    if not deltas:
        raise RuntimeError("Stitched video validation failed: non-increasing frame timestamps")
    span = timestamps[-1] - timestamps[0]
    median_delta = statistics.median(deltas)
    # If timestamps barely advance, playback will appear frozen while audio continues.
    if span < 0.2 or median_delta < 0.001:
        raise RuntimeError(
            f"Stitched video validation failed: timestamp span={span:.6f}s median_step={median_delta:.6f}s"
        )


def _is_stitched_video_valid(video_path: Path) -> Optional[bool]:
    try:
        _validate_stitched_video(video_path)
    except Exception as exc:
        message = str(exc)
        if "validation failed" in message:
            return False
        return None
    return True


def _shift_dialogues(dialogues: Sequence[_AssDialogue], offset_seconds: float) -> List[_AssDialogue]:
    if not dialogues or offset_seconds == 0:
        return list(dialogues)
    shifted: List[_AssDialogue] = []
    for entry in dialogues:
        shifted.append(
            _AssDialogue(
                start=max(0.0, entry.start + offset_seconds),
                end=max(0.0, entry.end + offset_seconds),
                translation=entry.translation,
                original=entry.original,
                transliteration=entry.transliteration,
                rtl_normalized=entry.rtl_normalized,
                speech_offset=entry.speech_offset,
                speech_duration=entry.speech_duration,
            )
        )
    return shifted


def _prepare_dialogues_for_stitched_render(
    dialogues: Sequence[_AssDialogue],
    *,
    language_code: str,
) -> List[_AssDialogue]:
    """
    Prepare parsed dialogue text for stitched subtitle rendering.

    The batch pipeline stores RTL translations in a pre-normalized (word-reversed)
    form and the subtitle renderers apply RTL normalization again when writing ASS/VTT.
    When stitching, we parse the batch subtitle exports (which are already "double
    normalized") and re-render them. To preserve the same highlight direction and
    layout, pre-normalize RTL translations here so stitched ASS/VTT outputs match
    the per-batch subtitle behavior.
    """

    if not dialogues:
        return []
    prepared: List[_AssDialogue] = []
    for entry in dialogues:
        prepared.append(
            _AssDialogue(
                start=entry.start,
                end=entry.end,
                translation=_normalize_rtl_word_order(entry.translation, language_code, force=True),
                original=entry.original,
                transliteration=entry.transliteration,
                rtl_normalized=True if entry.translation else entry.rtl_normalized,
                speech_offset=entry.speech_offset,
                speech_duration=entry.speech_duration,
            )
        )
    return prepared


def stitch_dub_batches(
    batch_videos: Sequence[Path],
    *,
    base_output: Path,
    language_code: str,
    include_transliteration: bool,
    transliterator: Optional[TransliterationService],
    target_height: int = _TARGET_DUB_HEIGHT,
    preserve_aspect_ratio: bool = True,
) -> Optional[Tuple[Path, Path, Path]]:
    """
    Stitch per-batch dubbed outputs into a single MP4 plus VTT and ASS subtitles.

    Returns (stitched_mp4, stitched_vtt, stitched_ass) or None when stitching is not applicable.
    """

    ordered = [Path(path) for path in batch_videos if path and Path(path).exists()]
    if len(ordered) < 2:
        return None
    ordered = sorted(ordered, key=lambda p: p.name)

    stitched_video = _resolve_stitched_output_path(base_output)
    stitched_video.parent.mkdir(parents=True, exist_ok=True)

    try:
        stitched_final: Path
        copy_safe = _segments_safe_for_stream_copy_concat(ordered)
        if copy_safe:
            try:
                _concat_video_segments_copy(ordered, stitched_video)
                try:
                    _validate_stitched_video(stitched_video)
                except Exception:
                    stitched_video.unlink(missing_ok=True)
                    raise
                stitched_final = stitched_video
                logger.info(
                    "Stitched batch videos via stream-copy concat (mp4)",
                    extra={"event": "youtube.dub.stitch.copy", "output": stitched_final.as_posix()},
                )
            except Exception:
                _concat_video_segments_ts_copy(ordered, stitched_video)
                _validate_stitched_video(stitched_video)
                stitched_final = stitched_video
                logger.info(
                    "Stitched batch videos via stream-copy concat (ts)",
                    extra={"event": "youtube.dub.stitch.ts_copy", "output": stitched_final.as_posix()},
                )
        else:
            logger.info(
                "Skipping stream-copy concat due to mismatched batch stream timing; re-encoding stitched output",
                extra={"event": "youtube.dub.stitch.copy_skipped"},
            )
            temp_concat = stitched_video.with_suffix(".concat.mp4")
            try:
                _concat_video_segments(ordered, temp_concat)
                stitched_final = _downscale_video(
                    temp_concat,
                    target_height=int(target_height),
                    preserve_aspect_ratio=bool(preserve_aspect_ratio),
                    output_path=stitched_video,
                )
                _validate_stitched_video(stitched_final)
                logger.info(
                    "Stitched batch videos via re-encode concat",
                    extra={"event": "youtube.dub.stitch.reencode", "output": stitched_final.as_posix()},
                )
            finally:
                temp_concat.unlink(missing_ok=True)
    except Exception:
        logger.warning("Unable to stitch batch videos into %s", stitched_video, exc_info=True)
        return None

    stitched_vtt = stitched_final.with_suffix(".vtt")
    stitched_ass = stitched_final.with_suffix(".ass")

    stitched_dialogues: List[_AssDialogue] = []
    offset = 0.0
    for batch_video in ordered:
        duration = _probe_duration_seconds(batch_video)
        subtitle_source = None
        for candidate in (
            batch_video.with_suffix(".ass"),
            batch_video.with_suffix(".vtt"),
            batch_video.with_suffix(".srt"),
        ):
            if candidate.exists():
                subtitle_source = candidate
                break
        if subtitle_source is not None:
            try:
                dialogues = _parse_dialogues(subtitle_source)
                dialogues = _prepare_dialogues_for_stitched_render(dialogues, language_code=language_code)
                stitched_dialogues.extend(_shift_dialogues(dialogues, offset))
            except Exception:
                logger.debug("Unable to parse stitched subtitles from %s", subtitle_source, exc_info=True)
        offset += max(0.0, duration)

    stitched_dialogues = sorted(stitched_dialogues, key=lambda d: (d.start, d.end))
    merged = _merge_overlapping_dialogues(stitched_dialogues) if stitched_dialogues else []
    try:
        _write_webvtt(
            merged,
            stitched_vtt,
            target_language=language_code,
            include_transliteration=include_transliteration,
            transliterator=transliterator if include_transliteration else None,
        )
    except Exception:
        logger.debug("Unable to write stitched VTT to %s", stitched_vtt, exc_info=True)
    try:
        palette = SubtitleColorPalette.default()
        emphasis_scale = 1.3 if _language_uses_non_latin(language_code) else 1.0
        renderer = CueTextRenderer("ass", palette, emphasis_scale=emphasis_scale)
        stitched_ass.parent.mkdir(parents=True, exist_ok=True)
        with stitched_ass.open("w", encoding="utf-8") as handle:
            writer = _SubtitleFileWriter(handle, renderer, "ass", start_index=1)
            render_ass_for_block(
                merged,
                writer,
                start_index=1,
                offset_seconds=0.0,
                include_transliteration=include_transliteration,
                transliterator=transliterator if include_transliteration else None,
                language_code=language_code,
                ass_renderer=renderer,
            )
    except Exception:
        logger.debug("Unable to write stitched ASS to %s", stitched_ass, exc_info=True)

    return stitched_final, stitched_vtt, stitched_ass


__all__ = ["stitch_dub_batches"]
