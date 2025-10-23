"""Minimal stub for :mod:`pydantic_settings` used in unit tests."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel


class SettingsConfigDict(dict):
    """Container mirroring Pydantic's settings config helper."""


class BaseSettings(BaseModel):
    """Thin wrapper around the stubbed :class:`pydantic.BaseModel`."""

    def model_dump(self, *_, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        return super().model_dump(**kwargs)


__all__ = ["BaseSettings", "SettingsConfigDict"]
