"""Helpers for loading environment variable files across the project."""

from __future__ import annotations

import os
import importlib
import importlib.util
from pathlib import Path
from typing import Iterable, Tuple

_DOTENV_SPEC = importlib.util.find_spec("dotenv")
if _DOTENV_SPEC is not None:
    load_dotenv = importlib.import_module("dotenv").load_dotenv
else:
    def load_dotenv(path: Path, override: bool = False) -> bool:
        """Minimal .env loader used when python-dotenv is unavailable."""

        if not Path(path).is_file():
            return False

        loaded = False
        with Path(path).open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                if not key:
                    continue
                if not override and key in os.environ:
                    continue
                os.environ[key] = value
                loaded = True
        return loaded

# Cache of files that have already been processed. Prevents re-loading when the
# module is imported multiple times (for example, by both the CLI and uvicorn).
_LOADED_FILES: Tuple[Path, ...] | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_candidate_files() -> Iterable[Path]:
    """Yield potential dotenv files in order of precedence."""

    root = _project_root()
    explicit_paths = os.environ.get("EBOOK_ENV_FILE")
    if explicit_paths:
        for value in explicit_paths.split(os.pathsep):
            if value.strip():
                yield Path(value).expanduser().resolve()

    target = os.environ.get("EBOOK_ENV")
    candidate_names = [".env"]
    if target:
        candidate_names.append(f".env.{target}")
    candidate_names.append(".env.local")

    for name in candidate_names:
        yield (root / name).resolve()


def load_environment(*, force: bool = False) -> Tuple[Path, ...]:
    """Load environment variables from project-level dotenv files."""

    global _LOADED_FILES
    if _LOADED_FILES is not None and not force:
        return _LOADED_FILES

    loaded: list[Path] = []
    seen: set[Path] = set()
    for path in _iter_candidate_files():
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            continue
        if load_dotenv(path, override=False):
            loaded.append(path)
    _LOADED_FILES = tuple(loaded)
    return _LOADED_FILES


__all__ = ["load_environment"]
