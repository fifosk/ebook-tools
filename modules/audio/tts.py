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
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
_AUTO_VOICE_CACHE: Dict[Tuple[str, str], Optional[Tuple[str, str, str, Optional[str]]]] = {}

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
def _cached_macos_voice_inventory() -> Tuple[Tuple[str, str, str, Optional[str]], ...]:
    """Return macOS voice inventory as tuples of (voice, locale, quality, gender)."""

    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return tuple()
    try:
        output = subprocess.check_output(["say", "-v", "?"], universal_newlines=True)
    except Exception as exc:  # pragma: no cover - platform specific
        logger.debug("Unable to query macOS voices: %s", exc)
        return tuple()

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


def select_voice(lang_code: str, gender_preference: str) -> Optional[Tuple[str, str, str, Optional[str]]]:
    """Return the best matching macOS voice for ``lang_code`` and gender preference."""

    voices = macos_voice_inventory()
    if not voices:
        return None

    candidates = [
        voice
        for voice in voices
        if voice[2] in _VOICE_QUALITIES and _locale_matches(lang_code, voice[1])
    ]
    if not candidates:
        return None

    gender_cycles: List[Optional[Iterable[str]]]
    if gender_preference == "female":
        gender_cycles = [["female"], ["male"], None]
    elif gender_preference == "male":
        gender_cycles = [["male"], ["female"], None]
    else:
        gender_cycles = [["female", "male"], None]

    for genders in gender_cycles:
        for desired_quality in _VOICE_QUALITIES:
            for voice in candidates:
                voice_gender = voice[3]
                if genders is not None and voice_gender not in genders:
                    continue
                if voice[2] == desired_quality:
                    return voice
    return None


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
            cached_voice = select_voice(lang_code, preference)
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
