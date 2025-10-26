"""Tests for macOS ``say`` voice helpers."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


MODULE_PATH = "modules.webapi.audio"


def reload_audio_module(
    *,
    output: str | None = None,
    side_effect: Exception | None = None,
    platform: str = "darwin",
    inventory: Optional[List[Tuple[str, str, str, Optional[str]]]] = None,
):
    """Reload the audio helper module with patched dependencies."""

    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]

    patch_kwargs = {"return_value": output or ""}
    if side_effect is not None:
        patch_kwargs = {"side_effect": side_effect}

    inventory_patch = mock.patch(
        "modules.audio.tts.macos_voice_inventory", return_value=inventory or []
    )

    with mock.patch("sys.platform", platform):
        with inventory_patch:
            with mock.patch("subprocess.check_output", **patch_kwargs) as patched:
                module = importlib.import_module(MODULE_PATH)
    return module, patched


def test_parse_voice_line_without_quality():
    module, _ = reload_audio_module(output="")

    line = "Bad News            en_US    # Aren't you glad you didn't listen?"
    parsed = module.parse_say_voice_line(line)
    assert parsed == {
        "name": "Bad News",
        "lang": "en_US",
        "quality": None,
        "gender": None,
    }


def test_parse_voice_line_with_quality():
    module, _ = reload_audio_module(output="")

    line = "Ava                 (Enhanced)    en_US    # Sample text"
    parsed = module.parse_say_voice_line(line)
    assert parsed == {
        "name": "Ava",
        "lang": "en_US",
        "quality": "Enhanced",
        "gender": None,
    }


def test_cached_voices_loaded_once():
    output = "\n".join(
        [
            "Alice               en_US    # Hello, my name is Alice.",
            "Ava                 (Enhanced)    en_US    # Sample text",
        ]
    )
    module, patched = reload_audio_module(output=output)

    assert patched.call_count == 1
    assert module.get_say_voices() == [
        {"name": "Alice", "lang": "en_US", "quality": None, "gender": None},
        {"name": "Ava", "lang": "en_US", "quality": "Enhanced", "gender": None},
    ]

    first = module.get_say_voices()
    first.append({"name": "Injected", "lang": "en_US", "quality": None, "gender": None})
    assert module.get_say_voices() == [
        {"name": "Alice", "lang": "en_US", "quality": None, "gender": None},
        {"name": "Ava", "lang": "en_US", "quality": "Enhanced", "gender": None},
    ]


def test_collect_say_voices_skips_when_unavailable():
    module, patched = reload_audio_module(side_effect=FileNotFoundError())

    assert patched.call_count == 1
    assert module.get_say_voices() == []


def test_collect_say_voices_skips_on_non_macos():
    module, patched = reload_audio_module(platform="linux")

    assert patched.call_count == 0
    assert module.get_say_voices() == []


def test_collect_voices_prefers_inventory():
    inventory = [
        ("Ava", "en_US", "Enhanced", "female"),
        ("Miguel", "es_ES", "Premium", "male"),
    ]
    module, patched = reload_audio_module(output="ignored", inventory=inventory)

    assert patched.call_count == 0
    assert module.get_say_voices() == [
        {"name": "Ava", "lang": "en_US", "quality": "Enhanced", "gender": "Female"},
        {"name": "Miguel", "lang": "es_ES", "quality": "Premium", "gender": "Male"},
    ]
