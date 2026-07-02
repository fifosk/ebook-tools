"""Shared audio role helpers for media playback routes."""

from __future__ import annotations

import re


def canonical_audio_track_key(value: str) -> str:
    """Return the stable audio role used by Apple and Web clients."""

    stripped = value.strip()
    normalized = re.sub(r"[^a-z0-9]+", "", stripped.lower())
    if normalized in {"origtrans", "originaltranslation", "originalandtranslation", "mix"}:
        return "orig_trans"
    if normalized in {
        "orig",
        "origaudio",
        "original",
        "originalaudio",
    }:
        return "orig"
    if normalized in {
        "trans",
        "transaudio",
        "translation",
        "translationaudio",
        "translated",
        "translatedaudio",
        "target",
        "targetaudio",
        "dubbed",
        "dubbedaudio",
    }:
        return "translation"
    return stripped


def canonical_timing_track_key(value: str) -> str:
    """Map audio role aliases onto timing payload track names."""

    role = canonical_audio_track_key(value)
    if role == "orig_trans":
        return "mix"
    if role == "orig":
        return "original"
    return role
