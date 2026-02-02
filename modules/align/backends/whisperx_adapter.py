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
    """Determine the best available device for alignment.

    Note: We default to CPU for alignment because MPS has recurring issues with
    meta tensors and device mismatches in the Wav2Vec2 alignment models. The
    alignment models are relatively small and CPU inference is reliable.
    CUDA is still used when available since it doesn't have these issues.
    """
    global _default_device
    if _default_device is not None:
        return _default_device

    try:
        import torch
        if torch.cuda.is_available():
            _default_device = "cuda"
        else:
            # Default to CPU - MPS has too many issues with alignment models
            # (meta tensor errors, device mismatches, FloatTensor type conflicts)
            _default_device = "cpu"
    except ImportError:
        _default_device = "cpu"

    logger.debug("WhisperX alignment using device: %s", _default_device)
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


def _load_align_model_no_meta_tensors(
    language: str,
    model_name: Optional[str] = None,
) -> Tuple[Any, dict]:
    """
    Load alignment model directly without meta tensors.

    This is a fallback for models that fail with "Cannot copy out of meta tensor"
    error. It loads the model with low_cpu_mem_usage=False to avoid meta tensors.
    """
    try:
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        import torchaudio
    except ImportError as exc:
        logger.warning("Required libraries not available for direct model load: %s", exc)
        raise

    # WhisperX default alignment models by language
    # See: https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py
    DEFAULT_ALIGN_MODELS = {
        "en": "WAV2VEC2_ASR_BASE_960H",
        "fr": "VOXPOPULI_ASR_BASE_10K_FR",
        "de": "VOXPOPULI_ASR_BASE_10K_DE",
        "es": "VOXPOPULI_ASR_BASE_10K_ES",
        "it": "VOXPOPULI_ASR_BASE_10K_IT",
        "ja": "jonatasgrosman/wav2vec2-large-xlsr-53-japanese",
        "zh": "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn",
        "nl": "jonatasgrosman/wav2vec2-large-xlsr-53-dutch",
        "uk": "Yehor/wav2vec2-xls-r-300m-uk-with-small-lm",
        "pt": "jonatasgrosman/wav2vec2-large-xlsr-53-portuguese",
        "ar": "jonatasgrosman/wav2vec2-large-xlsr-53-arabic",
        "cs": "comodoro/wav2vec2-xls-r-300m-cs-250",
        "ru": "jonatasgrosman/wav2vec2-large-xlsr-53-russian",
        "pl": "jonatasgrosman/wav2vec2-large-xlsr-53-polish",
        "hu": "jonatasgrosman/wav2vec2-large-xlsr-53-hungarian",
        "fi": "jonatasgrosman/wav2vec2-large-xlsr-53-finnish",
        "fa": "jonatasgrosman/wav2vec2-large-xlsr-53-persian",
        "el": "jonatasgrosman/wav2vec2-large-xlsr-53-greek",
        "tr": "mpoyraz/wav2vec2-xls-r-300m-cv7-turkish",
        "da": "saattrupdan/wav2vec2-xls-r-300m-ftspeech",
        "he": "imvladikon/wav2vec2-xls-r-300m-hebrew",
        "vi": "nguyenvulebinh/wav2vec2-base-vi",
        "ko": "kresnik/wav2vec2-large-xlsr-korean",
        "ur": "kingabzpro/wav2vec2-large-xls-r-300m-Urdu",
        "te": "anuragshas/wav2vec2-large-xlsr-53-telugu",
        "hi": "theainerd/Wav2Vec2-large-xlsr-hindi",
        "ca": "softcatala/wav2vec2-large-xlsr-catala",
        "ta": "Amrrs/wav2vec2-large-xlsr-53-tamil",
        "th": "sakares/wav2vec2-large-xlsr-thai-demo",
        "sw": "alokmatta/wav2vec2-large-xlsr-53-sw",
        "lt": "lexlexical/wav2vec2-common-voice-large-lv-colab",
    }

    # Determine the model to use
    if model_name:
        hf_model = model_name
    elif language in DEFAULT_ALIGN_MODELS:
        hf_model = DEFAULT_ALIGN_MODELS[language]
    else:
        raise ValueError(f"No default align-model for language: {language}")

    # Check if it's a torchaudio bundle or HuggingFace model
    if hf_model.startswith("WAV2VEC2") or hf_model.startswith("VOXPOPULI"):
        # torchaudio bundle
        logger.info("Loading torchaudio bundle: %s", hf_model)
        bundle = getattr(torchaudio.pipelines, hf_model)
        model = bundle.get_model()
        labels = bundle.get_labels()
        metadata = {
            "language": language,
            "dictionary": {c: i for i, c in enumerate(labels)},
            "type": "torchaudio",
        }
    else:
        # HuggingFace model - load with low_cpu_mem_usage=False to avoid meta tensors
        logger.info("Loading HuggingFace model without meta tensors: %s", hf_model)
        processor = Wav2Vec2Processor.from_pretrained(hf_model)
        model = Wav2Vec2ForCTC.from_pretrained(hf_model, low_cpu_mem_usage=False)

        # Build dictionary from processor vocabulary
        vocab = processor.tokenizer.get_vocab()
        metadata = {
            "language": language,
            "dictionary": vocab,
            "type": "huggingface",
        }

    logger.info("Successfully loaded alignment model for '%s' without meta tensors", language)
    return model, metadata


def _get_alignment_model(
    language: str,
    device: str,
    model_name: Optional[str] = None,
) -> Tuple[Any, dict]:
    """Get or create a cached alignment model for the given language.

    We prefer our direct model loading method which avoids meta tensors.
    This is more reliable than whisperx.load_align_model() which can load
    models with meta tensors that cause device mismatch errors.

    Thread-safety: The entire loading process is protected by a lock to prevent
    concurrent model loading which can cause meta tensor issues with transformers.
    """

    # Filter out invalid Whisper model names - let WhisperX choose the default
    if model_name and not _is_valid_alignment_model(model_name):
        logger.debug(
            "Ignoring invalid alignment model '%s' (looks like a Whisper model); "
            "using WhisperX default for language '%s'",
            model_name,
            language,
        )
        model_name = None

    # Always use CPU for cache key since we default to CPU now
    cache_key = f"{language}:cpu:{model_name or 'default'}"

    # Hold the lock for the entire cache check + loading process to prevent
    # concurrent model loads which cause meta tensor issues
    with _model_cache_lock:
        if cache_key in _model_cache:
            logger.debug("Using cached alignment model for %s", cache_key)
            return _model_cache[cache_key]

        logger.info(
            "Loading alignment model for language='%s', model='%s' (using direct load to avoid meta tensors)",
            language,
            model_name or "default",
        )

        # Try our direct loading method first - it avoids meta tensor issues
        try:
            model, metadata = _load_align_model_no_meta_tensors(language, model_name)
            _model_cache[cache_key] = (model, metadata)
            logger.info(
                "Alignment model loaded successfully: language='%s', model='%s'",
                language,
                model_name or "default",
            )
            return model, metadata
        except ValueError:
            # Language not in our known list - fall back to whisperx
            logger.debug(
                "Language '%s' not in direct loader, trying whisperx.load_align_model",
                language,
            )
        except Exception as exc:
            logger.warning(
                "Direct model load failed for language '%s': %s, trying whisperx fallback",
                language,
                exc,
            )

        # Fall back to whisperx.load_align_model for unsupported languages
        whisperx = _get_whisperx()
        try:
            model, metadata = whisperx.load_align_model(
                language_code=language,
                device="cpu",  # Always use CPU to avoid meta tensor issues
                model_name=model_name,
            )
        except ValueError as exc:
            # No model available for this language
            logger.warning("No alignment model available for language '%s': %s", language, exc)
            raise
        except Exception as exc:
            logger.warning("Failed to load alignment model: %s", exc, exc_info=True)
            raise

        _model_cache[cache_key] = (model, metadata)

        # Log the actual model that was loaded (helpful for troubleshooting)
        resolved_model_name = metadata.get("language", model_name) if isinstance(metadata, dict) else model_name
        logger.info(
            "WhisperX alignment model loaded: language='%s', resolved_model='%s'",
            language,
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
        exc_str = str(exc)
        exc_lower = exc_str.lower()
        # Check for device mismatch errors during inference
        # These can occur with MPS when tensors end up on wrong device
        if resolved_device != "cpu" and (
            "meta" in exc_str
            or "expected device" in exc_str
            or "device mismatch" in exc_lower
            or ("mps" in exc_lower and "floattensor" in exc_lower)
            or "input type" in exc_lower and "weight type" in exc_lower
        ):
            logger.warning(
                "WhisperX alignment failed on %s (device error: %s), retrying on CPU",
                resolved_device,
                exc,
            )
            # Clear cached model for this language/device combo to force reload on CPU
            cache_key = f"{resolved_language}:{resolved_device}:{model or 'default'}"
            with _model_cache_lock:
                _model_cache.pop(cache_key, None)
            # Retry with CPU
            return align_sentence(
                audio_path,
                text,
                model=model,
                device="cpu",
                language=resolved_language,
            )
        logger.warning("WhisperX alignment failed: %s", exc)
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
