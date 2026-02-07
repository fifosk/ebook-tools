"""Lightweight test stub for the :mod:`pydantic` package."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional


class ValidationError(Exception):
    """Exception raised when validation fails in the stub implementation."""


class AliasChoices(tuple):
    """Placeholder representing alternative field names."""

    def __new__(cls, *choices: str) -> "AliasChoices":  # type: ignore[override]
        return super().__new__(cls, choices)


class ConfigDict(dict):
    """Simple stand-in for :class:`pydantic.ConfigDict`."""


@dataclass
class FieldInfo:
    default: Any = None
    default_factory: Optional[Callable[[], Any]] = None
    validation_alias: Optional[AliasChoices] = None
    alias: Optional[str] = None

    def get_default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        return self.default


def Field(*, default: Any = None, default_factory: Optional[Callable[[], Any]] = None, validation_alias: Any = None, alias: Optional[str] = None, **_extras: Any) -> FieldInfo:  # noqa: D401, N802
    """Return a container describing field defaults."""

    resolved_alias = validation_alias if isinstance(validation_alias, AliasChoices) else None
    return FieldInfo(default=default, default_factory=default_factory, validation_alias=resolved_alias, alias=alias)


class SecretStr:
    """Minimal secret container mirroring Pydantic's interface used in tests."""

    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "SecretStr('***')"


class BaseModel:
    """Very small subset of :class:`pydantic.BaseModel` behaviour."""

    model_config: Dict[str, Any] = {}

    def __init__(self, **data: Any) -> None:
        defaults = self._collect_defaults()
        defaults.update(data)
        for key, value in defaults.items():
            setattr(self, key, value)

    @classmethod
    def _collect_defaults(cls) -> Dict[str, Any]:
        defaults: Dict[str, Any] = {}
        for name, value in cls.__dict__.items():
            if name.startswith("_") or callable(value):
                continue
            if isinstance(value, FieldInfo):
                defaults[name] = value.get_default()
            else:
                defaults[name] = value
        return defaults

    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> "BaseModel":
        return cls(**data)

    def model_dump(
        self,
        *,
        mode: str = "python",
        exclude: Optional[Iterable[str]] = None,
        **_: Any,
    ) -> Dict[str, Any]:  # noqa: ARG002 - unused in stub
        payload = dict(self.__dict__)
        if exclude:
            for key in exclude:
                payload.pop(key, None)
        return payload

    def model_copy(self, *, update: Optional[Dict[str, Any]] = None) -> "BaseModel":
        payload = self.model_dump()
        if update:
            payload.update(update)
        return self.__class__(**payload)


__all__ = [
    "AliasChoices",
    "BaseModel",
    "ConfigDict",
    "Field",
    "FieldInfo",
    "SecretStr",
    "ValidationError",
]
