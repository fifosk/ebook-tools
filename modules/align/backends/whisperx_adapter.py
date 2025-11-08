"""Thin wrapper around the WhisperX CLI for forced alignment."""

from __future__ import annotations

import json
import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Dict, List, Optional

from modules import logging_manager as log_mgr

logger = log_mgr.logger


def _cleanup_files(*paths: Path) -> None:
    for path in paths:
        with suppress(OSError):
            path.unlink()


def align_sentence(
    audio_path: str | Path,
    text: str,
    *,
    model: Optional[str] = None,
    device: Optional[str] = None,
) -> List[Dict[str, float | str]]:
    """Align ``text`` against ``audio_path`` using WhisperX."""

    audio = Path(audio_path)
    if not audio.exists():
        logger.warning("WhisperX alignment skipped: audio path '%s' not found.", audio)
        return []
    if not text.strip():
        return []

    transcript_handle = tempfile.NamedTemporaryFile(
        prefix="whisperx_transcript_", suffix=".txt", delete=False, mode="w", encoding="utf-8"
    )
    try:
        transcript_path = Path(transcript_handle.name)
        transcript_handle.write(text)
    finally:
        transcript_handle.close()

    output_handle = tempfile.NamedTemporaryFile(
        prefix="whisperx_alignment_", suffix=".json", delete=False
    )
    output_path = Path(output_handle.name)
    output_handle.close()

    command: List[str] = [
        "whisperx",
        str(audio),
        "--output_json",
        str(output_path),
        "--text",
        str(transcript_path),
    ]
    if model:
        command.extend(["--align_model", model])
    if device:
        command.extend(["--device", device])

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        logger.warning("WhisperX CLI not found; install whisperx to enable forced alignment.")
        _cleanup_files(transcript_path, output_path)
        return []
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("WhisperX invocation failed: %s", exc, exc_info=True)
        _cleanup_files(transcript_path, output_path)
        return []

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown error"
        logger.warning(
            "WhisperX exited with status %s: %s",
            result.returncode,
            message,
        )
        _cleanup_files(transcript_path, output_path)
        return []

    try:
        with output_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to parse WhisperX output: %s", exc)
        _cleanup_files(transcript_path, output_path)
        return []
    finally:
        _cleanup_files(transcript_path, output_path)

    tokens: List[Dict[str, float | str]] = []
    segments = payload.get("segments")
    if not isinstance(segments, list):
        return tokens

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        words = segment.get("words")
        if not isinstance(words, list):
            continue
        for word in words:
            if not isinstance(word, dict):
                continue
            token_text = word.get("word") or word.get("text") or ""
            if not isinstance(token_text, str):
                token_text = str(token_text)
            token_text = token_text.strip()
            try:
                start = float(word.get("start"))
                end = float(word.get("end", start))
            except (TypeError, ValueError):
                continue
            start = round(max(start, 0.0), 6)
            end = round(max(end, start), 6)
            tokens.append({"text": token_text, "start": start, "end": end})

    return tokens


def retry_alignment(
    audio_path: str | Path,
    text: str,
    *,
    model: Optional[str] = None,
    device: Optional[str] = None,
    max_attempts: int = 3,
) -> tuple[List[Dict[str, float | str]], bool]:
    """
    Attempt WhisperX alignment up to ``max_attempts`` times.

    Returns a tuple of (tokens, exhausted_retry_flag).
    """

    attempts = max(1, int(max_attempts))
    for attempt in range(1, attempts + 1):
        tokens = align_sentence(audio_path, text, model=model, device=device)
        if tokens:
            return tokens, False
        logger.warning(
            "WhisperX produced no tokens (attempt %s/%s).",
            attempt,
            attempts,
        )
    logger.warning(
        "WhisperX exhausted %s attempt(s) without producing any tokens; falling back to heuristics.",
        attempts,
    )
    return [], True


__all__ = ["align_sentence", "retry_alignment"]
