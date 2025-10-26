"""Utilities for interacting with macOS ``say`` voices."""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Dict, List, Optional


_AVFOUNDATION_SCRIPT = """
from AVFoundation import AVSpeechSynthesisVoice

def _quality_label(value: int) -> str:
    if value == 3:
        return "Premium"
    if value == 2:
        return "Enhanced"
    if value == 1:
        return "High"
    return "Default"


def _gender_label(value: int) -> str:
    if value == 2:
        return "female"
    if value == 1:
        return "male"
    return "unknown"


for voice in AVSpeechSynthesisVoice.speechVoices():
    quality = _quality_label(voice.quality())
    gender = _gender_label(voice.gender())
    print(f"{voice.name()} - {voice.language()} - {gender} - {quality}")
"""


_VOICE_PATTERN = re.compile(
    r"^(?P<name>.+?)\s{2,}(?:\((?P<quality>[^)]+)\)\s+)?(?P<lang>[A-Za-z0-9_\-]+)\s*$"
)


def parse_avfoundation_voice_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """Parse output emitted by the AVFoundation discovery script."""

    candidate = line.strip()
    if not candidate:
        return None

    parts = [segment.strip() for segment in candidate.split(" - ")]
    if len(parts) < 4:
        return None

    name, lang, gender, quality = parts[0], parts[1], parts[2], parts[3]
    if not name or not lang:
        return None

    normalized_gender = gender.lower() if gender else None
    if normalized_gender == "unknown":
        normalized_gender = None

    normalized_quality = quality if quality else None
    if normalized_quality:
        normalized_quality = normalized_quality.strip() or None

    return {
        "name": name,
        "lang": lang,
        "gender": normalized_gender,
        "quality": normalized_quality,
    }


def parse_say_voice_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """Parse a single line of ``say -v '?'`` output."""

    if not line:
        return None

    prefix = line.split("#", 1)[0].rstrip()
    if not prefix:
        return None

    match = _VOICE_PATTERN.match(prefix)
    if not match:
        return None

    name = match.group("name").strip()
    lang = match.group("lang").strip()
    quality = match.group("quality")
    if not name or not lang:
        return None

    return {"name": name, "lang": lang, "quality": quality, "gender": None}


def _collect_say_voices() -> List[Dict[str, Optional[str]]]:
    """Return available macOS voices using AVFoundation with say fallback."""

    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return []

    executable = sys.executable or "python3"
    try:
        output = subprocess.check_output(
            [executable, "-c", _AVFOUNDATION_SCRIPT], text=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        output = ""

    voices: List[Dict[str, Optional[str]]] = []
    if output:
        for line in output.splitlines():
            parsed = parse_avfoundation_voice_line(line)
            if parsed:
                voices.append(parsed)

    if voices:
        return voices

    try:
        legacy_output = subprocess.check_output(["say", "-v", "?"], text=True)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return []

    for line in legacy_output.splitlines():
        parsed = parse_say_voice_line(line)
        if parsed:
            voices.append(parsed)
    return voices


_SAY_VOICE_CACHE: tuple[Dict[str, Optional[str]], ...] = tuple(_collect_say_voices())


def get_say_voices() -> List[Dict[str, Optional[str]]]:
    """Return cached voice metadata from macOS ``say`` output."""

    return [voice.copy() for voice in _SAY_VOICE_CACHE]


__all__ = ["get_say_voices", "parse_say_voice_line"]
