import os
import json
import shutil
import atexit
import errno
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, cast, overload

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydub import AudioSegment

from contextvars import ContextVar

from modules import logging_manager
from modules import ramdisk_manager

MODULE_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = MODULE_DIR.parent.resolve()
DEFAULT_WORKING_RELATIVE = Path("output")
DEFAULT_OUTPUT_RELATIVE = DEFAULT_WORKING_RELATIVE / "ebook"
DEFAULT_TMP_RELATIVE = Path("tmp")
DEFAULT_BOOKS_RELATIVE = Path("books")
DEFAULT_SMB_SHARE_ROOT = Path("/Volumes/Data/Download/Subs")
DEFAULT_SMB_OUTPUT_PATH = DEFAULT_SMB_SHARE_ROOT / "ebook"
DEFAULT_SMB_BOOKS_PATH = DEFAULT_SMB_SHARE_ROOT
_SMB_WRITE_PROBE_NAME = ".ebook_tools_smb_write_probe"
CONF_DIR = SCRIPT_DIR / "conf"
DEFAULT_CONFIG_PATH = CONF_DIR / "config.json"
DEFAULT_LOCAL_CONFIG_PATH = CONF_DIR / "config.local.json"

DERIVED_RUNTIME_DIRNAME = "runtime"
DERIVED_REFINED_FILENAME_TEMPLATE = "{base_name}_refined_list.json"
DERIVED_CONFIG_KEYS = {"refined_list"}
SENSITIVE_CONFIG_KEYS = {"ollama_api_key", "database_url", "job_store_url"}

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
DEFAULT_FFMPEG_PATH = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"
DEFAULT_MODEL = "gemma2:27b"
DEFAULT_THREADS = 5
DEFAULT_QUEUE_SIZE = 20

VAULT_FILE_ENV = "EBOOK_VAULT_FILE"


logger = logging_manager.get_logger()
console_info = logging_manager.console_info
console_warning = logging_manager.console_warning


# Explicitly set ffmpeg converter for pydub using configurable path
AudioSegment.converter = DEFAULT_FFMPEG_PATH


class EbookToolsSettings(BaseModel):
    """Typed representation of the application configuration."""

    model_config = ConfigDict(extra="allow")

    input_file: str = ""
    ebooks_dir: str = str(DEFAULT_BOOKS_RELATIVE)
    base_output_file: str = ""
    input_language: str = "English"
    target_languages: list[str] = Field(default_factory=lambda: ["Arabic"])
    ollama_model: str = DEFAULT_MODEL
    generate_audio: bool = True
    generate_video: bool = True
    sentences_per_output_file: int = 10
    start_sentence: int = 1
    end_sentence: Optional[int] = None
    max_words: int = 18
    percentile: int = 96
    split_on_comma_semicolon: bool = False
    audio_mode: str = "1"
    written_mode: str = "4"
    include_transliteration: bool = False
    debug: bool = False
    output_html: bool = True
    output_pdf: bool = False
    stitch_full: bool = False
    selected_voice: str = "gTTS"
    book_title: str = "Unknown Title"
    book_author: str = "Unknown Author"
    book_year: str = "Unknown Year"
    book_summary: str = "No summary provided."
    book_cover_file: Optional[str] = None
    auto_metadata: bool = True
    macos_reading_speed: int = 100
    tempo: float = 1.0
    sync_ratio: float = 0.9
    word_highlighting: bool = True
    highlight_granularity: str = "word"
    slide_parallelism: str = "off"
    slide_parallel_workers: Optional[int] = None
    prefer_pillow_simd: bool = False
    slide_render_benchmark: bool = False
    working_dir: str = str(DEFAULT_WORKING_RELATIVE)
    output_dir: str = str(DEFAULT_OUTPUT_RELATIVE)
    tmp_dir: str = str(DEFAULT_TMP_RELATIVE)
    ollama_url: str = DEFAULT_OLLAMA_URL
    ffmpeg_path: Optional[str] = DEFAULT_FFMPEG_PATH
    thread_count: int = DEFAULT_THREADS
    queue_size: int = DEFAULT_QUEUE_SIZE
    pipeline_mode: bool = False
    use_ramdisk: bool = True
    ollama_api_key: Optional[SecretStr] = None
    database_url: Optional[SecretStr] = None
    job_store_url: Optional[SecretStr] = None
    job_max_workers: int = 2


class EnvironmentOverrides(BaseSettings):
    """Configuration overrides sourced from environment variables."""

    model_config = SettingsConfigDict(env_prefix="", env_nested_delimiter="__", extra="ignore")

    working_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_WORKING_DIR")
    )
    output_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_OUTPUT_DIR")
    )
    tmp_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_TMP_DIR")
    )
    ebooks_dir: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOKS_DIR", "EBOOK_EBOOKS_DIR")
    )
    ffmpeg_path: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("FFMPEG_PATH", "EBOOK_FFMPEG_PATH")
    )
    ollama_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("OLLAMA_URL", "EBOOK_OLLAMA_URL")
    )
    ollama_model: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_OLLAMA_MODEL")
    )
    thread_count: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_THREAD_COUNT")
    )
    queue_size: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_QUEUE_SIZE")
    )
    pipeline_mode: Optional[bool] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_PIPELINE_MODE")
    )
    use_ramdisk: Optional[bool] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_USE_RAMDISK")
    )
    ollama_api_key: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("OLLAMA_API_KEY", "EBOOK_OLLAMA_API_KEY")
    )
    database_url: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("DATABASE_URL", "EBOOK_DATABASE_URL")
    )
    job_store_url: Optional[SecretStr] = Field(
        default=None, validation_alias=AliasChoices("JOB_STORE_URL", "EBOOK_JOB_STORE_URL")
    )
    job_max_workers: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("EBOOK_JOB_MAX_WORKERS")
    )


_ACTIVE_SETTINGS: Optional[EbookToolsSettings] = None


def _load_environment_overrides() -> Dict[str, Any]:
    """Return configuration overrides sourced from environment variables."""

    try:
        overrides = EnvironmentOverrides()
    except ValidationError as exc:
        logger.warning(
            "Invalid environment configuration detected; using defaults.",
            extra={
                "event": "config.env.validation_error",
                "error": str(exc),
                "console_suppress": True,
            },
        )
        return {}
    return overrides.model_dump(exclude_none=True)


def _load_vault_secrets(path: Path) -> Dict[str, SecretStr]:
    """Attempt to read secret values from a vault-style JSON document."""

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        logger.debug(
            "Vault secret file not found at %s; skipping.",
            path,
            extra={"event": "config.vault.missing", "console_suppress": True},
        )
        return {}
    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to parse vault secret file at %s: %s",
            path,
            exc,
            extra={"event": "config.vault.invalid", "console_suppress": True},
        )
        return {}

    secrets: Dict[str, SecretStr] = {}
    for key in ("ollama_api_key", "database_url", "job_store_url"):
        value = payload.get(key)
        if value:
            secrets[key] = SecretStr(str(value))
    return secrets


def _apply_updates(
    settings: EbookToolsSettings, updates: Dict[str, Any]
) -> EbookToolsSettings:
    if not updates:
        return settings
    return settings.model_copy(update=updates)


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable container describing resolved runtime environment settings."""

    working_dir: Path
    output_dir: Path
    tmp_dir: Path
    books_dir: Path
    ffmpeg_path: str
    ollama_url: str
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
            "thread_count": self.thread_count,
            "queue_size": self.queue_size,
            "pipeline_enabled": self.pipeline_enabled,
            "is_tmp_ramdisk": self.is_tmp_ramdisk,
        }


_REGISTERED_CONTEXT_IDS: set[int] = set()
_ACTIVE_CONTEXT: ContextVar[Optional["RuntimeContext"]] = ContextVar(
    "ebook_tools_runtime_context", default=None
)

_DEFAULT_CONTEXT_SENTINEL = object()


def set_runtime_context(context: RuntimeContext) -> None:
    """Make ``context`` the active runtime context for the current execution scope."""

    _ACTIVE_CONTEXT.set(context)


@overload
def get_runtime_context() -> RuntimeContext:
    ...


@overload
def get_runtime_context(default: Optional[RuntimeContext]) -> Optional[RuntimeContext]:
    ...


def get_runtime_context(default=_DEFAULT_CONTEXT_SENTINEL):
    """Return the active :class:`RuntimeContext` for the caller.

    When ``default`` is provided (even if ``None``), that value will be returned if
    no runtime context has been activated for the current execution scope.
    """

    context = _ACTIVE_CONTEXT.get()
    if context is None:
        if default is _DEFAULT_CONTEXT_SENTINEL:
            raise RuntimeError(
                "Runtime context has not been initialized. Call set_runtime_context() first."
            )
        return cast(Optional[RuntimeContext], default)
    return context


def clear_runtime_context() -> None:
    """Clear the active runtime context for the current execution scope."""

    _ACTIVE_CONTEXT.set(None)
def _cleanup_directory_path(path: Path) -> None:
    """Remove broken symlinks or non-directories along ``path`` and its parents."""

    for candidate in (path, *path.parents):
        if candidate == candidate.parent:
            break

        try:
            if candidate.is_symlink():
                if candidate.exists():
                    continue
                candidate.unlink()
                continue

            if candidate.exists() and not candidate.is_dir():
                if candidate.is_file() or candidate.is_symlink():
                    candidate.unlink()
                else:
                    shutil.rmtree(candidate)
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.debug("Unable to prepare path %s: %s", candidate, exc)


def resolve_directory(path_value, default_relative: Path) -> Path:
    """Resolve a directory path relative to the script directory and ensure it exists."""

    def _normalize(candidate: Path) -> Path:
        expanded = Path(os.path.expanduser(str(candidate)))
        if expanded.is_absolute():
            return expanded
        return SCRIPT_DIR / expanded

    base_value = path_value if path_value not in [None, ""] else default_relative
    base_path = _normalize(Path(base_value))
    fallback_path = _normalize(default_relative)

    attempts = []
    seen = set()

    for candidate in (base_path, fallback_path):
        if candidate not in seen:
            attempts.append(candidate)
            seen.add(candidate)

    last_error: Optional[Exception] = None

    for index, attempt in enumerate(attempts):
        _cleanup_directory_path(attempt)

        try:
            attempt.mkdir(parents=True, exist_ok=True)
            return attempt
        except PermissionError as exc:
            last_error = exc
        except OSError as exc:
            last_error = exc
            if attempt.exists() and attempt.is_dir():
                return attempt
            if getattr(exc, "errno", None) not in {errno.EPERM, errno.EACCES, errno.EROFS}:
                raise

        if index < len(attempts) - 1:
            logger.warning(
                "Unable to prepare directory %s (%s); falling back to %s",
                attempt,
                last_error,
                attempts[index + 1],
            )

    if last_error:
        raise last_error

    return attempts[-1]


def resolve_file_path(path_value, base_dir=None) -> Optional[Path]:
    """Resolve a potentially relative file path relative to a base directory."""
    if not path_value:
        return None
    file_path = Path(os.path.expanduser(str(path_value)))
    if file_path.is_absolute():
        return file_path
    if base_dir:
        base = Path(base_dir)
        if file_path.parts and base.name == file_path.parts[0]:
            file_path = (SCRIPT_DIR / file_path).resolve()
        else:
            file_path = (base / file_path).resolve()
    else:
        file_path = (SCRIPT_DIR / file_path).resolve()
    return file_path


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

    working_path = resolve_directory(working_override or config.get("working_dir"), DEFAULT_WORKING_RELATIVE)

    def _should_use_default(value: Optional[str], default_relative: Path) -> bool:
        return value in [None, "", str(default_relative)]

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

    smb_output_path = None
    if not output_override and _should_use_default(config.get("output_dir"), DEFAULT_OUTPUT_RELATIVE):
        smb_output_path = _try_smb_directory(DEFAULT_SMB_OUTPUT_PATH, require_write=True)

    if output_override not in [None, ""]:
        output_path = resolve_directory(output_override, DEFAULT_OUTPUT_RELATIVE)
    elif not _should_use_default(config.get("output_dir"), DEFAULT_OUTPUT_RELATIVE):
        output_path = resolve_directory(config.get("output_dir"), DEFAULT_OUTPUT_RELATIVE)
    elif smb_output_path is not None:
        output_path = smb_output_path
    else:
        output_path = (working_path / "ebook")
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
    if not books_override and _should_use_default(config.get("ebooks_dir"), DEFAULT_BOOKS_RELATIVE):
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

    ollama_url = (
        ollama_override or config.get("ollama_url") or DEFAULT_OLLAMA_URL
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


def _read_config_json(path, verbose: bool = False, label: str = "configuration") -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if verbose:
            console_info("Loaded %s from %s", label, path, logger_obj=logger)
        return data
    except FileNotFoundError:
        if verbose:
            console_info("No %s found at %s.", label, path, logger_obj=logger)
        return {}
    except Exception as e:  # pragma: no cover - log and continue
        if verbose:
            console_warning(
                "Error loading %s from %s: %s. Proceeding without it.",
                label,
                path,
                e,
                logger_obj=logger,
            )
        return {}


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_configuration(
    config_file: Optional[str] = None,
    verbose: bool = False,
    default_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Load the layered configuration and return a dictionary view."""

    global _ACTIVE_SETTINGS

    base_payload: Dict[str, Any] = {}
    default_config = _read_config_json(
        DEFAULT_CONFIG_PATH, verbose=verbose, label="default configuration"
    )
    base_payload = _deep_merge_dict(base_payload, default_config)

    override_path = None
    if config_file:
        override_path = Path(config_file).expanduser()
        if not override_path.is_absolute():
            override_path = (Path.cwd() / override_path).resolve()
    else:
        override_path = DEFAULT_LOCAL_CONFIG_PATH

    override_config = (
        _read_config_json(override_path, verbose=verbose, label="local configuration")
        if override_path
        else {}
    )
    base_payload = _deep_merge_dict(base_payload, override_config)

    if verbose and override_path and not override_config:
        if override_path == DEFAULT_LOCAL_CONFIG_PATH:
            console_info(
                "Proceeding with defaults from %s",
                DEFAULT_CONFIG_PATH,
                logger_obj=logger,
            )
        else:
            console_info(
                "Proceeding with defaults because %s could not be loaded",
                override_path,
                logger_obj=logger,
            )

    try:
        settings = EbookToolsSettings.model_validate(base_payload)
    except ValidationError as exc:
        raise RuntimeError("Invalid configuration detected") from exc

    vault_path = os.environ.get(VAULT_FILE_ENV)
    vault_updates: Dict[str, Any] = {}
    if vault_path:
        vault_updates = _load_vault_secrets(Path(vault_path).expanduser())
        if vault_updates:
            logger.info(
                "Loaded secret overrides from vault file at %s",
                vault_path,
                extra={"event": "config.vault.loaded", "console_suppress": True},
            )
    env_overrides = _load_environment_overrides()

    settings = _apply_updates(settings, dict(vault_updates))
    settings = _apply_updates(settings, env_overrides)

    if default_model is None:
        default_model = DEFAULT_MODEL
    if not settings.ollama_model:
        settings = _apply_updates(settings, {"ollama_model": default_model})

    _ACTIVE_SETTINGS = settings

    exported = settings.model_dump(
        mode="python",
        exclude={"ollama_api_key", "database_url", "job_store_url"},
    )
    return exported


def strip_derived_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the configuration without derived runtime keys."""
    excluded = DERIVED_CONFIG_KEYS | SENSITIVE_CONFIG_KEYS
    return {k: v for k, v in config.items() if k not in excluded}


def get_settings() -> EbookToolsSettings:
    """Return the currently loaded :class:`EbookToolsSettings` instance."""

    global _ACTIVE_SETTINGS
    if _ACTIVE_SETTINGS is None:
        settings = EbookToolsSettings()
        vault_path = os.environ.get(VAULT_FILE_ENV)
        vault_updates: Dict[str, Any] = {}
        if vault_path:
            vault_updates = _load_vault_secrets(Path(vault_path).expanduser())
        env_overrides = _load_environment_overrides()
        settings = _apply_updates(settings, dict(vault_updates))
        settings = _apply_updates(settings, env_overrides)
        _ACTIVE_SETTINGS = settings
    return _ACTIVE_SETTINGS


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


def get_ollama_url() -> str:
    """Return the Ollama endpoint URL for the active runtime context."""

    context = _ACTIVE_CONTEXT.get()
    return context.ollama_url if context else DEFAULT_OLLAMA_URL
