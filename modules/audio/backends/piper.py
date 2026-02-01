"""Piper TTS backend implementation.

Piper is a fast, local neural text-to-speech system that runs entirely offline.
Voice models use ONNX format and require two files per voice:
  - <voice_name>.onnx - The neural network model
  - <voice_name>.onnx.json - Configuration and phoneme mappings

Download models from: https://github.com/rhasspy/piper/releases
or: https://huggingface.co/rhasspy/piper-voices

Voice naming convention: <lang>_<region>-<voice_name>-<quality>
Example: en_US-lessac-medium, de_DE-thorsten-high, ar_JO-kareem-medium

PLATFORM NOTES:
- Linux: Fully supported via piper-tts Python package
- macOS: Requires espeak-ng (`brew install espeak-ng`) and may need manual
  compilation of the espeakbridge extension. Use Docker or the standalone
  piper binary as alternatives.
- Windows: Supported via piper-tts with prebuilt wheels
"""

from __future__ import annotations

import io
import os
import tempfile
import wave
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Mapping, Optional, Tuple

import yaml
from pydub import AudioSegment

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.core.storage_config import get_piper_models_path

from .base import BaseTTSBackend, TTSBackendError

logger = log_mgr.logger

# Configuration file path
_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
_PIPER_VOICES_CONFIG_PATH = _CONFIG_DIR / "piper_voices.yaml"

# Lazy-loaded piper module
_piper_voice_module: Optional[Any] = None
_piper_lock = Lock()

# Voice model cache (thread-safe)
_voice_cache: Dict[str, Any] = {}
_voice_cache_lock = Lock()


def _get_piper_voice_module() -> Any:
    """Lazy-load piper.voice to avoid import errors when not installed."""
    global _piper_voice_module
    if _piper_voice_module is not None:
        return _piper_voice_module

    with _piper_lock:
        if _piper_voice_module is not None:
            return _piper_voice_module
        try:
            from piper import voice as piper_voice

            _piper_voice_module = piper_voice
            logger.debug("Piper TTS library loaded successfully")
            return piper_voice
        except ImportError as exc:
            logger.warning("Piper TTS not installed: %s", exc)
            raise TTSBackendError(
                "Piper TTS not installed. Install with: pip install piper-tts"
            ) from exc


@lru_cache(maxsize=1)
def load_piper_voice_config(path: Optional[str] = None) -> Mapping[str, Any]:
    """Load Piper voice configuration from YAML.

    Args:
        path: Optional path to config file. Defaults to config/piper_voices.yaml.

    Returns:
        Configuration dictionary with 'voices' and 'fallbacks' sections.
    """
    config_path = Path(path) if path else _PIPER_VOICES_CONFIG_PATH
    if not config_path.exists():
        logger.warning("Piper voice config not found at %s", config_path)
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        logger.error("Failed to parse Piper voice config: %s", exc)
        return {}

    return config


def get_voice_for_language(lang_code: str) -> Optional[str]:
    """Get the best available Piper voice for a language code.

    Args:
        lang_code: ISO language code (e.g., 'en', 'de', 'ar')

    Returns:
        Voice model name if found, None otherwise.
    """
    config = load_piper_voice_config()
    voices_map = config.get("voices", {})
    fallbacks = config.get("fallbacks", {})

    # Normalize language code (handle en_US, en-US, en variants)
    normalized = lang_code.lower().replace("-", "_").split("_")[0]

    # Direct lookup
    if normalized in voices_map:
        voice_list = voices_map[normalized]
        if isinstance(voice_list, list) and voice_list:
            return _find_available_voice(voice_list)
        elif isinstance(voice_list, str):
            return _find_available_voice([voice_list])

    # Fallback lookup
    fallback_lang = fallbacks.get(normalized)
    if fallback_lang and fallback_lang in voices_map:
        voice_list = voices_map[fallback_lang]
        if isinstance(voice_list, list) and voice_list:
            logger.debug(
                "Using fallback voice for %s -> %s", lang_code, fallback_lang
            )
            return _find_available_voice(voice_list)

    return None


def _find_available_voice(voice_list: List[str]) -> Optional[str]:
    """Find the first available voice from a list.

    Checks if model files exist locally. If none found locally,
    returns the first voice in the list (will need to be downloaded).

    Args:
        voice_list: List of voice model names to check.

    Returns:
        Voice name if found, None if list is empty.
    """
    models_path = get_piper_models_path()

    for voice_name in voice_list:
        # Check for model files
        model_path = models_path / f"{voice_name}.onnx"
        if model_path.exists():
            return voice_name

    # If no local model found, return first in list (will be downloaded)
    return voice_list[0] if voice_list else None


def _get_voice_model(voice_name: str) -> Any:
    """Get or load a cached Piper voice model.

    Models are cached to avoid repeated loading overhead.

    Args:
        voice_name: Name of the voice model (e.g., 'en_US-lessac-medium')

    Returns:
        Loaded PiperVoice instance.

    Raises:
        TTSBackendError: If model files not found or loading fails.
    """
    cache_key = voice_name

    with _voice_cache_lock:
        if cache_key in _voice_cache:
            return _voice_cache[cache_key]

    piper_voice_module = _get_piper_voice_module()
    models_path = get_piper_models_path()

    model_path = models_path / f"{voice_name}.onnx"
    config_path = models_path / f"{voice_name}.onnx.json"

    if not model_path.exists():
        raise TTSBackendError(
            f"Piper voice model not found: {model_path}. "
            f"Download from https://github.com/rhasspy/piper/releases "
            f"and place in {models_path}"
        )

    config_path_str = str(config_path) if config_path.exists() else None

    try:
        voice = piper_voice_module.PiperVoice.load(
            str(model_path), config_path_str
        )
    except Exception as exc:
        raise TTSBackendError(
            f"Failed to load Piper voice '{voice_name}': {exc}"
        ) from exc

    with _voice_cache_lock:
        _voice_cache[cache_key] = voice

    logger.info("Loaded Piper voice model: %s", voice_name)
    return voice


def get_speed_multiplier(lang_code: str) -> float:
    """Get the speed multiplier for a language to normalize speech rates.

    Different Piper voice models have different natural speaking rates.
    This multiplier adjusts speed so all languages sound similar pace.

    Args:
        lang_code: ISO language code (e.g., 'en', 'ar', 'zh')

    Returns:
        Speed multiplier (1.0 = no change, >1.0 = faster, <1.0 = slower)
    """
    config = load_piper_voice_config()
    multipliers = config.get("speed_multipliers", {})

    # Normalize language code
    normalized = lang_code.lower().replace("-", "_").split("_")[0]

    return float(multipliers.get(normalized, 1.0))


def _speed_to_length_scale(speed: int, lang_code: str = "en") -> float:
    """Convert speed (words per minute) to Piper length_scale.

    Piper uses length_scale to control speech rate:
      - length_scale < 1.0 = faster speech
      - length_scale > 1.0 = slower speech
      - length_scale = 1.0 = normal speed

    Reference: macOS 'say' uses ~175 WPM as default (speed=175).

    Args:
        speed: Words per minute (positive integer).
        lang_code: Language code for speed multiplier adjustment.

    Returns:
        Length scale value clamped to [0.5, 2.0].
    """
    baseline_speed = 175

    if speed <= 0:
        return 1.0

    # Apply language-specific speed multiplier
    multiplier = get_speed_multiplier(lang_code)
    effective_speed = speed * multiplier

    # Inverse relationship: higher speed = lower length_scale
    length_scale = baseline_speed / effective_speed

    # Clamp to reasonable range
    return max(0.5, min(2.0, length_scale))


class PiperTTSBackend(BaseTTSBackend):
    """Backend using Piper TTS for local neural speech synthesis.

    Piper is a fast, offline TTS system using ONNX models. It supports
    51 languages with various voice models.

    Voice selection priority:
      1. Explicit Piper model name (e.g., 'en_US-lessac-medium')
      2. Auto-select from language code using piper_voices.yaml
      3. Fallback to related language if no direct match
    """

    name = "piper"

    def __init__(self, *, executable_path: Optional[str] = None) -> None:
        """Initialize Piper backend.

        Args:
            executable_path: Not used for Piper (uses Python library).
        """
        super().__init__(executable_path=executable_path)
        self._models_path = get_piper_models_path()

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        speed: int,
        lang_code: str,
        output_path: Optional[str] = None,
    ) -> AudioSegment:
        """Generate speech audio using Piper TTS.

        Args:
            text: Text to synthesize.
            voice: Voice identifier or 'auto'/'piper' for auto-selection.
            speed: Speech rate in words per minute (baseline: 175).
            lang_code: ISO language code for voice selection.
            output_path: Optional path to save WAV file.

        Returns:
            AudioSegment containing the synthesized speech.

        Raises:
            TTSBackendError: If no voice available or synthesis fails.
        """
        # Resolve voice name
        voice_name = self._resolve_voice(voice, lang_code)
        if not voice_name:
            raise TTSBackendError(
                f"No Piper voice available for language '{lang_code}'. "
                f"Check config/piper_voices.yaml for supported languages."
            )

        # Load voice model
        try:
            piper_voice = _get_voice_model(voice_name)
        except TTSBackendError:
            raise
        except Exception as exc:
            raise TTSBackendError(f"Failed to load Piper voice: {exc}") from exc

        # Calculate length scale from speed (with language-specific adjustment)
        length_scale = _speed_to_length_scale(speed, lang_code)

        # Generate audio using piper-tts 1.4+ API
        try:
            from piper.config import SynthesisConfig

            syn_config = SynthesisConfig(
                length_scale=length_scale,
            )

            # Collect audio chunks from the generator
            audio_chunks = []
            for chunk in piper_voice.synthesize(text, syn_config=syn_config):
                audio_chunks.append(chunk.audio_int16_bytes)

            if not audio_chunks:
                raise TTSBackendError("Piper synthesis returned no audio")

            # Combine all chunks into a single WAV
            combined_audio = b"".join(audio_chunks)

            # Get sample rate from voice config
            sample_rate = piper_voice.config.sample_rate

            # Create WAV file in memory
            audio_bytes = io.BytesIO()
            with wave.open(audio_bytes, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(combined_audio)
            audio_bytes.seek(0)

            # Convert to AudioSegment
            audio = AudioSegment.from_wav(audio_bytes)

        except TTSBackendError:
            raise
        except Exception as exc:
            raise TTSBackendError(f"Piper synthesis failed: {exc}") from exc

        # Export if output path specified
        if output_path:
            audio.export(output_path, format="wav")

        return audio

    def _resolve_voice(self, voice: str, lang_code: str) -> Optional[str]:
        """Resolve voice identifier to Piper model name.

        Args:
            voice: Voice identifier (model name, 'auto', or 'piper').
            lang_code: Language code for auto-selection.

        Returns:
            Resolved voice model name, or None if not found.
        """
        # If voice looks like a Piper model name, use it directly
        # Format: <lang>_<region>-<name>-<quality> (e.g., en_US-lessac-medium)
        if "_" in voice and "-" in voice:
            return voice

        # Auto-select based on language
        if voice.lower() in ("auto", "piper", "piper-auto"):
            return get_voice_for_language(lang_code)

        # Try to find voice matching the provided name
        config = load_piper_voice_config()
        voices_map = config.get("voices", {})

        for lang_voices in voices_map.values():
            if isinstance(lang_voices, list):
                for v in lang_voices:
                    if voice.lower() in v.lower():
                        return v

        # Fallback to language-based selection
        return get_voice_for_language(lang_code)

    def list_available_voices(self) -> List[Tuple[str, str, str]]:
        """List all available Piper voices (installed locally).

        Returns:
            List of tuples: (voice_name, lang_region, quality)
        """
        voices: List[Tuple[str, str, str]] = []

        if not self._models_path.exists():
            return voices

        for model_file in self._models_path.glob("*.onnx"):
            voice_name = model_file.stem
            # Parse voice name: lang_region-name-quality
            parts = voice_name.split("-")
            if len(parts) >= 2:
                lang_region = parts[0]
                quality = parts[-1] if len(parts) >= 3 else "unknown"
                voices.append((voice_name, lang_region, quality))

        return sorted(voices)


def clear_voice_cache() -> None:
    """Clear the cached voice models to free memory."""
    with _voice_cache_lock:
        _voice_cache.clear()
    logger.info("Piper voice cache cleared")


__all__ = [
    "PiperTTSBackend",
    "clear_voice_cache",
    "get_speed_multiplier",
    "get_voice_for_language",
    "load_piper_voice_config",
]
