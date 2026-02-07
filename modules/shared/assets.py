"""Load reusable asset definitions for the ebook tools interfaces.

The raw payload lives in ``assets_data.json`` so that the same source of truth
can be consumed by both Python code and the web application.  This module
provides a thin caching layer together with helper accessors.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Dict, Iterable, List, Sequence

_ASSET_RESOURCE = "assets_data.json"


@lru_cache(maxsize=1)
def get_assets_payload() -> Dict[str, Any]:
    """Return the full asset payload bundled with the package."""
    with resources.files(__package__).joinpath(_ASSET_RESOURCE).open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


def _copy_sequence(items: Sequence[Any]) -> List[Any]:
    return list(items) if not isinstance(items, list) else items.copy()


def get_top_languages() -> List[str]:
    """Return the curated list of top languages supported by the UI."""
    payload = get_assets_payload()
    return _copy_sequence(payload.get("top_languages", ()))


def _options_lookup(key: str) -> List[Dict[str, Any]]:
    payload = get_assets_payload()
    return _copy_sequence(payload.get(key, ()))


def _options_to_map(options: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    return {str(item["value"]): str(item["description"]) for item in options}


def get_audio_mode_descriptions() -> Dict[str, str]:
    """Return a mapping of audio mode IDs to their descriptions."""
    return _options_to_map(AUDIO_MODE_OPTIONS)


def get_written_mode_descriptions() -> Dict[str, str]:
    """Return a mapping of written mode IDs to their descriptions."""
    return _options_to_map(WRITTEN_MODE_OPTIONS)


AUDIO_MODE_OPTIONS: List[Dict[str, Any]] = _options_lookup("audio_modes")
WRITTEN_MODE_OPTIONS: List[Dict[str, Any]] = _options_lookup("written_modes")
VOICE_OPTIONS: List[Dict[str, Any]] = _options_lookup("voice_options")
DEFAULT_ASSET_VALUES: Dict[str, Any] = get_assets_payload().get("defaults", {})
TOP_LANGUAGES = get_top_languages()
"""A cached copy of :func:`get_top_languages` for convenience."""
