"""Utilities for computing job-specific storage paths and URLs."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Callable, Optional, Union
from urllib.parse import quote

from .. import config_manager as cfg

PathLikeStr = Union[str, os.PathLike[str]]

_JOB_STORAGE_ENV = "JOB_STORAGE_DIR"
_STORAGE_BASE_URL_ENV = "EBOOK_STORAGE_BASE_URL"

_ALLOWED_FRAGMENT_CHARS = {
    *"abcdefghijklmnopqrstuvwxyz",
    *"ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    *"0123456789",
    "-",
    "_",
}


def _sanitize_fragment(value: str) -> str:
    """Return a filesystem-safe fragment for ``value``."""

    if not value:
        return "job"
    sanitized = [ch if ch in _ALLOWED_FRAGMENT_CHARS else "_" for ch in value]
    result = "".join(sanitized).strip("._")
    return result or "job"


class FileLocator:
    """Resolve filesystem paths and URLs for persisted pipeline job artifacts."""

    def __init__(
        self,
        *,
        storage_dir: Optional[PathLikeStr] = None,
        base_url: Optional[str] = None,
        settings_provider: Optional[Callable[[], object]] = None,
    ) -> None:
        self._settings_provider = settings_provider or cfg.get_settings
        settings = self._settings_provider()

        storage_candidate = storage_dir or os.environ.get(_JOB_STORAGE_ENV)
        if storage_candidate is None:
            storage_candidate = getattr(settings, "job_storage_dir", None)
        if storage_candidate is None:
            storage_candidate = Path("storage") / "jobs"
        self._storage_root = self._normalize_root(storage_candidate)

        base_url_candidate = base_url or os.environ.get(_STORAGE_BASE_URL_ENV)
        if base_url_candidate is None:
            base_url_candidate = getattr(settings, "storage_base_url", "")
        self._base_url = (base_url_candidate or "").rstrip("/")

    @staticmethod
    def _normalize_root(path_value: PathLikeStr) -> Path:
        path = Path(path_value).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()

    @property
    def storage_root(self) -> Path:
        """Absolute root directory where job files are stored."""

        return self._storage_root

    @property
    def base_url(self) -> str:
        """Base URL prefix for exposing stored job artifacts."""

        return self._base_url

    def resolve_path(
        self, job_id: str, file_name: Optional[PathLikeStr] = None
    ) -> Path:
        """Return the filesystem path for ``job_id`` joined with ``file_name``.

        ``file_name`` must be a relative path. A :class:`ValueError` is raised if an
        absolute path or parent directory traversal is requested.
        """

        job_fragment = _sanitize_fragment(job_id)
        base_path = self._storage_root / job_fragment
        if not file_name:
            return base_path
        relative = Path(file_name)
        if relative.is_absolute() or any(part == ".." for part in relative.parts):
            raise ValueError("file_name must be a relative path inside the job directory")
        return base_path / relative

    def resolve_url(
        self, job_id: str, path: Optional[PathLikeStr] = None
    ) -> Optional[str]:
        """Return the URL for ``job_id`` joined with ``path`` if a base URL is set."""

        if not self._base_url:
            return None

        segments = [_sanitize_fragment(job_id)]
        if path:
            relative = PurePosixPath(str(path).replace("\\", "/"))
            for part in relative.parts:
                if part in {"", "."}:
                    continue
                if part == "..":
                    raise ValueError("path must not traverse parent directories")
                segments.append(part)
        encoded = "/".join(quote(segment) for segment in segments)
        return f"{self._base_url}/{encoded}" if encoded else self._base_url


__all__ = ["FileLocator"]
