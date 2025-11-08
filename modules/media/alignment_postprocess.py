"""Helpers for running optional forced-alignment post processing."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import run
from typing import Sequence


def forced_align_with_whisperx(
    audio_path: str | Path,
    transcript_path: str | Path,
    out_json: str | Path,
    *,
    model: str = "medium.en",
) -> None:
    """Run WhisperX to align text and audio and emit normalized timing payload."""

    audio = Path(audio_path)
    transcript = Path(transcript_path)
    destination = Path(out_json)

    command: Sequence[str] = (
        "whisperx",
        str(audio),
        "--align_model",
        model,
        "--output_json",
        str(destination),
        "--text",
        str(transcript),
    )
    run(command, check=True)

    with destination.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    segments = payload.get("segments", [])
    for segment in segments:
        seg_id = segment.get("id") or segment.get("segment_id") or "seg"
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start + 0.5))
        segment["id"] = seg_id
        segment["t0"] = round(start, 3)
        segment["t1"] = round(end, 3)
        words = segment.get("words") or []
        for index, word in enumerate(words):
            word_id = f"{seg_id}_{index}"
            word["id"] = word_id
            word["lane"] = "tran"
            word["segId"] = seg_id

    normalized_payload = {"trackKind": "translation_only", "segments": segments}
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(normalized_payload, handle, ensure_ascii=False, indent=2)
