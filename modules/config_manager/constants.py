"""Shared constants for the configuration manager package."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = MODULE_DIR.parent.resolve()
DEFAULT_WORKING_RELATIVE = Path("output")
DEFAULT_OUTPUT_RELATIVE = DEFAULT_WORKING_RELATIVE / "ebook"
DEFAULT_TMP_RELATIVE = Path("tmp")
DEFAULT_BOOKS_RELATIVE = Path("storage/ebooks")
DEFAULT_COVERS_RELATIVE = Path("storage/covers")
DEFAULT_SMB_SHARE_ROOT = Path("/Volumes/Data/Download/Ebooks")
DEFAULT_SMB_OUTPUT_PATH = DEFAULT_SMB_SHARE_ROOT / "ebook"
DEFAULT_SMB_BOOKS_PATH = DEFAULT_SMB_SHARE_ROOT
_SMB_WRITE_PROBE_NAME = ".ebook_tools_smb_write_probe"
CONF_DIR = SCRIPT_DIR / "conf"
DEFAULT_CONFIG_PATH = CONF_DIR / "config.json"
DEFAULT_LOCAL_CONFIG_PATH = CONF_DIR / "config.local.json"
DEFAULT_LIBRARY_ROOT = Path("/Volumes/Data/Video/Library")

DERIVED_RUNTIME_DIRNAME = "runtime"
DERIVED_REFINED_FILENAME_TEMPLATE = "{base_name}_refined_list.json"
DERIVED_CONFIG_KEYS = {"refined_list"}
SENSITIVE_CONFIG_KEYS = {"ollama_api_key", "database_url", "job_store_url"}

DEFAULT_OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://192.168.1.9:11434/api/chat"
)
DEFAULT_OLLAMA_CLOUD_URL = os.environ.get(
    "OLLAMA_CLOUD_URL", "https://api.ollama.com/v1/chat/completions"
)
DEFAULT_LMSTUDIO_URL = os.environ.get(
    "LMSTUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions"
)
VALID_LLM_SOURCES = {"local", "cloud", "lmstudio"}
_env_llm_source = os.environ.get("LLM_SOURCE", "local").strip().lower()
DEFAULT_LLM_SOURCE = _env_llm_source if _env_llm_source in VALID_LLM_SOURCES else "local"
DEFAULT_FFMPEG_PATH = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"
DEFAULT_MODEL = "kimi-k2-thinking:cloud"
DEFAULT_THREADS = 5
DEFAULT_QUEUE_SIZE = 20
DEFAULT_JOB_MAX_WORKERS = 2
DEFAULT_TRANSLATION_FALLBACK_MODEL = "gemma3:12b"
DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS = 60.0
DEFAULT_TTS_FALLBACK_VOICE = "macOS-auto"

VAULT_FILE_ENV = "EBOOK_VAULT_FILE"

__all__ = [
    "MODULE_DIR",
    "SCRIPT_DIR",
    "DEFAULT_WORKING_RELATIVE",
    "DEFAULT_OUTPUT_RELATIVE",
    "DEFAULT_TMP_RELATIVE",
    "DEFAULT_BOOKS_RELATIVE",
    "DEFAULT_COVERS_RELATIVE",
    "DEFAULT_LIBRARY_ROOT",
    "DEFAULT_SMB_SHARE_ROOT",
    "DEFAULT_SMB_OUTPUT_PATH",
    "DEFAULT_SMB_BOOKS_PATH",
    "_SMB_WRITE_PROBE_NAME",
    "CONF_DIR",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_LOCAL_CONFIG_PATH",
    "DERIVED_RUNTIME_DIRNAME",
    "DERIVED_REFINED_FILENAME_TEMPLATE",
    "DERIVED_CONFIG_KEYS",
    "SENSITIVE_CONFIG_KEYS",
    "DEFAULT_OLLAMA_URL",
    "DEFAULT_OLLAMA_CLOUD_URL",
    "DEFAULT_LMSTUDIO_URL",
    "VALID_LLM_SOURCES",
    "DEFAULT_LLM_SOURCE",
    "DEFAULT_FFMPEG_PATH",
    "DEFAULT_MODEL",
    "DEFAULT_THREADS",
    "DEFAULT_QUEUE_SIZE",
    "DEFAULT_JOB_MAX_WORKERS",
    "DEFAULT_TRANSLATION_FALLBACK_MODEL",
    "DEFAULT_TRANSLATION_LLM_TIMEOUT_SECONDS",
    "DEFAULT_TTS_FALLBACK_VOICE",
    "VAULT_FILE_ENV",
]
