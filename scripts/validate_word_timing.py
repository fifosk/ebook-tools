#!/usr/bin/env python3
"""Validate word-level timing coverage for a rendered job."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import soundfile as sf


def _load_timing_index(path: Path) -> list[dict[str, float]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload  # type: ignore[return-value]
    if isinstance(payload, dict):
        segments = payload.get("segments")
        if isinstance(segments, list):
            return segments  # type: ignore[return-value]
    raise ValueError(f"Unrecognised timing index format in {path}")


def validate_job(job_id: str, *, drift_threshold: float = 0.05) -> int:
    metadata_dir = Path("storage") / job_id / "metadata"
    timing_path = metadata_dir / "timing_index.json"
    if not timing_path.exists():
        print(f"❌ No timing_index.json for job {job_id}")
        return 1

    segments = _load_timing_index(timing_path)
    if not segments:
        print(f"❌ timing_index.json empty for job {job_id}")
        return 1

    audio_candidates = [
        Path("storage") / job_id / "media" / f"{job_id}.wav",
        Path("storage") / job_id / "media" / f"{job_id}.mp3",
    ]
    audio_path = next((candidate for candidate in audio_candidates if candidate.exists()), None)
    if audio_path is None:
        print(f"❌ No audio found for job {job_id} (looked for WAV/MP3).")
        return 1

    audio_info = sf.info(str(audio_path))
    audio_duration = float(audio_info.duration)
    try:
        last_segment = segments[-1]
        last_end = float(last_segment.get("t1") or last_segment.get("end") or 0.0)
    except (TypeError, ValueError):
        print(f"❌ Invalid timing entry in {timing_path}")
        return 1

    drift = audio_duration - last_end
    print(
        f"Job {job_id}: audio {audio_duration:.3f}s  last_token {last_end:.3f}s  "
        f"drift {drift * 1000:.1f} ms"
    )

    # Check for overlaps/monotonic violations
    overlaps = 0
    previous_end = None
    for entry in segments:
        try:
            start = float(entry.get("t0") or entry.get("start") or 0.0)
        except (TypeError, ValueError):
            start = 0.0
        if previous_end is not None and start < previous_end:
            overlaps += 1
        try:
            previous_end = float(entry.get("t1") or entry.get("end") or start)
        except (TypeError, ValueError):
            previous_end = start

    if abs(drift) > drift_threshold or overlaps:
        print(f"⚠️  Drift or overlap detected (drift={drift:.3f}s, overlaps={overlaps})")
        return 1

    print("✅ Timing OK")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: validate_word_timing.py <job_id>", file=sys.stderr)
        return 2
    job_id = argv[0]
    return validate_job(job_id)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
