"""Text-to-speech helpers for audio generation."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import tempfile
import textwrap
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

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

_LANGUAGE_TO_MACOS_LOCALES: Dict[str, Tuple[str, ...]] = {
    "en": ("en_US", "en_GB", "en_AU", "en_ZA", "en_IE"),
    "es": ("es_ES", "es_MX"),
    "ja": ("ja_JP",),
}

# Map unsupported languages to close TTS-capable fallbacks.
_VOICE_LANG_FALLBACKS = {
    # Romani lacks native TTS coverage; lean on Slovak.
    "rom": "sk",
    "romani": "sk",
    # Pashto unavailable in gTTS; lean on Urdu.
    "ps": "ur",
    "pashto": "ur",
    # Languages missing in gTTS mapped to closest available cousins.
    "armenian": "ru",
    "be": "ru",  # Belarusian → Russian
    "belarusian": "ru",
    "eo": "it",  # Esperanto → Italian (phonetic, common)
    "esperanto": "it",
    "fa": "ur",  # Persian/Farsi → Urdu
    "farsi": "ur",
    "fo": "da",  # Faroese → Danish
    "faroese": "da",
    "georgian": "ru",
    "hy": "ru",  # Armenian → Russian
    "ka": "ru",  # Georgian → Russian
    "kazakh": "tr",
    "kk": "tr",  # Kazakh → Turkish
    "kyrgyz": "tr",
    "ky": "tr",  # Kyrgyz → Turkish
    "lb": "de",  # Luxembourgish → German
    "luxembourgish": "de",
    "macedonian": "bg",
    "mk": "bg",  # Macedonian → Bulgarian
    "maltese": "it",
    "mn": "ru",  # Mongolian → Russian
    "mongolian": "ru",
    "mt": "it",  # Maltese → Italian
    "persian": "ur",
    "sl": "sr",  # Slovenian → Serbian
    "slovenian": "sr",
    "tajik": "fa",
    "tg": "fa",  # Tajik → Persian
    "tk": "tr",  # Turkmen → Turkish
    "turkmen": "tr",
    "uz": "tr",  # Uzbek → Turkish
    "uzbek": "tr",
    "xh": "zu",  # Xhosa → Zulu
    "xhosa": "zu",
    "yo": "sw",  # Yoruba → Swahili
    "yoruba": "sw",
    "zu": "xh",  # Zulu → Xhosa
    "zulu": "xh",
    # Celtic languages without broad TTS coverage fall back to English voices.
    "ga": "en",
    "irish": "en",
    "gd": "en",
    "scottish gaelic": "en",
    "sco": "en",
    "scots": "en",
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


def _apply_voice_language_fallback(language: str) -> str:
    """Return a TTS-friendly language code with fallbacks for unsupported locales."""

    normalized = language.strip().lower()
    if not normalized:
        return language
    short = normalized.replace("_", "-").split("-")[0]
    fallback = _VOICE_LANG_FALLBACKS.get(normalized) or _VOICE_LANG_FALLBACKS.get(short)
    return fallback or language


@lru_cache(maxsize=1)
def _available_gtts_languages() -> Tuple[str, ...]:
    """Return gTTS language identifiers as a cached tuple."""

    try:
        from gtts.lang import tts_langs

        langs = tts_langs()
        return tuple(sorted({code.lower() for code in langs}))
    except Exception:
        return tuple()


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
def _query_macos_voice_inventory_via_avfoundation() -> List[Tuple[str, str, str, Optional[str]]]:
    """Return macOS voice metadata using ``AVFoundation`` if available."""

    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return []

    script = textwrap.dedent(
        """
        import json
        from AVFoundation import AVSpeechSynthesisVoice

        QUALITY_MAP = {
            0: "Default",
            1: "Default",
            2: "Enhanced",
            3: "Premium",
        }
        GENDER_MAP = {
            1: "male",
            2: "female",
        }

        voices = []
        for voice in AVSpeechSynthesisVoice.speechVoices():
            voices.append(
                {
                    "name": voice.name(),
                    "language": voice.language(),
                    "quality": QUALITY_MAP.get(voice.quality()),
                    "gender": GENDER_MAP.get(voice.gender()),
                }
            )

        print(json.dumps(voices))
        """
    )

    executable = sys.executable or "python3"
    try:
        output = subprocess.check_output(
            [executable, "-c", script], universal_newlines=True
        )
    except Exception as exc:  # pragma: no cover - platform specific
        logger.debug("Unable to query macOS voices via AVFoundation: %s", exc)
        return []

    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive parsing
        logger.debug("Unable to parse AVFoundation voice data: %s", exc)
        return []

    voices: List[Tuple[str, str, str, Optional[str]]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        language = entry.get("language")
        if not name or not language:
            continue
        quality_value = entry.get("quality") or ""
        if isinstance(quality_value, str):
            lowered_quality = quality_value.strip().lower()
            if lowered_quality == "premium":
                quality = "Premium"
            elif lowered_quality == "enhanced":
                quality = "Enhanced"
            elif lowered_quality == "default":
                quality = ""
            else:
                quality = quality_value.strip()
        else:
            quality = ""
        gender_value = entry.get("gender")
        gender: Optional[str]
        if isinstance(gender_value, str):
            gender = gender_value.strip().lower() or None
        else:
            gender = None
        voices.append((name, language, quality, gender))
    return voices


@lru_cache(maxsize=1)
def _cached_macos_voice_inventory() -> Tuple[Tuple[str, str, str, Optional[str]], ...]:
    """Return macOS voice inventory as tuples of (voice, locale, quality, gender)."""

    if sys.platform != "darwin":  # pragma: no cover - platform specific
        return tuple()

    avfoundation_voices = _query_macos_voice_inventory_via_avfoundation()
    if avfoundation_voices:
        return tuple(avfoundation_voices)
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
        logger.debug("No macOS voices discovered via AVFoundation or `say -v ?`.")
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

    def _variants_for(code: str) -> List[str]:
        normalized_code = code.replace("-", "_")
        short_code = normalized_code.lower().split("_")[0]
        preferred_locales = _LANGUAGE_TO_MACOS_LOCALES.get(short_code, tuple())
        variants: List[str] = list(preferred_locales)
        variants.append(normalized_code)
        if short_code:
            variants.append(short_code)
        return variants

    raw_language = (language or "").strip()
    if not raw_language:
        return tuple()

    candidates: List[str] = _variants_for(raw_language)

    fallback_language = _apply_voice_language_fallback(raw_language)
    if fallback_language and fallback_language.strip().lower().replace("-", "_") != raw_language.replace("-", "_").lower():
        candidates.extend(_variants_for(fallback_language))

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

    normalized = normalize_gtts_language_code(language)
    short = normalized.split("-")[0] or "en"
    return f"gTTS-{short}"


def normalize_gtts_language_code(language: str) -> str:
    """Return a gTTS-compatible language code, applying provider quirks."""

    raw = (language or "").strip().lower().replace("_", "-")
    if not raw:
        return "en"

    # Use provider inventory to avoid unnecessary fallbacks when support exists.
    available = _available_gtts_languages()
    have_inventory = bool(available)

    def _is_supported(code: str) -> bool:
        candidate = code.lower()
        base = candidate.split("-")[0]
        return candidate in available or base in available

    def _apply_legacy_hebrew(code: str) -> str:
        base = code.split("-")[0]
        if base in {"he", "hebrew", "heb", "iw"}:
            return "iw"
        return code

    normalized = _apply_legacy_hebrew(raw)
    if have_inventory and _is_supported(normalized):
        return normalized

    fallback = _apply_voice_language_fallback(raw)
    fallback = _apply_legacy_hebrew((fallback or "").strip().lower().replace("_", "-"))
    if fallback and (not have_inventory or _is_supported(fallback)):
        return fallback

    base = normalized.split("-")[0]
    if have_inventory and _is_supported(base):
        return base

    if not have_inventory:
        # Without a provider inventory, prefer a best-effort fallback/base code over English.
        return fallback or base or normalized or "en"

    return "en"


def select_voice(language: str, voice_preference: str) -> str:
    """Select a voice identifier for ``language`` respecting ``voice_preference``."""

    variants = _language_variants(language)
    candidate = _select_macos_voice_candidate(variants, voice_preference)
    if candidate is not None:
        return _format_voice_display(candidate)
    fallback_language = _apply_voice_language_fallback(language)
    return _gtts_fallback(fallback_language)


def _synthesize_with_gtts(text: str, lang_code: str, speed: int) -> AudioSegment:
    lang_code = normalize_gtts_language_code(lang_code)
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
    normalized_lang_code = (lang_code or "").strip()
    if selected_voice in {AUTO_MACOS_VOICE, AUTO_MACOS_VOICE_FEMALE, AUTO_MACOS_VOICE_MALE}:
        preference = _resolve_auto_voice_preference(selected_voice)
        cache_key = (normalized_lang_code, preference)
        cached_voice = _AUTO_VOICE_CACHE.get(cache_key)
        if cache_key not in _AUTO_VOICE_CACHE:
            variants = _language_variants(normalized_lang_code)
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

    if voice_locale and normalized_lang_code and not _locale_matches(normalized_lang_code, voice_locale):
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

    resolved_macos_voice = _resolve_macos_voice_name(selected_voice, lang_code)
    # Force the macOS backend when we have a resolvable macOS voice, regardless of default backend.
    if resolved_macos_voice:
        service = AudioService(config=config, backend_name=MacOSSayBackend.name)
    else:
        service = AudioService(config=config)
    backend = service.get_backend()

    if isinstance(backend, MacOSSayBackend):
        voice_name = resolved_macos_voice or _resolve_macos_voice_name(selected_voice, lang_code)
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


def get_voice_display_name(
    selected_voice: str,
    language: str,
    language_codes: Mapping[str, str] | None = None,
) -> str:
    """Return a human-readable voice label for ``selected_voice``."""

    voice_identifier = (selected_voice or "").strip()
    if not voice_identifier:
        return ""

    language_key = (language or "").strip()
    if language_codes:
        lang_code = language_codes.get(language_key, language_key)
    else:
        lang_code = language_key

    if voice_identifier.lower().startswith("gtts"):
        if voice_identifier == "gTTS":
            fallback_lang = lang_code or language_key or "en"
            return _gtts_fallback(fallback_lang)
        return voice_identifier

    resolved = _resolve_macos_voice_name(voice_identifier, lang_code)
    if resolved:
        return resolved

    if " - " in voice_identifier:
        primary_name = voice_identifier.split(" - ", 1)[0].strip()
        if primary_name:
            return primary_name

    return voice_identifier


__all__ = [
    "AUTO_MACOS_VOICE",
    "AUTO_MACOS_VOICE_FEMALE",
    "AUTO_MACOS_VOICE_MALE",
    "SILENCE_DURATION_MS",
    "active_tmp_dir",
    "generate_audio",
    "get_voice_display_name",
    "macos_voice_inventory",
    "select_voice",
    "silence_audio_path",
]
