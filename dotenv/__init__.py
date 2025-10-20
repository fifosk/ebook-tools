"""Minimal stub of the :mod:`dotenv` package for test environments."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def load_dotenv(*args: Any, **kwargs: Any) -> Optional[str]:
    """Return ``None`` to simulate optional environment loading."""

    return None


def dotenv_values(
    dotenv_path: Optional[str | Path] = None,
    stream: Any = None,
    encoding: str = "utf-8",
    *args: Any,
    **kwargs: Any,
) -> Dict[str, str]:
    """Return a best-effort mapping of key/value pairs from a dotenv source."""

    data: Dict[str, str] = {}
    if stream is not None:
        for line in stream:
            _parse_line(line, data)
        return data

    if dotenv_path is None:
        return data

    path = Path(dotenv_path)
    if not path.exists():
        return data

    with path.open("r", encoding=encoding) as handle:
        for line in handle:
            _parse_line(line, data)
    return data


def _parse_line(line: str, data: Dict[str, str]) -> None:
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if "=" not in line:
        return
    key, value = line.split("=", 1)
    data[key.strip()] = value.strip().strip('"').strip("'")


__all__ = ["load_dotenv", "dotenv_values"]

