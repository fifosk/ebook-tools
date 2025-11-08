#!/usr/bin/env python3
"""Quick utility to inspect highlight drift after forced alignment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import soundfile as sf


def _load_segments(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        segments = payload.get("segments")
        if isinstance(segments, list):
            return segments  # type: ignore[return-value]
    raise ValueError(f"Unrecognised timing payload structure in {path}")


def main(args: list[str]) -> int:
    if len(args) != 2:
        print("Usage: validate_alignment_quality.py <timing_index.json> <audio_file>", file=sys.stderr)
        return 2

    timing_path = Path(args[0]).expanduser().resolve()
    audio_path = Path(args[1]).expanduser().resolve()
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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
