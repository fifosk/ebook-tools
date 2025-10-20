"""Template manager for slide layout and theming."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional


def _merge_mappings(base: Mapping[str, Any], overrides: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``overrides`` into ``base``."""

    result: Dict[str, Any] = dict(base)
    for key, value in overrides.items():
        if (
            isinstance(value, Mapping)
            and key in result
            and isinstance(result[key], Mapping)
        ):
            result[key] = _merge_mappings(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


def _parse_color(value: Any, *, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if value is None:
        return default
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        items = list(value)
        if len(items) >= 3:
            try:
                return tuple(int(float(x)) for x in items[:3])  # type: ignore[return-value]
            except (TypeError, ValueError):
                return default
        return default
    if isinstance(value, str):
        text = value.strip().lstrip("#")
        if len(text) == 6:
            try:
                r = int(text[0:2], 16)
                g = int(text[2:4], 16)
                b = int(text[4:6], 16)
                return (r, g, b)
            except ValueError:
                return default
        if len(text) == 3:
            try:
                r = int(text[0] * 2, 16)
                g = int(text[1] * 2, 16)
                b = int(text[2] * 2, 16)
                return (r, g, b)
            except ValueError:
                return default
    return default


@dataclass(frozen=True)
class TemplateDefinition:
    """Container representing a resolved template definition."""

    name: str
    data: Mapping[str, Any]

    def resolve(self, slide_type: Optional[str] = None) -> Dict[str, Any]:
        """Return a merged template for ``slide_type`` including defaults."""

        base = dict(self.data)
        slides = base.pop("slides", {}) if isinstance(base.get("slides"), Mapping) else {}
        resolved = dict(base)
        default_slide = slides.get("default") if isinstance(slides, Mapping) else {}
        if isinstance(default_slide, Mapping):
            resolved = _merge_mappings(resolved, default_slide)
        if slide_type and isinstance(slides, Mapping):
            slide_override = slides.get(slide_type)
            if isinstance(slide_override, Mapping):
                resolved = _merge_mappings(resolved, slide_override)
        return resolved

    def color(self, key: str, *, default: tuple[int, int, int] = (0, 0, 0)) -> tuple[int, int, int]:
        """Return an RGB tuple for ``key`` within the template."""

        colors = self.data.get("colors")
        if not isinstance(colors, Mapping):
            return default
        return _parse_color(colors.get(key), default=default)


class TemplateManager:
    """Loads and caches JSON templates describing slide appearance."""

    def __init__(self, *, theme_dir: Optional[str] = None) -> None:
        self._theme_dir = theme_dir or os.path.join(os.path.dirname(__file__), "themes")
        self._cache: Dict[str, TemplateDefinition] = {}
        self._lock = threading.Lock()

    def __getstate__(self) -> Dict[str, Any]:
        """Support pickling by omitting the non-serializable lock."""

        state = self.__dict__.copy()
        # ``threading.Lock`` objects cannot be pickled; remove and recreate later.
        state.pop("_lock", None)
        return state

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        self.__dict__.update(state)
        self._lock = threading.Lock()

    @property
    def theme_dir(self) -> str:
        return self._theme_dir

    def _resolve_path(self, template_name: str) -> Optional[str]:
        if not template_name:
            return None
        if os.path.isabs(template_name) and os.path.exists(template_name):
            return template_name
        candidate = template_name
        if not candidate.endswith(".json"):
            candidate = f"{candidate}.json"
        joined = os.path.join(self._theme_dir, candidate)
        if os.path.exists(joined):
            return joined
        return None

    def _load_raw(self, template_name: str) -> Mapping[str, Any]:
        path = self._resolve_path(template_name)
        if path is None:
            raise FileNotFoundError(f"Template '{template_name}' not found under {self._theme_dir}")
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, Mapping):
            raise ValueError(f"Template '{template_name}' must define a JSON object")
        base_template = data.get("base_template")
        if isinstance(base_template, str):
            parent = self.get_template(base_template)
            merged = _merge_mappings(parent.data, data)
            return merged
        return dict(data)

    def get_template(self, template_name: Optional[str]) -> TemplateDefinition:
        """Return the template definition for ``template_name`` or ``default``."""

        normalized = template_name or "default"
        with self._lock:
            cached = self._cache.get(normalized)
            if cached is not None:
                return cached
        raw = self._load_raw(normalized)
        template = TemplateDefinition(name=normalized, data=raw)
        with self._lock:
            self._cache[normalized] = template
        return template

    def available_templates(self) -> Dict[str, TemplateDefinition]:
        """Return all cached templates keyed by name."""

        with self._lock:
            return dict(self._cache)


__all__ = ["TemplateDefinition", "TemplateManager", "_parse_color"]
