"""Utilities for interacting with macOS ``say`` voices."""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Dict, List, Optional


_VOICE_PATTERN = re.compile(
    r"^(?P<name>.+?)\s{2,}(?:\((?P<quality>[^)]+)\)\s+)?(?P<lang>[A-Za-z0-9_\-]+)\s*$"
)


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

    return {"name": name, "lang": lang, "quality": quality}


def _collect_say_voices() -> List[Dict[str, Optional[str]]]:
    """Return available macOS voices using the ``say`` command."""

    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return []

    try:
        output = subprocess.check_output(["say", "-v", "?"], text=True)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return []

    voices: List[Dict[str, Optional[str]]] = []
    for line in output.splitlines():
        parsed = parse_say_voice_line(line)
        if parsed:
            voices.append(parsed)
    return voices


_SAY_VOICE_CACHE: tuple[Dict[str, Optional[str]], ...] = tuple(_collect_say_voices())


def get_say_voices() -> List[Dict[str, Optional[str]]]:
    """Return cached voice metadata from macOS ``say`` output."""

    return [voice.copy() for voice in _SAY_VOICE_CACHE]


__all__ = ["get_say_voices", "parse_say_voice_line"]
