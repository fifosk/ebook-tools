#!/usr/bin/env python3
"""Validate that audio duration and timing payload stay in sync."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import soundfile as sf


def check_timing(timing_path: str | Path, audio_path: str | Path) -> None:
    timing_file = Path(timing_path)
    audio_file = Path(audio_path)

    with timing_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    audio_info = sf.info(str(audio_file))
    duration = float(audio_info.duration)

    segments = payload.get("segments") or []
    if not segments:
        print("⚠️  No segments present in timing payload")
        return

    last_segment = segments[-1]
    last_t1 = float(last_segment.get("t1", 0.0))

    drift = duration - last_t1
    print(f"Audio duration={duration:.3f}s, last_t1={last_t1:.3f}s, drift={drift:.3f}s")
    if abs(drift) > 0.1:
        print("⚠️  Significant drift detected")
    else:
        print("✅ Timing OK")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: python scripts/validate_timing_alignment.py <timing.json> <audio file>",
            file=sys.stderr,
        )
        return 1
    check_timing(argv[1], argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
