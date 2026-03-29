from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from modules.services.youtube_subtitles import trim_stem_preserving_id

from .audio_utils import _build_atempo_filters, _has_audio_stream
from .common import _TARGET_DUB_HEIGHT, _TEMP_DIR, _YOUTUBE_ID_PATTERN, logger

_MP4_MOVFLAGS = "+faststart"
_IOS_TARGET_FPS = os.environ.get("EBOOK_IOS_TARGET_FPS", "30000/1001")
_IOS_VIDEO_TRACK_TIMESCALE = os.environ.get("EBOOK_IOS_VIDEO_TRACK_TIMESCALE", "90000")
_IOS_VIDEO_CODEC_ARGS = (
    "-c:v",
    "libx264",
    "-profile:v",
    "main",
    "-level:v",
    "4.1",
    "-pix_fmt",
    "yuv420p",
)
_IOS_AUDIO_CODEC_ARGS = ("-c:a", "aac", "-ac", "2", "-ar", "44100")


def _movflags_args(destination: Path) -> list[str]:
    if destination.suffix.lower() in {".mp4", ".m4v"}:
        return ["-movflags", _MP4_MOVFLAGS]
    return []


def _ios_timing_args(destination: Path) -> list[str]:
    """
    Return ffmpeg args that make output MP4 playback more predictable on iOS.

    A CFR output dramatically improves concat safety and avoids iOS/Safari edge cases where
    muxed VFR segments play back with frozen video while audio continues.
    """

    args = ["-vsync", "cfr", "-r", _IOS_TARGET_FPS]
    if destination.suffix.lower() in {".mp4", ".m4v"} and _IOS_VIDEO_TRACK_TIMESCALE:
        args.extend(["-video_track_timescale", str(_IOS_VIDEO_TRACK_TIMESCALE)])
    return args


def _subtitle_matches_video(video_path: Path, subtitle_path: Path) -> bool:
    """Return True if ``subtitle_path`` appears to belong to ``video_path``."""

    base_stem = video_path.stem
    subtitle_name = subtitle_path.name
    if subtitle_name.startswith(f"{base_stem}."):
        return True
    if subtitle_name.startswith(f"{base_stem}_"):
        return True
    if subtitle_name.startswith(f"{base_stem}-"):
        return True
    return False


def _classify_video_source(video_path: Path) -> str:
    """Return a source label for NAS videos to distinguish YouTube downloads."""

    stem = video_path.stem.lower()
    normalized = video_path.name.replace("_", "-")
    if stem.endswith("-yt") or stem.endswith("_yt"):
        return "youtube"
    if _YOUTUBE_ID_PATTERN.search(normalized):
        return "youtube"
    return "nas_video"


def _has_video_stream(path: Path) -> bool:
    """Return True if ffprobe detects a valid video stream with a known pixel format."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=pix_fmt,width,height",
                "-of",
                "json",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return False
        try:
            payload = json.loads(result.stdout.decode() or "{}")
        except Exception:
            return False
        streams = payload.get("streams") or []
        if not streams:
            return False
        stream = streams[0] or {}
        pix_fmt = (stream.get("pix_fmt") or "").strip()
        if not pix_fmt:
            return False
        pix_fmt_lower = pix_fmt.lower()
        if pix_fmt_lower in {"unknown", "none"}:
            return False
        # If width/height are present, ensure they are sane (>0).
        width = stream.get("width")
        height = stream.get("height")
        if width is not None and height is not None:
            try:
                if int(width) <= 0 or int(height) <= 0:
                    return False
            except Exception:
                return False
        return True
    except Exception:
        return False


def _probe_duration_seconds(path: Path) -> float:
    """Return media duration in seconds, or 0 on failure."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return 0.0
        return float(result.stdout.decode().strip() or 0.0)
    except Exception:
        return 0.0


def _probe_video_height(path: Path) -> Optional[int]:
    """Return the primary video stream height, or None when unavailable."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=height",
                "-of",
                "csv=p=0",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return None
        payload = result.stdout.decode().strip()
        return int(payload) if payload else None
    except Exception:
        return None


def _probe_video_stream_signature(path: Path) -> Optional[dict]:
    """
    Return a compact signature of the primary video stream for concat compatibility checks.

    Returns None when probing fails.
    """

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,profile,level,width,height,pix_fmt,r_frame_rate,avg_frame_rate,time_base",
                "-of",
                "json",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return None
        payload = json.loads(result.stdout.decode() or "{}")
        streams = payload.get("streams") or []
        if not streams:
            return None
        stream = streams[0] or {}
        return {
            "codec_name": stream.get("codec_name"),
            "profile": stream.get("profile"),
            "level": stream.get("level"),
            "width": stream.get("width"),
            "height": stream.get("height"),
            "pix_fmt": stream.get("pix_fmt"),
            "r_frame_rate": stream.get("r_frame_rate"),
            "avg_frame_rate": stream.get("avg_frame_rate"),
            "time_base": stream.get("time_base"),
        }
    except Exception:
        return None


def _segments_safe_for_stream_copy_concat(segments: Sequence[Path]) -> bool:
    """
    Return True if ffmpeg concat demuxer + `-c copy` is likely to be safe for these segments.

    We require identical codec parameters *and* timing metadata (frame rate + time_base). If timing
    differs, MP4 stream-copy concat can produce outputs that appear valid in ffprobe yet freeze in
    Safari/iOS players.
    """

    reference: Optional[dict] = None
    for segment in segments:
        signature = _probe_video_stream_signature(segment)
        if signature is None:
            return False
        if reference is None:
            reference = signature
            continue
        if signature != reference:
            return False
    return reference is not None


def _resolve_target_width(target_height: int) -> int:
    """Return an even width roughly matching 16:9 for the requested height."""

    if target_height <= 0:
        return 0
    width = int(round(target_height * 16 / 9))
    if width % 2:
        width += 1
    return max(2, width)


def _downscale_video(
    path: Path,
    *,
    target_height: int = _TARGET_DUB_HEIGHT,
    preserve_aspect_ratio: bool = True,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Downscale ``path`` to ``target_height`` producing an iOS-friendly MP4 (H.264 + AAC).

    Returns the final path (same as input when no change was needed). When
    ``output_path`` is provided, the final file is moved there (useful when the
    input lives on a RAM disk and the destination is NAS storage).
    """

    destination = output_path or path
    if target_height <= 0:
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
                return destination
            except Exception:
                logger.debug("Unable to move %s to %s", path, destination, exc_info=True)
        return path
    current_height = _probe_video_height(path)
    if current_height is not None and current_height <= target_height:
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
                return destination
            except Exception:
                logger.debug("Unable to move %s to %s", path, destination, exc_info=True)
        return path
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"

    def _make_temp_output(prefix: str) -> Path:
        candidates = [_TEMP_DIR, Path("/tmp")]
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    suffix=path.suffix or ".mp4",
                    delete=False,
                    prefix=prefix,
                    dir=candidate,
                ) as handle:
                    return Path(handle.name)
            except Exception:
                continue
        with tempfile.NamedTemporaryFile(suffix=path.suffix or ".mp4", delete=False, prefix=prefix) as handle:
            return Path(handle.name)

    temp_output = _make_temp_output("dub-resize-")
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        *_IOS_VIDEO_CODEC_ARGS,
        "-preset",
        "veryfast",
        "-vf",
        f"scale={'-2' if preserve_aspect_ratio else _resolve_target_width(target_height)}:{target_height},format=yuv420p",
        *_IOS_AUDIO_CODEC_ARGS,
        *_ios_timing_args(temp_output),
        *_movflags_args(temp_output),
        str(temp_output),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        temp_output.unlink(missing_ok=True)
        logger.warning(
            "Unable to downscale dubbed output to %sp (exit %s)",
            target_height,
            result.returncode,
            extra={"event": "youtube.dub.downscale.failed", "path": path.as_posix()},
        )
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
                return destination
            except Exception:
                logger.debug("Unable to move failed downscale source %s to %s", path, destination, exc_info=True)
        return path
    try:
        shutil.move(str(temp_output), destination)
    except Exception:
        logger.debug("Unable to replace %s with downscaled copy", destination, exc_info=True)
        temp_output.unlink(missing_ok=True)
        if destination != path and path.exists():
            try:
                shutil.move(str(path), destination)
            except Exception:
                logger.debug("Unable to move original %s to %s after downscale failure", path, destination, exc_info=True)
        return destination

    # Verify the resulting height; if it is still above target, retry with a stricter transcode.
    try:
        new_height = _probe_video_height(destination)
    except Exception:
        new_height = None
    if new_height is not None and new_height > target_height:
        logger.warning(
            "Downscaled output still above target height (target=%s, actual=%s); retrying fallback transcode",
            target_height,
            new_height,
            extra={"event": "youtube.dub.downscale.retry", "path": destination.as_posix()},
        )
        fallback_output = _make_temp_output("dub-resize-fallback-")
        fallback_command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(destination),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            *_IOS_VIDEO_CODEC_ARGS,
            "-preset",
            "veryfast",
            "-vf",
            f"scale={'-2' if preserve_aspect_ratio else _resolve_target_width(target_height)}:{target_height},format=yuv420p",
            *_IOS_AUDIO_CODEC_ARGS,
            *_ios_timing_args(fallback_output),
            *_movflags_args(fallback_output),
            str(fallback_output),
        ]
        fallback_result = subprocess.run(
            fallback_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if fallback_result.returncode == 0:
            try:
                shutil.move(str(fallback_output), destination)
            except Exception:
                logger.debug("Unable to replace %s with fallback downscaled copy", destination, exc_info=True)
            else:
                return destination
        fallback_output.unlink(missing_ok=True)
        logger.warning(
            "Fallback downscale failed; keeping existing output",
            extra={"event": "youtube.dub.downscale.retry_failed", "path": destination.as_posix()},
        )
    if destination != path and path.exists():
        try:
            path.unlink(missing_ok=True)
        except Exception:
            logger.debug("Unable to clean up source after downscale", exc_info=True)
    return destination


def _pad_clip_to_duration(path: Path, target_seconds: float) -> Path:
    """
    Ensure ``path`` lasts at least ``target_seconds`` by padding video/audio tails.

    Returns the (possibly new) path to use.
    """

    if target_seconds <= 0:
        return path
    current = _probe_duration_seconds(path)
    delta = target_seconds - current
    # If we're already within 20ms, leave as-is.
    if abs(delta) <= 0.02:
        return path
    # If the clip is longer than expected, trim it to the target duration.
    if delta < -0.02:
        ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
        with tempfile.NamedTemporaryFile(
            suffix=path.suffix or ".mp4",
            delete=False,
            prefix="dub-trim-",
            dir=_TEMP_DIR,
        ) as handle:
            trimmed_path = Path(handle.name)
        command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(path),
            "-t",
            f"{target_seconds:.6f}",
            *_IOS_VIDEO_CODEC_ARGS,
            "-preset",
            "veryfast",
            *_IOS_AUDIO_CODEC_ARGS,
            *_ios_timing_args(trimmed_path),
            *_movflags_args(trimmed_path),
            str(trimmed_path),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode == 0:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return trimmed_path
        else:
            trimmed_path.unlink(missing_ok=True)
            return path

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    with tempfile.NamedTemporaryFile(
        suffix=path.suffix or ".mp4",
        delete=False,
        prefix="dub-pad-",
        dir=_TEMP_DIR,
    ) as handle:
        padded_path = Path(handle.name)

    video_pad = f"tpad=stop_mode=clone:stop_duration={delta:.6f}"
    audio_pad = f"apad=pad_dur={delta:.6f}"
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(path),
        "-vf",
        f"{video_pad},format=yuv420p",
        "-af",
        audio_pad,
        "-t",
        f"{target_seconds:.6f}",
        *_IOS_VIDEO_CODEC_ARGS,
        "-preset",
        "veryfast",
        *_IOS_AUDIO_CODEC_ARGS,
        *_ios_timing_args(padded_path),
        *_movflags_args(padded_path),
        str(padded_path),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        padded_path.unlink(missing_ok=True)
        return path
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    return padded_path


def _format_clip_suffix(start_offset: float, end_offset: Optional[float]) -> str:
    # Keep output names compact; we no longer append millisecond offsets for non-zero starts.
    return ""


def _resolve_output_path(
    video_path: Path,
    language: str,
    output_dir: Optional[Path],
    *,
    start_offset: float = 0.0,
    end_offset: Optional[float] = None,
) -> Path:
    safe_lang = re.sub(r"[^A-Za-z0-9_-]+", "-", language.strip() or "dub")
    target_dir = (output_dir or video_path.parent / f"dubbed-{safe_lang}").expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    clip_suffix = _format_clip_suffix(start_offset, end_offset)
    trimmed_stem = trim_stem_preserving_id(video_path.stem)
    return target_dir / f"{trimmed_stem}.{safe_lang}.dub{clip_suffix}.mp4"


def _format_time_prefix(seconds: float) -> str:
    clamped = max(0, int(seconds))
    hours = clamped // 3600
    minutes = (clamped % 3600) // 60
    secs = clamped % 60
    return f"{hours:02d}-{minutes:02d}-{secs:02d}"


def _resolve_batch_output_path(base_output: Path, start_seconds: float) -> Path:
    stem = base_output.stem
    suffix = base_output.suffix or ".mp4"
    prefix = _format_time_prefix(start_seconds)
    candidate = base_output.with_name(f"{prefix}-{stem}{suffix}")
    counter = 2
    while candidate.exists():
        candidate = base_output.with_name(f"{prefix}-{stem}-{counter}{suffix}")
        counter += 1
    return candidate


def _resolve_temp_batch_path(base_output: Path, start_seconds: float, *, suffix: str = ".mp4") -> Path:
    """Return a temp path on the RAM disk for intermediate batch media."""

    prefix = _format_time_prefix(start_seconds)
    stem = base_output.stem
    counter = 1
    while True:
        name = f"{prefix}-{stem}{'' if counter == 1 else f'-{counter}'}{suffix}"
        candidate = _TEMP_DIR / name
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_temp_output_path(base_output: Path) -> Path:
    """Return a temp path on the RAM disk mirroring the final output name."""

    stem = base_output.stem
    suffix = base_output.suffix or ".mp4"
    counter = 1
    while True:
        name = f"{stem}{'' if counter == 1 else f'-{counter}'}{suffix}"
        candidate = _TEMP_DIR / name
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_temp_target(target: Path) -> Path:
    """Return a temp RAM-disk path mirroring the target name."""

    stem = target.stem or "dub"
    suffix = target.suffix or ""
    counter = 1
    while True:
        name = f"{stem}{'' if counter == 1 else f'-{counter}'}{suffix}"
        candidate = _TEMP_DIR / name
        if not candidate.exists():
            return candidate
        counter += 1


def _trim_video_segment(
    video_path: Path,
    *,
    start_offset: float,
    end_offset: Optional[float],
) -> Path:
    """Return a trimmed copy of ``video_path`` based on the provided window."""

    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    duration = end_offset - start_offset if end_offset is not None else None
    with tempfile.NamedTemporaryFile(
        suffix=video_path.suffix or ".mp4",
        delete=False,
        prefix="dub-clip-",
        dir=_TEMP_DIR,
    ) as handle:
        trimmed_path = Path(handle.name)

    # Fast path: copy streams, bias seek before input for better keyframe alignment.
    command = [ffmpeg_bin, "-y"]
    if start_offset > 0:
        command.extend(["-ss", f"{start_offset}"])
    command.extend(["-i", str(video_path)])
    if duration is not None:
        command.extend(["-t", f"{duration}"])
    command.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            "-reset_timestamps",
            "1",
            str(trimmed_path),
        ]
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        return trimmed_path

    # Fallback: re-encode if copy failed (e.g., no keyframe).
    command = [ffmpeg_bin, "-y"]
    if start_offset > 0:
        command.extend(["-ss", f"{start_offset}"])
    command.extend(["-i", str(video_path)])
    if duration is not None:
        command.extend(["-t", f"{duration}"])
    command.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-ac",
            "2",
            "-ar",
            "44100",
            *_movflags_args(trimmed_path),
            str(trimmed_path),
        ]
    )
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        trimmed_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"ffmpeg failed to trim video (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
        )
    return trimmed_path


def _concat_video_segments(segments: Sequence[Path], output_path: Path) -> None:
    """Concatenate ``segments`` into ``output_path`` using ffmpeg concat demuxer."""

    if not segments:
        raise ValueError("No segments provided for concatenation")
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    inputs: List[str] = []
    filter_inputs: List[str] = []
    input_index = 0

    def _probe_media(path: Path) -> Tuple[bool, float]:
        """Return (has_audio, duration_seconds) for the given media path."""

        has_audio = _has_audio_stream(path)
        duration = 0.0
        ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
        try:
            result = subprocess.run(
                [
                    ffprobe_bin,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            duration = float(result.stdout.decode().strip() or 0.0)
        except Exception:
            duration = 0.0
        return has_audio, max(0.0, duration)

    valid_segments = 0
    for segment in segments:
        has_audio, duration = _probe_media(segment)
        has_video = _has_video_stream(segment)
        if not has_video or duration <= 0.1:
            logger.warning(
                "Skipping invalid concat segment (video=%s, duration=%.3fs)",
                has_video,
                duration,
                extra={"event": "youtube.dub.concat.invalid_segment", "segment": segment.as_posix(), "duration": duration},
            )
            continue
        valid_segments += 1
        if not has_audio:
            logger.warning(
                "Segment lacks audio stream; injecting silence to preserve concat timing",
                extra={"event": "youtube.dub.concat.silence", "segment": segment.as_posix(), "duration": duration},
            )
        inputs.extend(["-i", str(segment)])
        video_label = f"[{input_index}:v:0]"
        audio_label = f"[{input_index}:a:0]"
        input_index += 1
        if not has_audio:
            # Synthesize a silent track so concat never drops audio for this segment.
            silent_duration = max(duration, 0.1)
            inputs.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{silent_duration:.3f}",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                ]
            )
            audio_label = f"[{input_index}:a:0]"
            input_index += 1
        filter_inputs.append(f"{video_label}{audio_label}")
    if valid_segments == 0:
        raise RuntimeError("No valid segments available for concatenation")
    filter_concat = "".join(filter_inputs) + f"concat=n={valid_segments}:v=1:a=1[v][a]"
    command = [
        ffmpeg_bin,
        "-y",
        *inputs,
        "-filter_complex",
        filter_concat,
        "-map",
        "[v]",
        "-map",
        "[a]",
        *_IOS_VIDEO_CODEC_ARGS,
        "-preset",
        "veryfast",
        *_IOS_AUDIO_CODEC_ARGS,
        *_ios_timing_args(output_path),
        *_movflags_args(output_path),
        str(output_path),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg concat failed (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
        )


def _concat_video_segments_copy(segments: Sequence[Path], output_path: Path) -> None:
    """
    Concatenate ``segments`` into ``output_path`` by stream copying.

    This is significantly faster than re-encoding, but requires compatible
    streams (same codec parameters across all inputs).
    """

    if not segments:
        raise ValueError("No segments provided for concatenation")
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        prefix="concat-copy-",
        dir=_TEMP_DIR,
    ) as handle:
        list_path = Path(handle.name)
        for segment in segments:
            path_value = str(segment)
            handle.write("file '" + path_value.replace("'", "\\'") + "'\n")
    try:
        command = [
            ffmpeg_bin,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            *_movflags_args(output_path),
            str(output_path),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg concat copy failed (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
            )
    finally:
        list_path.unlink(missing_ok=True)


def _concat_video_segments_ts_copy(segments: Sequence[Path], output_path: Path) -> None:
    """
    Concatenate ``segments`` into ``output_path`` by stream-copying via MPEG-TS intermediates.

    This is a fallback for cases where MP4 concat demuxer + stream copy fails due
    to subtle container differences; it avoids a full re-encode.
    """

    if not segments:
        raise ValueError("No segments provided for concatenation")
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for segment in segments:
        if not _has_audio_stream(segment):
            raise RuntimeError(f"Segment lacks audio stream: {segment.as_posix()}")

    with tempfile.TemporaryDirectory(prefix="youtube-dub-ts-", dir=str(_TEMP_DIR)) as temp_dir:
        ts_dir = Path(temp_dir)
        ts_paths: List[Path] = []
        for index, segment in enumerate(segments):
            ts_path = ts_dir / f"seg-{index:04d}.ts"
            command = [
                ffmpeg_bin,
                "-y",
                "-i",
                str(segment),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
                "-c",
                "copy",
                "-bsf:v",
                "h264_mp4toannexb",
                "-f",
                "mpegts",
                str(ts_path),
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg ts remux failed (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
                )
            ts_paths.append(ts_path)

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            prefix="concat-ts-",
            dir=_TEMP_DIR,
        ) as handle:
            list_path = Path(handle.name)
            for ts_path in ts_paths:
                handle.write("file '" + str(ts_path).replace("'", "\\'") + "'\n")
        try:
            command = [
                ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                "-bsf:a",
                "aac_adtstoasc",
                *_movflags_args(output_path),
                str(output_path),
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg ts concat copy failed (exit {result.returncode}): {result.stderr.decode(errors='ignore')}"
                )
        finally:
            list_path.unlink(missing_ok=True)


def _mux_audio_track(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    language: str,
    *,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    target_duration_seconds: Optional[float] = None,
    include_source_audio: bool = True,
    source_duration_seconds: Optional[float] = None,
) -> None:
    ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
    command = [ffmpeg_bin, "-y"]
    if start_time is not None and start_time > 0:
        # Seek the video input while leaving the dubbed audio at t=0 for batch alignment.
        command.extend(["-ss", f"{start_time}"])
    command.extend(["-i", str(video_path)])
    command.extend(["-i", str(audio_path)])
    segment_duration = None
    if end_time is not None and end_time > 0:
        segment_duration = end_time
        if start_time is not None and start_time > 0:
            segment_duration = max(0.0, end_time - start_time)
    if source_duration_seconds is not None and source_duration_seconds > 0:
        segment_duration = source_duration_seconds
    stretch_ratio = None
    if target_duration_seconds is not None and target_duration_seconds > 0 and segment_duration:
        if target_duration_seconds > segment_duration + 0.01:
            stretch_ratio = target_duration_seconds / max(segment_duration, 0.001)
    filter_complex: List[str] = []
    if stretch_ratio is not None:
        filter_complex.append(f"[0:v]setpts={stretch_ratio:.6f}*PTS[v0]")
        if include_source_audio:
            atempo_ratio = 1.0 / stretch_ratio
            atempo_chain = ",".join(f"atempo={factor:.5f}" for factor in _build_atempo_filters(atempo_ratio))
            filter_complex.append(f"[0:a]{atempo_chain}[a0]")
    if filter_complex:
        command.extend(["-filter_complex", ";".join(filter_complex)])
    if filter_complex:
        command.extend(["-map", "[v0]"])
    else:
        command.extend(["-map", "0:v:0"])
    command.extend(
        [
            "-map",
            "1:a",
        ]
    )
    if include_source_audio and filter_complex:
        command.extend(["-map", "[a0]"])
    elif include_source_audio:
        command.extend(["-map", "0:a?"])
    command.extend(
        [
            *_IOS_VIDEO_CODEC_ARGS,
            "-preset",
            "veryfast",
            *_IOS_AUDIO_CODEC_ARGS,
            *_ios_timing_args(output_path),
            *_movflags_args(output_path),
            "-disposition:a:0",
            "default",
            "-metadata:s:a:0",
            f"language={language}",
            "-disposition:a:1",
            "0",
        ]
    )
    duration_arg = None
    if target_duration_seconds is not None and target_duration_seconds > 0:
        duration_arg = target_duration_seconds
    elif segment_duration is not None:
        duration_arg = segment_duration
    if duration_arg is not None and duration_arg > 0:
        command.extend(["-t", f"{duration_arg}"])
    command.append(str(output_path))

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed with exit code {result.returncode}: {result.stderr.decode(errors='ignore')}"
        )

    # Ensure the output carries an audio stream; if not, re-mux with dubbed audio only.
    if not _has_audio_stream(output_path):
        logger.warning(
            "Muxed clip missing audio; retrying without source mix",
            extra={"event": "youtube.dub.mux.audio_missing", "clip": output_path.as_posix()},
        )
        recover_command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            str(output_path),
        ]
        subprocess.run(recover_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

        # If audio is still missing, inject silence to preserve downstream timing.
        if not _has_audio_stream(output_path):
            ffmpeg_bin = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BIN") or "ffmpeg"
            inject_command = [
                ffmpeg_bin,
                "-y",
                "-i",
                str(output_path),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                str(output_path),
            ]
            subprocess.run(inject_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


__all__ = [
    "_classify_video_source",
    "_concat_video_segments",
    "_concat_video_segments_copy",
    "_format_clip_suffix",
    "_format_time_prefix",
    "_segments_safe_for_stream_copy_concat",
    "_has_video_stream",
    "_mux_audio_track",
    "_pad_clip_to_duration",
    "_probe_duration_seconds",
    "_probe_video_height",
    "_resolve_batch_output_path",
    "_resolve_output_path",
    "_resolve_target_width",
    "_resolve_temp_batch_path",
    "_resolve_temp_output_path",
    "_resolve_temp_target",
    "_subtitle_matches_video",
    "_trim_video_segment",
    "_downscale_video",
    "logger",
]
