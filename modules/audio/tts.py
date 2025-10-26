"""Text-to-speech helpers for audio generation."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydub import AudioSegment

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.audio.api import AudioService
from modules.audio.backends import GTTSBackend, MacOSSayBackend, TTSBackendError

logger = log_mgr.logger

AUTO_MACOS_VOICE = "macOS-auto"
AUTO_MACOS_VOICE_FEMALE = "macOS-auto-female"
AUTO_MACOS_VOICE_MALE = "macOS-auto-male"
_VOICE_QUALITIES = ("Premium", "Enhanced")
_AVFOUNDATION_SCRIPT = """
from AVFoundation import AVSpeechSynthesisVoice

def _quality_label(value: int) -> str:
    if value == 3:
        return "Premium"
    if value == 2:
        return "Enhanced"
    if value == 1:
        return "High"
    return "Default"


def _gender_label(value: int) -> str:
    if value == 2:
        return "female"
    if value == 1:
        return "male"
    return "unknown"


for voice in AVSpeechSynthesisVoice.speechVoices():
    quality = _quality_label(voice.quality())
    gender = _gender_label(voice.gender())
    print(f"{voice.name()} - {voice.language()} - {gender} - {quality}")
"""
_AUTO_VOICE_CACHE: Dict[Tuple[str, str], Optional[Tuple[str, str, str, Optional[str]]]] = {}

_LANGUAGE_TO_MACOS_LOCALES: Dict[str, Tuple[str, ...]] = {
    "en": ("en_US", "en_GB", "en_AU", "en_ZA", "en_IE"),
    "es": ("es_ES", "es_MX"),
    "ja": ("ja_JP",),
}

_SILENCE_LOCK = Lock()
_SILENCE_FILENAME = "silence.wav"
SILENCE_DURATION_MS = 100


def active_tmp_dir() -> str:
    """Return the effective temporary directory for media generation."""

    context = cfg.get_runtime_context(None)
    if context is not None:
        return str(context.tmp_dir)
    return tempfile.gettempdir()


def silence_audio_path() -> str:
    """Return the shared silence audio file, creating it if necessary."""

    tmp_dir = active_tmp_dir()
    os.makedirs(tmp_dir, exist_ok=True)
    silence_path = os.path.join(tmp_dir, _SILENCE_FILENAME)

    if os.path.exists(silence_path):
        return silence_path

    with _SILENCE_LOCK:
        if not os.path.exists(silence_path):
            silent = AudioSegment.silent(duration=SILENCE_DURATION_MS)
            silent.export(silence_path, format="wav")
    return silence_path


def _macos_voice_directories() -> Tuple[Path, ...]:
    return (
        Path("/System/Library/Speech/Voices"),
        Path("/Library/Speech/Voices"),
        Path.home() / "Library/Speech/Voices",
    )


@lru_cache(maxsize=1)
def _macos_voice_gender_map() -> Dict[str, Optional[str]]:
    """Return a mapping of macOS voice names to gender identifiers."""

    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return {}

    genders: Dict[str, Optional[str]] = {}
    for directory in _macos_voice_directories():
        if not directory.exists():
            continue
        for voice_dir in directory.rglob("*.SpeechVoice"):
            info_plist = voice_dir / "Contents" / "Info.plist"
            if not info_plist.exists():
                continue
            try:
                with info_plist.open("rb") as fh:
                    info = plistlib.load(fh)
            except Exception as exc:  # pragma: no cover - defensive parsing
                logger.debug("Unable to load metadata for %s: %s", voice_dir, exc)
                continue
            voice_name = info.get("VoiceName") or voice_dir.stem
            raw_gender = info.get("VoiceGender") or info.get("VoiceGenderIdentifier")
            normalized: Optional[str] = None
            if isinstance(raw_gender, str):
                lowered = raw_gender.lower()
                if "female" in lowered:
                    normalized = "female"
                elif "male" in lowered:
                    normalized = "male"
            genders.setdefault(voice_name, normalized)
    return genders


@lru_cache(maxsize=1)
def _parse_avfoundation_line(line: str) -> Optional[Tuple[str, str, str, Optional[str]]]:
    candidate = line.strip()
    if not candidate:
        return None

    parts = [segment.strip() for segment in candidate.split(" - ")]
    if len(parts) < 4:
        return None

    name, locale, gender, quality = parts[0], parts[1], parts[2], parts[3]
    if not name or not locale:
        return None

    normalized_gender: Optional[str] = gender.lower() if gender else None
    if normalized_gender == "unknown":
        normalized_gender = None

    normalized_quality = quality.strip() if quality else ""

    return (name, locale, normalized_quality, normalized_gender)


def _collect_avfoundation_inventory() -> List[Tuple[str, str, str, Optional[str]]]:
    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return []

    executable = sys.executable or "python3"
    try:
        output = subprocess.check_output([executable, "-c", _AVFOUNDATION_SCRIPT], text=True)
    except Exception as exc:  # pragma: no cover - platform specific
        logger.debug("Unable to query AVFoundation voices: %s", exc)
        return []

    voices: List[Tuple[str, str, str, Optional[str]]] = []
    for line in output.splitlines():
        parsed = _parse_avfoundation_line(line)
        if parsed:
            voices.append(parsed)
    return voices


def _collect_say_inventory() -> List[Tuple[str, str, str, Optional[str]]]:
    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return []
    try:
        output = subprocess.check_output(["say", "-v", "?"], universal_newlines=True)
    except Exception as exc:  # pragma: no cover - platform specific
        logger.debug("Unable to query macOS voices: %s", exc)
        return []

    gender_map = _macos_voice_gender_map()
    voices: List[Tuple[str, str, str, Optional[str]]] = []
    for line in output.splitlines():
        details = line.strip().split("#")[0].strip().split()
        if not details:
            continue
        quality = ""
        if len(details) >= 3 and details[1].startswith("("):
            quality = details[1].strip("()")
            locale = details[2]
        elif len(details) >= 2:
            locale = details[1]
        else:
            continue
        voice_name = details[0]
        gender = gender_map.get(voice_name)
        voices.append((voice_name, locale, quality, gender))
    return voices


@lru_cache(maxsize=1)
def _cached_macos_voice_inventory() -> Tuple[Tuple[str, str, str, Optional[str]], ...]:
    """Return macOS voice inventory as tuples of (voice, locale, quality, gender)."""

    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return tuple()

    voices = _collect_avfoundation_inventory()
    if not voices:
        voices = _collect_say_inventory()

    return tuple(voices)


def macos_voice_inventory(*, debug_enabled: bool = False) -> List[Tuple[str, str, str, Optional[str]]]:
    """Expose cached macOS voice inventory for other modules."""

    voices = list(_cached_macos_voice_inventory())
    if debug_enabled and sys.platform == "darwin" and not voices:  # pragma: no cover - platform specific
        logger.debug("No macOS voices discovered via `say -v ?`.")
    return voices


def _normalize_locale(locale: str) -> str:
    return locale.lower().replace("_", "-")


def _locale_matches(lang_code: str, locale: str) -> bool:
    normalized = lang_code.lower()
    short = normalized.split("-")[0]
    candidate = _normalize_locale(locale)
    return (
        candidate == normalized
        or candidate.startswith(f"{normalized}-")
        or candidate == short
        or candidate.startswith(f"{short}-")
    )


def _unique_preserving_order(values: Iterable[str]) -> Tuple[str, ...]:
    """Return ``values`` with duplicates removed while preserving order."""

    seen = set()
    result: List[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def _language_variants(language: str) -> Tuple[str, ...]:
    """Return locale variants to consider for ``language`` selection."""

    normalized = language.strip()
    if not normalized:
        return tuple()

    normalized = normalized.replace("-", "_")
    lowered = normalized.lower()
    short = lowered.split("_")[0]
    preferred_locales = _LANGUAGE_TO_MACOS_LOCALES.get(short, tuple())

    candidates: List[str] = list(preferred_locales)
    candidates.append(normalized)
    if short:
        candidates.append(short)
    return _unique_preserving_order(candidates)


def _gender_priority(preference: str) -> List[Optional[Iterable[str]]]:
    """Return search order for genders given ``preference``."""

    normalized = preference.strip().lower()
    if normalized == "female":
        return [["female"], ["male"], None]
    if normalized == "male":
        return [["male"], ["female"], None]
    return [["female", "male"], None]


def _select_macos_voice_candidate(
    language_variants: Sequence[str], preference: str
) -> Optional[Tuple[str, str, str, Optional[str]]]:
    """Return best macOS voice tuple for ``language_variants`` and ``preference``."""

    voices = macos_voice_inventory()
    if not voices:
        return None

    variants = tuple(language_variants)
    if not variants:
        return None

    filtered: List[Tuple[str, str, str, Optional[str]]] = [
        voice
        for voice in voices
        if voice[2] in _VOICE_QUALITIES
        and any(_locale_matches(variant, voice[1]) for variant in variants)
    ]
    if not filtered:
        return None

    gender_cycles = _gender_priority(preference)

    for genders in gender_cycles:
        best_voice: Optional[Tuple[str, str, str, Optional[str]]] = None
        best_rank: Optional[Tuple[int, int]] = None
        for voice in filtered:
            voice_gender = voice[3]
            if genders is not None and voice_gender not in genders:
                continue
            try:
                quality_rank = _VOICE_QUALITIES.index(voice[2])
            except ValueError:
                continue
            locale_rank = min(
                (
                    index
                    for index, variant in enumerate(variants)
                    if _locale_matches(variant, voice[1])
                ),
                default=len(variants),
            )
            rank = (quality_rank, locale_rank)
            if best_rank is None or rank < best_rank:
                best_rank = rank
                best_voice = voice
        if best_voice is not None:
            return best_voice
    return None


def _format_voice_display(voice: Tuple[str, str, str, Optional[str]]) -> str:
    """Return human-readable string for ``voice`` tuple."""

    name, locale, quality, gender = voice
    gender_suffix = f" - {gender.capitalize()}" if gender else ""
    return f"{name} - {locale} - ({quality}){gender_suffix}"


def _gtts_fallback(language: str) -> str:
    """Return fallback identifier for gTTS based on ``language``."""

    normalized = language.strip().lower()
    if not normalized:
        return "gTTS-en"
    short = normalized.replace("_", "-").split("-")[0]
    short = short or "en"
    return f"gTTS-{short}"


def select_voice(language: str, voice_preference: str) -> str:
    """Select a voice identifier for ``language`` respecting ``voice_preference``."""

    variants = _language_variants(language)
    candidate = _select_macos_voice_candidate(variants, voice_preference)
    if candidate is not None:
        return _format_voice_display(candidate)
    return _gtts_fallback(language)


def _synthesize_with_gtts(text: str, lang_code: str, speed: int) -> AudioSegment:
    service = AudioService(backend_name=GTTSBackend.name)
    return service.synthesize(
        text=text,
        voice="gTTS",
        speed=speed,
        lang_code=lang_code,
    )


def _resolve_auto_voice_preference(selected_voice: str) -> str:
    if selected_voice == AUTO_MACOS_VOICE_FEMALE:
        return "female"
    if selected_voice == AUTO_MACOS_VOICE_MALE:
        return "male"
    return "any"


def _resolve_macos_voice_name(selected_voice: str, lang_code: str) -> Optional[str]:
    if selected_voice in {AUTO_MACOS_VOICE, AUTO_MACOS_VOICE_FEMALE, AUTO_MACOS_VOICE_MALE}:
        preference = _resolve_auto_voice_preference(selected_voice)
        cache_key = (lang_code, preference)
        cached_voice = _AUTO_VOICE_CACHE.get(cache_key)
        if cache_key not in _AUTO_VOICE_CACHE:
            variants = _language_variants(lang_code)
            cached_voice = _select_macos_voice_candidate(variants, preference)
            _AUTO_VOICE_CACHE[cache_key] = cached_voice
        if cached_voice:
            voice_name, _locale, _quality, _gender = cached_voice
            return voice_name
        return None

    parts = selected_voice.split(" - ", 1)
    voice_name = parts[0].strip()
    voice_locale = parts[1].strip() if len(parts) >= 2 else ""

    if not voice_name:
        return None

    if voice_locale and not _locale_matches(lang_code, voice_locale):
        return None

    return voice_name


def generate_audio(
    text: str,
    lang_code: str,
    selected_voice: str,
    macos_reading_speed: int,
    *,
    config: Optional[Any] = None,
) -> AudioSegment:
    """Generate spoken audio for ``text`` using the configured backend."""

    if selected_voice == "gTTS":
        return _synthesize_with_gtts(text, lang_code, macos_reading_speed)

    service = AudioService(config=config)
    backend = service.get_backend()

    if isinstance(backend, MacOSSayBackend):
        voice_name = _resolve_macos_voice_name(selected_voice, lang_code)
        if voice_name:
            try:
                return service.synthesize(
                    text=text,
                    voice=voice_name,
                    speed=macos_reading_speed,
                    lang_code=lang_code,
                    output_path=None,
                )
            except TTSBackendError:
                log_mgr.console_warning(
                    "MacOS TTS command failed for voice '%s'. Falling back to default gTTS voice.",
                    voice_name,
                    logger_obj=logger,
                )
        else:
            logger.debug(
                "Unable to resolve macOS voice '%s' for language '%s'; using gTTS fallback.",
                selected_voice,
                lang_code,
            )
    else:
        logger.debug(
            "Configured TTS backend '%s' does not support macOS voices; using gTTS fallback.",
            backend.name,
        )

    return _synthesize_with_gtts(text, lang_code, macos_reading_speed)


__all__ = [
    "AUTO_MACOS_VOICE",
    "AUTO_MACOS_VOICE_FEMALE",
    "AUTO_MACOS_VOICE_MALE",
    "SILENCE_DURATION_MS",
    "active_tmp_dir",
    "generate_audio",
    "macos_voice_inventory",
    "select_voice",
    "silence_audio_path",
]
