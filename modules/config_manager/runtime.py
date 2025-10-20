"""Runtime context management for ebook-tools."""
from __future__ import annotations

import atexit
import os
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, cast, overload

from modules import logging_manager, ramdisk_manager

from .constants import (
    DEFAULT_BOOKS_RELATIVE,
    DEFAULT_FFMPEG_PATH,
    DEFAULT_OLLAMA_CLOUD_URL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_OUTPUT_RELATIVE,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_SMB_BOOKS_PATH,
    DEFAULT_SMB_OUTPUT_PATH,
    DEFAULT_THREADS,
    DEFAULT_TMP_RELATIVE,
    DEFAULT_WORKING_RELATIVE,
    _SMB_WRITE_PROBE_NAME,
)
from .paths import resolve_directory
from .settings import normalize_llm_source

logger = logging_manager.get_logger()


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable container describing resolved runtime environment settings."""

    working_dir: Path
    output_dir: Path
    tmp_dir: Path
    books_dir: Path
    ffmpeg_path: str
    ollama_url: str
    llm_source: str
    local_ollama_url: str
    cloud_ollama_url: str
    thread_count: int
    queue_size: int
    pipeline_enabled: bool
    is_tmp_ramdisk: bool = False

    def as_dict(self) -> Dict[str, Any]:
        """Return a mapping representation of the context for serialization/debugging."""

        return {
            "working_dir": str(self.working_dir),
            "output_dir": str(self.output_dir),
            "tmp_dir": str(self.tmp_dir),
            "books_dir": str(self.books_dir),
            "ffmpeg_path": self.ffmpeg_path,
            "ollama_url": self.ollama_url,
            "llm_source": self.llm_source,
            "local_ollama_url": self.local_ollama_url,
            "cloud_ollama_url": self.cloud_ollama_url,
            "thread_count": self.thread_count,
            "queue_size": self.queue_size,
            "pipeline_enabled": self.pipeline_enabled,
            "is_tmp_ramdisk": self.is_tmp_ramdisk,
        }


_REGISTERED_CONTEXT_IDS: set[int] = set()
_ACTIVE_CONTEXT: ContextVar[Optional[RuntimeContext]] = ContextVar(
    "ebook_tools_runtime_context", default=None
)

_DEFAULT_CONTEXT_SENTINEL = object()


@overload
def get_runtime_context() -> RuntimeContext:
    ...


@overload
def get_runtime_context(default: Optional[RuntimeContext]) -> Optional[RuntimeContext]:
    ...


def get_runtime_context(default=_DEFAULT_CONTEXT_SENTINEL):
    """Return the active :class:`RuntimeContext` for the caller."""

    context = _ACTIVE_CONTEXT.get()
    if context is None:
        if default is _DEFAULT_CONTEXT_SENTINEL:
            raise RuntimeError(
                "Runtime context has not been initialized. Call set_runtime_context() first."
            )
        return cast(Optional[RuntimeContext], default)
    return context


def set_runtime_context(context: RuntimeContext) -> None:
    """Make ``context`` the active runtime context for the current execution scope."""

    _ACTIVE_CONTEXT.set(context)


def clear_runtime_context() -> None:
    """Clear the active runtime context for the current execution scope."""

    _ACTIVE_CONTEXT.set(None)


def _coerce_thread_count(value: Optional[Any]) -> int:
    """Return a safe worker count based on ``value``."""

    if value is None:
        return DEFAULT_THREADS
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_THREADS
    return max(1, parsed)


def _coerce_queue_size(value: Optional[Any]) -> int:
    if value is None:
        return DEFAULT_QUEUE_SIZE
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_QUEUE_SIZE
    return max(1, parsed)


def _coerce_bool(value: Optional[Any]) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def cleanup_environment(context: RuntimeContext) -> None:
    """Tear down any temporary RAM disk resources for ``context``."""

    if not context.is_tmp_ramdisk:
        return

    try:
        ramdisk_manager.teardown_ramdisk(str(context.tmp_dir))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Failed to clean up temporary workspace %s: %s", context.tmp_dir, exc)


def _cleanup_tmp_ramdisk(context: RuntimeContext) -> None:
    try:
        cleanup_environment(context)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug(
            "Failed to clean up RAM disk during interpreter shutdown: %s", exc
        )


def _resolve_url(candidate: Any, fallback: str) -> str:
    if isinstance(candidate, str):
        stripped = candidate.strip()
        if stripped:
            return stripped
    return fallback


def _try_smb_directory(candidate: Path, *, require_write: bool) -> Optional[Path]:
    candidate_path = Path(os.path.expanduser(str(candidate)))
    if not candidate_path.exists():
        parent = candidate_path.parent
        if not parent.exists() or not parent.is_dir():
            return None
        try:
            candidate_path.mkdir(parents=False, exist_ok=True)
        except OSError:
            return None
    if not candidate_path.is_dir():
        return None
    if not os.access(candidate_path, os.R_OK):
        return None
    if require_write:
        if not os.access(candidate_path, os.W_OK):
            return None
        probe_path = candidate_path / _SMB_WRITE_PROBE_NAME
        try:
            with open(probe_path, "w", encoding="utf-8") as probe:
                probe.write("probe")
        except OSError:
            return None
        finally:
            try:
                probe_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                logger.debug("Failed to remove SMB probe file at %s", probe_path)
    return candidate_path


def build_runtime_context(
    config: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None
) -> RuntimeContext:
    """Configure directories and external tool locations based on config and overrides."""

    overrides = overrides or {}

    working_override = overrides.get("working_dir")
    output_override = overrides.get("output_dir")
    tmp_override = overrides.get("tmp_dir")
    books_override = overrides.get("ebooks_dir")
    ffmpeg_override = overrides.get("ffmpeg_path")
    ollama_override = overrides.get("ollama_url")

    raw_llm_source = overrides.get("llm_source") if overrides else None
    if raw_llm_source is None:
        raw_llm_source = config.get("llm_source")
    llm_source = normalize_llm_source(raw_llm_source)

    local_override = overrides.get("ollama_local_url") if overrides else None
    cloud_override = overrides.get("ollama_cloud_url") if overrides else None
    config_local_url = config.get("ollama_local_url")
    config_cloud_url = config.get("ollama_cloud_url")

    local_ollama_url = _resolve_url(
        local_override or config_local_url,
        DEFAULT_OLLAMA_URL,
    )
    cloud_ollama_url = _resolve_url(
        cloud_override or config_cloud_url,
        DEFAULT_OLLAMA_CLOUD_URL,
    )

    working_path = resolve_directory(
        working_override or config.get("working_dir"), DEFAULT_WORKING_RELATIVE
    )

    def _should_use_default(value: Optional[str], default_relative: Path) -> bool:
        return value in [None, "", str(default_relative)]

    smb_output_path = None
    if not output_override and _should_use_default(
        config.get("output_dir"), DEFAULT_OUTPUT_RELATIVE
    ):
        smb_output_path = _try_smb_directory(DEFAULT_SMB_OUTPUT_PATH, require_write=True)

    if output_override not in [None, ""]:
        output_path = resolve_directory(output_override, DEFAULT_OUTPUT_RELATIVE)
    elif not _should_use_default(config.get("output_dir"), DEFAULT_OUTPUT_RELATIVE):
        output_path = resolve_directory(config.get("output_dir"), DEFAULT_OUTPUT_RELATIVE)
    elif smb_output_path is not None:
        output_path = smb_output_path
    else:
        output_path = working_path / "ebook"
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "SMB ebook share unavailable or unwritable; using local output directory at %s.",
            output_path,
        )

    tmp_path = resolve_directory(tmp_override or config.get("tmp_dir"), DEFAULT_TMP_RELATIVE)

    use_ramdisk_override = overrides.get("use_ramdisk") if overrides else None
    use_ramdisk_value = (
        use_ramdisk_override
        if use_ramdisk_override is not None
        else config.get("use_ramdisk", True)
    )
    use_ramdisk = _coerce_bool(use_ramdisk_value)

    if use_ramdisk:
        ramdisk_ready = ramdisk_manager.ensure_ramdisk(tmp_path)
        if not ramdisk_ready:
            logger.info(
                "RAM disk unavailable; continuing with on-disk temporary directory at %s.",
                tmp_path,
            )
            tmp_path = ramdisk_manager.ensure_standard_directory(tmp_path)
    else:
        tmp_path = ramdisk_manager.ensure_standard_directory(tmp_path)

    tmp_path = Path(tmp_path)

    smb_books_path = None
    if not books_override and _should_use_default(
        config.get("ebooks_dir"), DEFAULT_BOOKS_RELATIVE
    ):
        smb_books_path = _try_smb_directory(DEFAULT_SMB_BOOKS_PATH, require_write=False)

    if books_override not in [None, ""]:
        books_path = resolve_directory(books_override, DEFAULT_BOOKS_RELATIVE)
    elif not _should_use_default(config.get("ebooks_dir"), DEFAULT_BOOKS_RELATIVE):
        books_path = resolve_directory(config.get("ebooks_dir"), DEFAULT_BOOKS_RELATIVE)
    elif smb_books_path is not None:
        books_path = smb_books_path
    else:
        books_path = resolve_directory(None, DEFAULT_BOOKS_RELATIVE)
        logger.info(
            "SMB ebook share unavailable; using local books directory at %s.",
            books_path,
        )

    is_tmp_ramdisk = ramdisk_manager.is_ramdisk(tmp_path)

    ffmpeg_path = os.path.expanduser(
        str(ffmpeg_override or config.get("ffmpeg_path") or DEFAULT_FFMPEG_PATH)
    )

    config_primary_url = config.get("ollama_url")
    default_primary_url = cloud_ollama_url if llm_source == "cloud" else local_ollama_url
    ollama_url = _resolve_url(
        ollama_override or config_primary_url,
        default_primary_url,
    )

    thread_override = overrides.get("thread_count") if overrides else None
    thread_count = _coerce_thread_count(thread_override or config.get("thread_count"))

    queue_override = overrides.get("queue_size") if overrides else None
    queue_size = _coerce_queue_size(queue_override or config.get("queue_size"))

    pipeline_override = overrides.get("pipeline_mode") if overrides else None
    pipeline_enabled = _coerce_bool(
        pipeline_override if pipeline_override is not None else config.get("pipeline_mode")
    )

    context = RuntimeContext(
        working_dir=working_path,
        output_dir=Path(output_path),
        tmp_dir=tmp_path,
        books_dir=Path(books_path),
        ffmpeg_path=ffmpeg_path,
        ollama_url=ollama_url,
        llm_source=llm_source,
        local_ollama_url=local_ollama_url,
        cloud_ollama_url=cloud_ollama_url,
        thread_count=thread_count,
        queue_size=queue_size,
        pipeline_enabled=pipeline_enabled,
        is_tmp_ramdisk=is_tmp_ramdisk,
    )

    context_id = id(context)
    if context.is_tmp_ramdisk and context_id not in _REGISTERED_CONTEXT_IDS:
        atexit.register(_cleanup_tmp_ramdisk, context)
        _REGISTERED_CONTEXT_IDS.add(context_id)

    return context


def get_thread_count() -> int:
    """Return the currently configured worker thread count."""

    context = _ACTIVE_CONTEXT.get()
    return context.thread_count if context else DEFAULT_THREADS


def get_queue_size() -> int:
    """Return the configured bounded queue size for the pipeline."""

    context = _ACTIVE_CONTEXT.get()
    return context.queue_size if context else DEFAULT_QUEUE_SIZE


def is_pipeline_mode() -> bool:
    """Return whether the concurrent translation/media pipeline is enabled."""

    context = _ACTIVE_CONTEXT.get()
    return context.pipeline_enabled if context else False


__all__ = [
    "RuntimeContext",
    "build_runtime_context",
    "cleanup_environment",
    "clear_runtime_context",
    "get_queue_size",
    "get_runtime_context",
    "get_thread_count",
    "is_pipeline_mode",
    "set_runtime_context",
]
