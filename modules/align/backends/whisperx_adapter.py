"""WhisperX forced alignment adapter using the Python API."""

from __future__ import annotations

import functools
import threading
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules import logging_manager as log_mgr

# Suppress known deprecation warnings from transformers library
warnings.filterwarnings(
    "ignore",
    message=".*gradient_checkpointing.*",
    category=UserWarning,
    module="transformers",
)

# Suppress PyTorch meta tensor warnings during model loading
# These occur when loading Wav2Vec2 models and are harmless
warnings.filterwarnings(
    "ignore",
    message=".*copying from a non-meta parameter.*",
    category=UserWarning,
    module="torch",
)

logger = log_mgr.logger

# Lazy-loaded whisperx modules and cached models
_whisperx: Optional[Any] = None
_whisperx_lock = threading.Lock()

# Model cache to avoid reloading for each sentence
_model_cache: Dict[str, Tuple[Any, dict]] = {}
_model_cache_lock = threading.Lock()

# Default device - will be set on first use
_default_device: Optional[str] = None


def _get_whisperx():
    """Lazy-load whisperx to avoid import errors when not installed."""
    global _whisperx
    if _whisperx is not None:
        return _whisperx

    with _whisperx_lock:
        if _whisperx is not None:
            return _whisperx
        try:
            import whisperx
            _whisperx = whisperx
            logger.debug("WhisperX library loaded successfully")
            return whisperx
        except ImportError as exc:
            logger.warning("WhisperX not installed: %s", exc)
            raise
        except Exception as exc:
            logger.warning("Failed to import WhisperX: %s", exc, exc_info=True)
            raise


def _get_default_device() -> str:
    """Determine the best available device (cuda/mps/cpu)."""
    global _default_device
    if _default_device is not None:
        return _default_device

    try:
        import torch
        if torch.cuda.is_available():
            _default_device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            _default_device = "mps"
        else:
            _default_device = "cpu"
    except ImportError:
        _default_device = "cpu"

    logger.debug("WhisperX using device: %s", _default_device)
    return _default_device


def _is_valid_alignment_model(model_name: Optional[str]) -> bool:
    """Check if model_name is a valid Wav2Vec2 alignment model (not a Whisper model)."""
    if not model_name:
        return False

    model_lower = model_name.lower()

    # Valid alignment models contain wav2vec, hubert, voxpopuli, or are HuggingFace paths
    valid_patterns = ("wav2vec", "hubert", "voxpopuli", "_asr_")
    if any(p in model_lower for p in valid_patterns) or "/" in model_name:
        return True

    # Reject Whisper model patterns (these are NOT alignment models)
    whisper_patterns = (
        "tiny", "base", "small", "medium", "large",  # Whisper size names
        "large-v1", "large-v2", "large-v3",          # Whisper versions
        ".en",                                        # English-only Whisper models
    )
    for pattern in whisper_patterns:
        if pattern in model_lower:
            return False

    # Unknown model - let WhisperX decide
    return True


def _get_alignment_model(
    language: str,
    device: str,
    model_name: Optional[str] = None,
) -> Tuple[Any, dict]:
    """Get or create a cached alignment model for the given language."""

    # Filter out invalid Whisper model names - let WhisperX choose the default
    if model_name and not _is_valid_alignment_model(model_name):
        logger.debug(
            "Ignoring invalid alignment model '%s' (looks like a Whisper model); "
            "using WhisperX default for language '%s'",
            model_name,
            language,
        )
        model_name = None

    cache_key = f"{language}:{device}:{model_name or 'default'}"

    with _model_cache_lock:
        if cache_key in _model_cache:
            logger.debug("Using cached alignment model for %s", cache_key)
            return _model_cache[cache_key]

    whisperx = _get_whisperx()

    logger.info(
        "Loading WhisperX alignment model for language='%s', device='%s', model='%s'",
        language,
        device,
        model_name or "default",
    )

    try:
        model, metadata = whisperx.load_align_model(
            language_code=language,
            device=device,
            model_name=model_name,
        )
    except ValueError as exc:
        # No model available for this language
        logger.warning("No alignment model available for language '%s': %s", language, exc)
        raise
    except Exception as exc:
        # Check for "meta tensor" error - MPS/CUDA device issue with certain models
        # This can be NotImplementedError or wrapped in other exception types
        exc_str = str(exc)
        if "meta tensor" in exc_str and device != "cpu":
            logger.warning(
                "MPS/CUDA device failed for language '%s' (meta tensor error), falling back to CPU",
                language,
            )
            return _get_alignment_model(language, "cpu", model_name)
        logger.warning("Failed to load alignment model: %s", exc, exc_info=True)
        raise

    with _model_cache_lock:
        _model_cache[cache_key] = (model, metadata)

    # Log the actual model that was loaded (helpful for troubleshooting)
    resolved_model_name = metadata.get("language", model_name) if isinstance(metadata, dict) else model_name
    logger.info(
        "WhisperX alignment model loaded: language='%s', device='%s', resolved_model='%s'",
        language,
        device,
        resolved_model_name or "default",
    )
    return model, metadata


def _detect_language(text: str) -> str:
    """
    Simple language detection heuristic.

    Returns a 2-letter language code. Defaults to 'en' if detection fails.
    """
    # Check for common non-Latin scripts
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    japanese_chars = sum(1 for c in text if '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
    hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
    cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')

    total = len(text) or 1

    if arabic_chars / total > 0.3:
        return "ar"
    if chinese_chars / total > 0.3:
        return "zh"
    if japanese_chars / total > 0.3:
        return "ja"
    if hebrew_chars / total > 0.3:
        return "he"
    if cyrillic_chars / total > 0.3:
        return "ru"

    # Default to English for Latin scripts
    return "en"


def align_sentence(
    audio_path: str | Path,
    text: str,
    *,
    model: Optional[str] = None,
    device: Optional[str] = None,
    language: Optional[str] = None,
) -> List[Dict[str, float | str]]:
    """
    Align ``text`` against ``audio_path`` using WhisperX Python API.

    Args:
        audio_path: Path to audio file (WAV recommended)
        text: Text to align against the audio
        model: Optional alignment model name (e.g., 'WAV2VEC2_ASR_BASE_960H')
        device: Device to use ('cuda', 'mps', 'cpu'). Auto-detected if None.
        language: Language code (e.g., 'en', 'ar'). Auto-detected if None.

    Returns:
        List of word timing dictionaries with 'text', 'start', 'end' keys.
        Returns empty list on any failure.
    """
    audio = Path(audio_path)
    if not audio.exists():
        logger.warning("WhisperX alignment skipped: audio path '%s' not found.", audio)
        return []

    text = text.strip()
    if not text:
        logger.debug("WhisperX alignment skipped: empty text")
        return []

    # Resolve device
    resolved_device = device or _get_default_device()

    # Resolve language
    resolved_language = language or _detect_language(text)

    try:
        whisperx = _get_whisperx()
    except Exception:
        return []

    # Load audio
    try:
        audio_array = whisperx.load_audio(str(audio))
    except Exception as exc:
        logger.warning("WhisperX failed to load audio '%s': %s", audio, exc)
        return []

    # Load alignment model
    try:
        align_model, align_metadata = _get_alignment_model(
            resolved_language,
            resolved_device,
            model,
        )
    except Exception:
        return []

    # Create transcript segments in the format whisperx.align expects
    # We treat the entire text as a single segment spanning the audio duration
    try:
        # Get audio duration
        sample_rate = 16000  # WhisperX default
        duration = len(audio_array) / sample_rate
    except Exception:
        duration = 9999.0  # Fallback to large value

    transcript_segments = [
        {
            "start": 0.0,
            "end": duration,
            "text": text,
        }
    ]

    # Perform alignment
    try:
        result = whisperx.align(
            transcript_segments,
            align_model,
            align_metadata,
            audio_array,
            resolved_device,
            return_char_alignments=False,
        )
    except Exception as exc:
        logger.warning("WhisperX alignment failed: %s", exc, exc_info=True)
        return []

    # Extract word-level tokens from result
    tokens: List[Dict[str, float | str]] = []

    # Result structure: {"segments": [...], "word_segments": [...]}
    segments = result.get("segments", [])
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        words = segment.get("words", [])
        for word in words:
            if not isinstance(word, dict):
                continue

            token_text = word.get("word", "")
            if not isinstance(token_text, str):
                token_text = str(token_text)
            token_text = token_text.strip()

            if not token_text:
                continue

            try:
                start = float(word.get("start", 0))
                end = float(word.get("end", start))
            except (TypeError, ValueError):
                continue

            # Clamp and round values
            start = round(max(start, 0.0), 6)
            end = round(max(end, start), 6)

            tokens.append({
                "text": token_text,
                "start": start,
                "end": end,
            })

    if tokens:
        logger.debug(
            "WhisperX aligned %d words from '%s' (lang=%s, device=%s)",
            len(tokens),
            audio.name,
            resolved_language,
            resolved_device,
        )
    else:
        logger.warning(
            "WhisperX produced no tokens for '%s' (lang=%s)",
            audio.name,
            resolved_language,
        )

    return tokens


def retry_alignment(
    audio_path: str | Path,
    text: str,
    *,
    model: Optional[str] = None,
    device: Optional[str] = None,
    language: Optional[str] = None,
    max_attempts: int = 3,
) -> Tuple[List[Dict[str, float | str]], bool]:
    """
    Attempt WhisperX alignment up to ``max_attempts`` times.

    Returns a tuple of (tokens, exhausted_retry_flag).
    The exhausted flag is True if all attempts failed.
    """
    attempts = max(1, int(max_attempts))
    for attempt in range(1, attempts + 1):
        tokens = align_sentence(
            audio_path,
            text,
            model=model,
            device=device,
            language=language,
        )
        if tokens:
            return tokens, False
        if attempt < attempts:
            logger.warning(
                "WhisperX produced no tokens (attempt %d/%d), retrying...",
                attempt,
                attempts,
            )
    logger.warning(
        "WhisperX exhausted %d attempt(s) without producing tokens; falling back to heuristics.",
        attempts,
    )
    return [], True


def clear_model_cache() -> None:
    """Clear the cached alignment models to free memory."""
    with _model_cache_lock:
        _model_cache.clear()
    logger.info("WhisperX model cache cleared")


__all__ = ["align_sentence", "retry_alignment", "clear_model_cache"]
