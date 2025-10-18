import os
import json
import logging
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from pydub import AudioSegment

MODULE_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = MODULE_DIR.parent.resolve()
LOG_DIR = SCRIPT_DIR / "log"
LOG_FILE = LOG_DIR / "app.log"
DEFAULT_WORKING_RELATIVE = Path("output")
DEFAULT_OUTPUT_RELATIVE = DEFAULT_WORKING_RELATIVE / "ebook"
DEFAULT_TMP_RELATIVE = Path("tmp")
DEFAULT_BOOKS_RELATIVE = Path("books")
CONF_DIR = SCRIPT_DIR / "conf"
DEFAULT_CONFIG_PATH = CONF_DIR / "config.json"
DEFAULT_LOCAL_CONFIG_PATH = CONF_DIR / "config.local.json"

WORKING_DIR: Optional[str] = None
EBOOK_DIR: Optional[str] = None
TMP_DIR: Optional[str] = None
BOOKS_DIR: Optional[str] = None

DERIVED_RUNTIME_DIRNAME = "runtime"
DERIVED_REFINED_FILENAME_TEMPLATE = "{base_name}_refined_list.json"
DERIVED_CONFIG_KEYS = {"refined_list"}

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
DEFAULT_FFMPEG_PATH = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"
DEFAULT_MODEL = "gemma2:27b"


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configure application-wide logging with a rotating file handler."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ebook_tools")
    if logger.handlers:
        return logger

    logger.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger


logger = setup_logging()


def configure_logging_level(debug_enabled: bool = False) -> int:
    """Adjust the global logger level based on debug preference."""
    level = logging.DEBUG if debug_enabled else logging.INFO
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
    return level


# Explicitly set ffmpeg converter for pydub using configurable path
AudioSegment.converter = DEFAULT_FFMPEG_PATH

# Will be updated once configuration is loaded
OLLAMA_API_URL = DEFAULT_OLLAMA_URL


def resolve_directory(path_value, default_relative: Path) -> Path:
    """Resolve a directory path relative to the script directory and ensure it exists."""
    base_value = path_value if path_value not in [None, ""] else default_relative
    base_path = Path(os.path.expanduser(str(base_value)))
    if not base_path.is_absolute():
        base_path = (SCRIPT_DIR / base_path).resolve()
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


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


def initialize_environment(config: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> None:
    """Configure directories and external tool locations based on config and overrides."""
    overrides = overrides or {}

    working_override = overrides.get("working_dir")
    output_override = overrides.get("output_dir")
    tmp_override = overrides.get("tmp_dir")
    books_override = overrides.get("ebooks_dir")
    ffmpeg_override = overrides.get("ffmpeg_path")
    ollama_override = overrides.get("ollama_url")

    working_path = resolve_directory(working_override or config.get("working_dir"), DEFAULT_WORKING_RELATIVE)

    if output_override or config.get("output_dir"):
        output_path = resolve_directory(output_override or config.get("output_dir"), DEFAULT_OUTPUT_RELATIVE)
    else:
        output_path = (working_path / "ebook")
        output_path.mkdir(parents=True, exist_ok=True)

    tmp_path = resolve_directory(tmp_override or config.get("tmp_dir"), DEFAULT_TMP_RELATIVE)
    books_path = resolve_directory(books_override or config.get("ebooks_dir"), DEFAULT_BOOKS_RELATIVE)

    global WORKING_DIR, EBOOK_DIR, TMP_DIR, BOOKS_DIR, OLLAMA_API_URL
    WORKING_DIR = str(working_path)
    EBOOK_DIR = str(output_path)
    TMP_DIR = str(tmp_path)
    BOOKS_DIR = str(books_path)

    ffmpeg_path = os.path.expanduser(str(ffmpeg_override or config.get("ffmpeg_path") or DEFAULT_FFMPEG_PATH))
    AudioSegment.converter = ffmpeg_path

    OLLAMA_API_URL = ollama_override or config.get("ollama_url") or DEFAULT_OLLAMA_URL


def _read_config_json(path, verbose: bool = False, label: str = "configuration") -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if verbose:
            logger.info("Loaded %s from %s", label, path)
        return data
    except FileNotFoundError:
        if verbose:
            logger.info("No %s found at %s.", label, path)
        return {}
    except Exception as e:  # pragma: no cover - log and continue
        if verbose:
            logger.warning("Error loading %s from %s: %s. Proceeding without it.", label, path, e)
        return {}


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_configuration(config_file: Optional[str] = None, verbose: bool = False, default_model: Optional[str] = None) -> Dict[str, Any]:
    config: Dict[str, Any] = {}

    default_config = _read_config_json(DEFAULT_CONFIG_PATH, verbose=verbose, label="default configuration")
    config = _deep_merge_dict(config, default_config)

    override_path = None
    if config_file:
        override_path = Path(config_file).expanduser()
        if not override_path.is_absolute():
            override_path = (Path.cwd() / override_path).resolve()
    else:
        override_path = DEFAULT_LOCAL_CONFIG_PATH

    override_config = _read_config_json(override_path, verbose=verbose, label="local configuration") if override_path else {}
    config = _deep_merge_dict(config, override_config)

    if verbose and override_path and not override_config:
        if override_path == DEFAULT_LOCAL_CONFIG_PATH:
            logger.info("Proceeding with defaults from %s", DEFAULT_CONFIG_PATH)
        else:
            logger.info("Proceeding with defaults because %s could not be loaded", override_path)

    if default_model is None:
        default_model = DEFAULT_MODEL

    config.setdefault("input_file", "")
    config.setdefault("ebooks_dir", str(DEFAULT_BOOKS_RELATIVE))
    config.setdefault("base_output_file", "")
    config.setdefault("input_language", "English")
    config.setdefault("target_languages", ["Arabic"])
    config.setdefault("ollama_model", default_model)
    config.setdefault("generate_audio", True)
    config.setdefault("generate_video", True)
    config.setdefault("sentences_per_output_file", 10)
    config.setdefault("start_sentence", 1)
    config.setdefault("end_sentence", None)
    config.setdefault("max_words", 18)
    config.setdefault("percentile", 96)
    config.setdefault("split_on_comma_semicolon", False)
    config.setdefault("audio_mode", "1")
    config.setdefault("written_mode", "4")
    config.setdefault("include_transliteration", False)
    config.setdefault("debug", False)
    config.setdefault("output_html", True)
    config.setdefault("output_pdf", False)
    config.setdefault("stitch_full", False)
    config.setdefault("selected_voice", "gTTS")
    config.setdefault("book_title", "Unknown Title")
    config.setdefault("book_author", "Unknown Author")
    config.setdefault("book_year", "Unknown Year")
    config.setdefault("book_summary", "No summary provided.")
    config.setdefault("book_cover_file", None)
    config.setdefault("macos_reading_speed", 100)
    config.setdefault("tempo", 1.0)
    config.setdefault("sync_ratio", 0.9)
    config.setdefault("word_highlighting", True)
    config.setdefault("working_dir", str(DEFAULT_WORKING_RELATIVE))
    config.setdefault("output_dir", str(DEFAULT_OUTPUT_RELATIVE))
    config.setdefault("tmp_dir", str(DEFAULT_TMP_RELATIVE))
    config.setdefault("ollama_url", DEFAULT_OLLAMA_URL)
    config.setdefault("ffmpeg_path", DEFAULT_FFMPEG_PATH)

    return config


def strip_derived_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the configuration without derived runtime keys."""
    return {k: v for k, v in config.items() if k not in DERIVED_CONFIG_KEYS}
