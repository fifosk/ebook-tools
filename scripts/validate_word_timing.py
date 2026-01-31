#!/usr/bin/env python3
"""Validate per-track timing JSON files.

Supports both the legacy *.timing.json format (TrackTiming schema) and
the new per-chunk timingTracks format from chunk_XXXX.json files.

Usage:
    # Legacy format (*.timing.json files)
    validate_word_timing.py path/to/track.timing.json

    # New format (job directory with chunks)
    validate_word_timing.py --job-dir <job_directory>

    # New format (individual chunk files)
    validate_word_timing.py --chunk path/to/chunk_0000.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

# Try to import the schema module for legacy validation
try:
    from modules.core.rendering.timing_schema import (
        TrackTiming,
        SentenceTiming,
        WordTiming,
        validate_track,
    )

    HAS_SCHEMA = True
except ImportError:
    HAS_SCHEMA = False


def load_legacy_track(path: str) -> "TrackTiming":
    """Light loader that rehydrates dataclasses from JSON (legacy format)."""
    if not HAS_SCHEMA:
        raise ImportError("modules.core.rendering.timing_schema not available")

    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    sentences = []
    for s in obj.get("sentences", []):
        words = [WordTiming(**w) for w in s.get("words", [])]
        sentences.append(
            SentenceTiming(
                sid=s["sid"],
                text=s["text"],
                start=s["start"],
                end=s["end"],
                words=words,
                approx_quality=s.get("approx_quality"),
            )
        )
    return TrackTiming(
        chunk_id=obj["chunk_id"],
        lang=obj["lang"],
        policy=obj["policy"],
        sample_rate=obj.get("sample_rate", 22050),
        duration=obj["duration"],
        sentences=sentences,
        qa=obj.get("qa"),
    )


def load_chunk_timing_tracks(
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


def find_chunks(job_dir: Path) -> List[Path]:
    """Find all chunk metadata files in a job directory."""
    metadata_dir = job_dir / "metadata"
    if not metadata_dir.is_dir():
        return []

    chunks = sorted(metadata_dir.glob("chunk_*.json"))
    return chunks


def validate_chunk_tokens(
    tokens: List[Dict[str, Any]], track_name: str, tol_ms: int = 80
) -> List[str]:
    """Validate timing tokens from a chunk, return list of issues."""
    issues: List[str] = []

    if not tokens:
        return ["empty token list"]

    prev_end = 0.0
    for i, token in enumerate(tokens):
        start = float(token.get("start") or token.get("t0") or 0.0)
        end = float(token.get("end") or token.get("t1") or 0.0)

        # Check ordering
        if start < prev_end - (tol_ms / 1000):
            issues.append(
                f"token {i}: start {start:.3f}s before prev end {prev_end:.3f}s"
            )

        # Check duration
        if end < start:
            issues.append(f"token {i}: end {end:.3f}s before start {start:.3f}s")

        # Check for very long tokens (likely errors)
        duration = end - start
        if duration > 10.0:
            issues.append(f"token {i}: suspiciously long duration {duration:.3f}s")

        prev_end = end

    # Check monotonicity
    times = [
        float(t.get("start") or t.get("t0") or 0.0)
        for t in tokens
    ]
    if times != sorted(times):
        issues.append("tokens not in monotonic order")

    return issues


def validate_legacy_paths(paths: List[str], tol_ms: int) -> bool:
    """Validate legacy *.timing.json files."""
    if not HAS_SCHEMA:
        print(
            "ERROR: modules.core.rendering.timing_schema not available. "
            "Run from project root or install the package.",
            file=sys.stderr,
        )
        return False

    ok = True
    for p in paths:
        try:
            t = load_legacy_track(p)
            validate_track(t, tol_ms=tol_ms)
            print(f"OK  {p}  duration={t.duration:.3f}s  sentences={len(t.sentences)}")
        except Exception as e:
            ok = False
            print(f"ERR {p}: {e}", file=sys.stderr)
    return ok


def validate_chunk_file(chunk_path: Path, tol_ms: int) -> bool:
    """Validate a single chunk file's timing tracks."""
    timing_tracks = load_chunk_timing_tracks(chunk_path)
    if not timing_tracks:
        print(f"  {chunk_path.name}: no timing tracks found")
        return True

    all_ok = True
    for track_name, tokens in timing_tracks.items():
        issues = validate_chunk_tokens(tokens, track_name, tol_ms)
        token_count = len(tokens)

        if tokens:
            first_start = float(tokens[0].get("start") or tokens[0].get("t0") or 0.0)
            last_end = float(tokens[-1].get("end") or tokens[-1].get("t1") or 0.0)
            duration = last_end - first_start
        else:
            duration = 0.0

        if issues:
            all_ok = False
            print(
                f"ERR {chunk_path.name} [{track_name}]: "
                f"{token_count} tokens, {duration:.3f}s"
            )
            for issue in issues[:5]:  # Limit output
                print(f"    - {issue}")
            if len(issues) > 5:
                print(f"    ... and {len(issues) - 5} more issues")
        else:
            print(
                f"OK  {chunk_path.name} [{track_name}]: "
                f"{token_count} tokens, {duration:.3f}s"
            )

    return all_ok


def validate_job_dir(job_dir: Path, tol_ms: int, track_filter: Optional[str] = None) -> bool:
    """Validate all chunk files in a job directory."""
    chunks = find_chunks(job_dir)
    if not chunks:
        print(f"No chunk files found in {job_dir / 'metadata'}", file=sys.stderr)
        return False

    print(f"Found {len(chunks)} chunk(s) in {job_dir}")
    print("-" * 60)

    all_ok = True
    for chunk_path in chunks:
        timing_tracks = load_chunk_timing_tracks(chunk_path)
        if not timing_tracks:
            print(f"  {chunk_path.name}: no timing tracks found")
            continue

        for track_name, tokens in timing_tracks.items():
            if track_filter and track_name != track_filter:
                continue

            issues = validate_chunk_tokens(tokens, track_name, tol_ms)
            token_count = len(tokens)

            if tokens:
                first_start = float(tokens[0].get("start") or tokens[0].get("t0") or 0.0)
                last_end = float(tokens[-1].get("end") or tokens[-1].get("t1") or 0.0)
                duration = last_end - first_start
            else:
                duration = 0.0

            if issues:
                all_ok = False
                print(
                    f"ERR {chunk_path.name} [{track_name}]: "
                    f"{token_count} tokens, {duration:.3f}s"
                )
                for issue in issues[:3]:
                    print(f"    - {issue}")
                if len(issues) > 3:
                    print(f"    ... and {len(issues) - 3} more issues")
            else:
                print(
                    f"OK  {chunk_path.name} [{track_name}]: "
                    f"{token_count} tokens, {duration:.3f}s"
                )

    print("-" * 60)
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate per-track timing JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--job-dir",
        type=Path,
        help="Job directory containing metadata/chunk_*.json files",
    )
    parser.add_argument(
        "--chunk",
        type=Path,
        help="Single chunk_XXXX.json file to validate",
    )
    parser.add_argument(
        "--track",
        type=str,
        help="Filter to specific track (translation, original)",
    )
    parser.add_argument(
        "--tol-ms",
        type=int,
        default=80,
        help="Tolerance in milliseconds for timing gaps (default: 80)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Legacy mode: *.timing.json files to validate",
    )

    args = parser.parse_args()

    # New format: job directory
    if args.job_dir:
        job_dir = args.job_dir.expanduser().resolve()
        if not job_dir.is_dir():
            print(f"ERROR: {job_dir} is not a directory", file=sys.stderr)
            return 2
        ok = validate_job_dir(job_dir, args.tol_ms, track_filter=args.track)
        return 0 if ok else 1

    # New format: single chunk file
    if args.chunk:
        chunk_path = args.chunk.expanduser().resolve()
        if not chunk_path.is_file():
            print(f"ERROR: {chunk_path} is not a file", file=sys.stderr)
            return 2
        ok = validate_chunk_file(chunk_path, args.tol_ms)
        return 0 if ok else 1

    # Legacy format: *.timing.json files
    if args.paths:
        ok = validate_legacy_paths(args.paths, args.tol_ms)
        return 0 if ok else 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
