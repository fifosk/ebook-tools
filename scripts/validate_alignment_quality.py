#!/usr/bin/env python3
"""Quick utility to inspect highlight drift after forced alignment.

Supports both legacy timing_index.json and new per-chunk timingTracks format.

Usage:
    # Legacy format (single timing file)
    validate_alignment_quality.py <timing_index.json> <audio_file>

    # New format (job directory with chunks)
    validate_alignment_quality.py --job-dir <job_directory>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

try:
    import soundfile as sf
except ImportError:
    sf = None  # type: ignore[assignment]


def _load_segments(path: Path) -> list[dict[str, object]]:
    """Load timing segments from a legacy timing_index.json file."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        segments = payload.get("segments")
        if isinstance(segments, list):
            return segments  # type: ignore[return-value]
    raise ValueError(f"Unrecognised timing payload structure in {path}")


def _load_chunk_timing_tracks(
    chunk_path: Path,
) -> Dict[str, List[Dict[str, Any]]]:
    """Load timingTracks from a chunk_XXXX.json file."""
    with chunk_path.open("r", encoding="utf-8") as f:
        chunk_data = json.load(f)

    timing_tracks = chunk_data.get("timingTracks") or chunk_data.get("timing_tracks")
    if not isinstance(timing_tracks, Mapping):
        return {}

    result: Dict[str, List[Dict[str, Any]]] = {}
    for track_name, tokens in timing_tracks.items():
        if isinstance(tokens, list):
            result[track_name] = tokens
    return result


def _find_chunks(job_dir: Path) -> List[Path]:
    """Find all chunk metadata files in a job directory."""
    metadata_dir = job_dir / "metadata"
    if not metadata_dir.is_dir():
        return []

    chunks = sorted(metadata_dir.glob("chunk_*.json"))
    return chunks


def _find_audio_for_track(
    job_dir: Path, track_name: str, chunk_index: int
) -> Optional[Path]:
    """Find the audio file corresponding to a track in a chunk."""
    # Try common patterns
    audio_dir = job_dir / "media" / "audio"
    if not audio_dir.is_dir():
        return None

    patterns = [
        f"{track_name}/chunk_{chunk_index:04d}.mp3",
        f"{track_name}/chunk_{chunk_index:04d}.wav",
        f"chunk_{chunk_index:04d}_{track_name}.mp3",
        f"chunk_{chunk_index:04d}_{track_name}.wav",
    ]

    for pattern in patterns:
        candidate = audio_dir / pattern
        if candidate.is_file():
            return candidate

    return None


def validate_legacy(timing_path: Path, audio_path: Path) -> int:
    """Validate using legacy timing_index.json format."""
    if sf is None:
        print("ERROR: soundfile not installed. Run: pip install soundfile", file=sys.stderr)
        return 2

    segments = _load_segments(timing_path)
    if not segments:
        print("No segments found; nothing to validate.", file=sys.stderr)
        return 1

    audio_info = sf.info(str(audio_path))
    audio_duration = float(audio_info.duration)
    last_segment = segments[-1]
    end_time = float(last_segment.get("t1") or last_segment.get("end") or 0.0)
    drift = abs(audio_duration - end_time)
    print(f"Drift {drift * 1000:.1f} ms  ({end_time:.2f}s vs {audio_duration:.2f}s)")
    if drift > 0.02:
        print("⚠️  Consider re-aligning")
        return 1
    return 0


def validate_job_dir(job_dir: Path, track_filter: Optional[str] = None) -> int:
    """Validate timing tracks across all chunks in a job directory."""
    chunks = _find_chunks(job_dir)
    if not chunks:
        print(f"No chunk files found in {job_dir / 'metadata'}", file=sys.stderr)
        return 1

    print(f"Found {len(chunks)} chunk(s) in {job_dir}")
    print("-" * 60)

    all_ok = True
    total_drift_ms = 0.0
    track_count = 0

    for chunk_idx, chunk_path in enumerate(chunks):
        timing_tracks = _load_chunk_timing_tracks(chunk_path)
        if not timing_tracks:
            print(f"  {chunk_path.name}: no timing tracks found")
            continue

        for track_name, tokens in timing_tracks.items():
            if track_filter and track_name != track_filter:
                continue

            if not tokens:
                print(f"  {chunk_path.name} [{track_name}]: empty")
                continue

            # Get timing bounds from tokens
            first_token = tokens[0]
            last_token = tokens[-1]
            first_start = float(first_token.get("start") or first_token.get("t0") or 0.0)
            last_end = float(last_token.get("end") or last_token.get("t1") or 0.0)
            token_count = len(tokens)

            # Try to find corresponding audio
            audio_path = _find_audio_for_track(job_dir, track_name, chunk_idx)
            if audio_path and sf is not None:
                audio_info = sf.info(str(audio_path))
                audio_duration = float(audio_info.duration)
                drift = abs(audio_duration - last_end)
                drift_ms = drift * 1000
                total_drift_ms += drift_ms
                track_count += 1

                status = "✓" if drift <= 0.02 else "⚠️"
                print(
                    f"  {chunk_path.name} [{track_name}]: {token_count} tokens, "
                    f"{last_end:.3f}s timing vs {audio_duration:.3f}s audio, "
                    f"drift {drift_ms:.1f}ms {status}"
                )
                if drift > 0.02:
                    all_ok = False
            else:
                print(
                    f"  {chunk_path.name} [{track_name}]: {token_count} tokens, "
                    f"timing range {first_start:.3f}s - {last_end:.3f}s (no audio found)"
                )

    print("-" * 60)
    if track_count > 0:
        avg_drift = total_drift_ms / track_count
        print(f"Average drift: {avg_drift:.1f}ms across {track_count} track(s)")

    return 0 if all_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate highlight timing drift against audio duration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--job-dir",
        type=Path,
        help="Job directory containing metadata/chunk_*.json files",
    )
    parser.add_argument(
        "--track",
        type=str,
        help="Filter to specific track (translation, original)",
    )
    parser.add_argument(
        "positional",
        nargs="*",
        help="Legacy mode: <timing_index.json> <audio_file>",
    )

    args = parser.parse_args()

    # New format: job directory
    if args.job_dir:
        job_dir = args.job_dir.expanduser().resolve()
        if not job_dir.is_dir():
            print(f"ERROR: {job_dir} is not a directory", file=sys.stderr)
            return 2
        return validate_job_dir(job_dir, track_filter=args.track)

    # Legacy format: timing_index.json + audio_file
    if len(args.positional) == 2:
        timing_path = Path(args.positional[0]).expanduser().resolve()
        audio_path = Path(args.positional[1]).expanduser().resolve()
        return validate_legacy(timing_path, audio_path)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
