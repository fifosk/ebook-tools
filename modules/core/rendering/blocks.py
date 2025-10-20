"""Helpers for constructing written and video output blocks."""

from __future__ import annotations

from typing import Tuple


def build_written_and_video_blocks(
    *,
    sentence_number: int,
    sentence: str,
    fluent: str,
    transliteration: str,
    current_target: str,
    written_mode: str,
    total_sentences: int,
    include_transliteration: bool,
) -> Tuple[str, str]:
    """Return formatted written and video blocks mirroring the legacy output."""

    percent = (sentence_number / total_sentences * 100) if total_sentences else 0.0
    header = f"{current_target} - {sentence_number} - {percent:.2f}%\n"

    if written_mode == "1":
        written_block = f"{fluent}\n"
    elif written_mode == "2":
        written_block = f"{sentence_number} - {percent:.2f}%\n{fluent}\n"
    elif written_mode == "3":
        written_block = f"{sentence_number} - {percent:.2f}%\n{sentence}\n\n{fluent}\n"
    else:
        written_block = f"{sentence}\n\n{fluent}\n"

    if include_transliteration and transliteration:
        written_block = written_block.rstrip() + f"\n{transliteration}\n"
        video_block = f"{header}{sentence}\n\n{fluent}\n{transliteration}\n"
    else:
        video_block = f"{header}{sentence}\n\n{fluent}\n"

    return written_block, video_block
