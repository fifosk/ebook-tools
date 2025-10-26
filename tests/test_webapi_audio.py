"""Tests for macOS ``say`` voice helpers."""

from __future__ import annotations

import importlib
import sys
from unittest import mock


MODULE_PATH = "modules.webapi.audio"


def reload_audio_module(
    *,
    output: str | None = None,
    side_effect: Exception | None = None,
    platform: str = "darwin",
):
    """Reload the audio helper module with patched dependencies."""

    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]

    patch_kwargs = {"return_value": output or ""}
    if side_effect is not None:
        patch_kwargs = {"side_effect": side_effect}

    with mock.patch("sys.platform", platform):
        with mock.patch("subprocess.check_output", **patch_kwargs) as patched:
            module = importlib.import_module(MODULE_PATH)
    return module, patched


def test_parse_voice_line_without_quality():
    module, _ = reload_audio_module(output="")

    line = "Bad News            en_US    # Aren't you glad you didn't listen?"
    parsed = module.parse_say_voice_line(line)
    assert parsed == {"name": "Bad News", "lang": "en_US", "quality": None}


def test_parse_voice_line_with_quality():
    module, _ = reload_audio_module(output="")

    line = "Ava                 (Enhanced)    en_US    # Sample text"
    parsed = module.parse_say_voice_line(line)
    assert parsed == {"name": "Ava", "lang": "en_US", "quality": "Enhanced"}


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
        {"name": "Alice", "lang": "en_US", "quality": None},
        {"name": "Ava", "lang": "en_US", "quality": "Enhanced"},
    ]

    first = module.get_say_voices()
    first.append({"name": "Injected", "lang": "en_US", "quality": None})
    assert module.get_say_voices() == [
        {"name": "Alice", "lang": "en_US", "quality": None},
        {"name": "Ava", "lang": "en_US", "quality": "Enhanced"},
    ]


def test_collect_say_voices_skips_when_unavailable():
    module, patched = reload_audio_module(side_effect=FileNotFoundError())

    assert patched.call_count == 1
    assert module.get_say_voices() == []


def test_collect_say_voices_skips_on_non_macos():
    module, patched = reload_audio_module(platform="linux")

    assert patched.call_count == 0
    assert module.get_say_voices() == []
