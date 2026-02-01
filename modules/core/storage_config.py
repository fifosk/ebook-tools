"""Centralized configuration for ML model storage paths.

Supports external SSD storage to offload large model files from the local
system cache. Configure paths via environment variables:

    EBOOK_PIPER_MODELS_PATH - Piper TTS voice models (.onnx + .onnx.json)
    EBOOK_WHISPERX_MODELS_PATH - WhisperX alignment models
    EBOOK_HF_CACHE_PATH - HuggingFace model cache (transformers, datasets)

Example usage with external SSD at /Volumes/WD-1TB:

    export EBOOK_PIPER_MODELS_PATH=/Volumes/WD-1TB/ml-models/piper-voices
    export EBOOK_WHISPERX_MODELS_PATH=/Volumes/WD-1TB/ml-models/whisperx
    export EBOOK_HF_CACHE_PATH=/Volumes/WD-1TB/ml-models/huggingface
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# Default paths (when no external storage configured)
DEFAULT_PIPER_MODELS_PATH = Path.home() / ".local" / "share" / "piper-tts" / "piper-voices"
DEFAULT_WHISPERX_MODELS_PATH = Path.home() / ".cache" / "whisperx"
DEFAULT_HF_CACHE_PATH = Path.home() / ".cache" / "huggingface"


def get_piper_models_path() -> Path:
    """Return the path for Piper voice models.

    Checks EBOOK_PIPER_MODELS_PATH environment variable first, falling back
    to the default ~/.local/share/piper-tts/piper-voices location.
    """
    custom_path = os.environ.get("EBOOK_PIPER_MODELS_PATH")
    if custom_path:
        path = Path(custom_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return DEFAULT_PIPER_MODELS_PATH


def get_whisperx_models_path() -> Path:
    """Return the path for WhisperX alignment models.

    Checks EBOOK_WHISPERX_MODELS_PATH environment variable first, falling back
    to the default ~/.cache/whisperx location.
    """
    custom_path = os.environ.get("EBOOK_WHISPERX_MODELS_PATH")
    if custom_path:
        path = Path(custom_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return DEFAULT_WHISPERX_MODELS_PATH


def get_hf_cache_path() -> Path:
    """Return the HuggingFace cache path.

    Checks EBOOK_HF_CACHE_PATH environment variable first, falling back to
    the default ~/.cache/huggingface location.
    """
    custom_path = os.environ.get("EBOOK_HF_CACHE_PATH")
    if custom_path:
        path = Path(custom_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return DEFAULT_HF_CACHE_PATH


def configure_hf_environment() -> None:
    """Configure HuggingFace environment variables for external storage.

    Sets HF_HOME, HUGGINGFACE_HUB_CACHE, and HF_DATASETS_CACHE based on the
    configured cache path. Call this early in application startup, before
    importing any HuggingFace libraries.

    Uses setdefault to avoid overwriting existing environment variables.
    """
    hf_path = get_hf_cache_path()
    os.environ.setdefault("HF_HOME", str(hf_path))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_path / "hub"))
    os.environ.setdefault("HF_DATASETS_CACHE", str(hf_path / "datasets"))


def get_model_paths_summary() -> dict[str, str]:
    """Return a summary of all configured model paths.

    Useful for debugging and logging configuration state.
    """
    return {
        "piper_models": str(get_piper_models_path()),
        "whisperx_models": str(get_whisperx_models_path()),
        "hf_cache": str(get_hf_cache_path()),
        "hf_home": os.environ.get("HF_HOME", "(not set)"),
        "hf_hub_cache": os.environ.get("HUGGINGFACE_HUB_CACHE", "(not set)"),
    }


__all__ = [
    "DEFAULT_HF_CACHE_PATH",
    "DEFAULT_PIPER_MODELS_PATH",
    "DEFAULT_WHISPERX_MODELS_PATH",
    "configure_hf_environment",
    "get_hf_cache_path",
    "get_model_paths_summary",
    "get_piper_models_path",
    "get_whisperx_models_path",
]
