"""Audio synthesis HTTP routes."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from gtts import gTTS
from gtts.lang import tts_langs
from starlette.background import BackgroundTask

from modules import config_manager as cfg
from modules import logging_manager as log_mgr
from modules.audio.tts import macos_voice_inventory, normalize_gtts_language_code, select_voice
from modules.webapi.audio_utils import resolve_language, resolve_speed, resolve_voice
from modules.webapi.audio import get_say_voices
from modules.webapi.schemas import (
    AudioSynthesisRequest,
    GTTSLanguage,
    MacOSVoice,
    PiperVoice,
    VoiceInventoryResponse,
    VoiceMatchResponse,
)


router = APIRouter(prefix="/api/audio", tags=["audio"])
logger = log_mgr.logger


def _cleanup_file(path: Path) -> None:
    """Remove ``path`` while ignoring missing files."""

    try:
        os.remove(path)
    except FileNotFoundError:  # pragma: no cover - defensive cleanup
        return


def _gtts_identifier(language: str) -> str:
    """Return canonical gTTS identifier for ``language``."""

    normalized = normalize_gtts_language_code(language)
    short = normalized.split("-")[0] or "en"
    return f"gTTS-{short}"


def _extract_gtts_language(identifier: str) -> str:
    """Return gTTS language code from ``identifier``."""

    parts = identifier.split("-", 1)
    if len(parts) == 2 and parts[1]:
        return normalize_gtts_language_code(parts[1])
    return "en"


def _analyse_voice_choice(voice: Optional[str]) -> Tuple[str, bool, bool, Optional[str]]:
    """Return ``(preference, force_gtts, force_piper, explicit_voice)`` for ``voice``."""

    if voice is None:
        return "any", False, False, None

    normalized = voice.strip()
    lowered = normalized.lower()

    if lowered == "macos-auto-female":
        return "female", False, False, None
    if lowered == "macos-auto-male":
        return "male", False, False, None
    if lowered == "macos-auto":
        return "any", False, False, None
    if lowered.startswith("gtts"):
        return "any", True, False, None
    if lowered in ("piper-auto", "piper-auto-male", "piper-auto-female"):
        return "any", False, True, None

    return "any", False, False, normalized


def _voice_name_for_say(identifier: str) -> str:
    """Return the ``say`` voice name for ``identifier``."""

    if " - " in identifier:
        return identifier.split(" - ", 1)[0].strip()
    return identifier.strip()


def _normalize_locale_for_compare(locale: str) -> str:
    return locale.replace("_", "-").lower()


def _parse_voice_identifier(identifier: str) -> Tuple[str, Optional[str]]:
    parts = [segment.strip() for segment in identifier.split(" - ") if segment.strip()]
    if not parts:
        return identifier.strip(), None

    name = parts[0]
    locale: Optional[str] = None
    for segment in parts[1:]:
        lowered = segment.lower()
        if lowered in {"male", "female", "unknown"}:
            continue
        if segment.startswith("(") and segment.endswith(")"):
            continue
        locale = segment
        break
    return name, locale


def _lookup_macos_voice_details(identifier: str) -> Optional[Dict[str, Optional[str]]]:
    name, locale = _parse_voice_identifier(identifier)
    if not name:
        return None

    voices = macos_voice_inventory()
    target_locale = _normalize_locale_for_compare(locale) if locale else None

    for voice_name, voice_locale, quality, gender in voices:
        if voice_name.lower() != name.lower():
            continue
        if target_locale and _normalize_locale_for_compare(voice_locale) != target_locale:
            continue
        return {
            "name": voice_name,
            "lang": voice_locale,
            "quality": quality or None,
            "gender": gender.capitalize() if gender else None,
        }
    return None


def _synthesize_with_say(text: str, voice_identifier: str, speed: int, destination: Path) -> None:
    """Generate MP3 bytes using the macOS ``say`` command and ``ffmpeg``."""

    voice_name = _voice_name_for_say(voice_identifier)
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as handle:
        aiff_path = Path(handle.name)

    try:
        subprocess.run(
            [
                "say",
                "-v",
                voice_name,
                "-r",
                str(speed),
                "-o",
                str(aiff_path),
                text,
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(aiff_path),
                str(destination),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="macOS synthesis failed") from exc
    finally:
        try:
            os.remove(aiff_path)
        except FileNotFoundError:
            pass


def _synthesize_with_gtts(text: str, voice_identifier: str, destination: Path) -> None:
    """Generate MP3 bytes using gTTS for ``voice_identifier``."""

    language = _extract_gtts_language(voice_identifier)
    try:
        gTTS(text=text, lang=language).save(str(destination))
    except Exception as exc:  # pragma: no cover - network/library failure
        raise HTTPException(status_code=500, detail="gTTS synthesis failed") from exc


def _synthesize_with_piper(
    text: str, voice_identifier: str, language: str, speed: int, destination: Path
) -> None:
    """Generate MP3 using Piper TTS for ``voice_identifier``."""
    try:
        from modules.audio.backends.piper import PiperTTSBackend

        backend = PiperTTSBackend()
        audio = backend.synthesize(
            text=text,
            voice=voice_identifier,
            speed=speed,
            lang_code=language,
        )
        # Export as MP3
        audio.export(str(destination), format="mp3")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Piper synthesis failed: {exc}") from exc


def _is_piper_voice(voice: str) -> bool:
    """Check if the voice identifier is a Piper voice."""
    if not voice:
        return False
    lowered = voice.lower()
    # Piper auto selection
    if lowered in ("piper-auto", "piper"):
        return True
    # Explicit Piper model name format: lang_REGION-name-quality
    # e.g., en_US-lessac-medium, ar_JO-kareem-medium
    if "_" in voice and "-" in voice:
        parts = voice.split("-")
        if len(parts) >= 2 and "_" in parts[0]:
            return True
    return False


def _resolve_piper_auto_voice(language: str) -> Optional[str]:
    """Return Piper voice for language if available, preferring highest quality male voice."""
    try:
        from modules.audio.backends.piper import get_voice_for_language

        voice = get_voice_for_language(language)
        return voice
    except Exception:
        return None


def _resolve_voice(language: str, requested_voice: Optional[str]) -> Tuple[str, str]:
    """Return ``(voice_identifier, engine)`` for the synthesis request.

    Priority order for auto-selection:
      1. gTTS auto (for the token's language)
      2. Piper auto (fallback, prefer highest quality male voice)
      3. macOS auto (final fallback)
    """

    # Check for explicit Piper voice first (but not piper-auto keywords)
    if requested_voice and _is_piper_voice(requested_voice):
        lowered = requested_voice.lower()
        # Handle piper-auto explicitly to resolve the actual voice name
        if lowered in ("piper-auto", "piper", "piper-auto-male", "piper-auto-female"):
            piper_voice = _resolve_piper_auto_voice(language)
            if piper_voice:
                return piper_voice, "piper"
            # Fallback to gTTS if Piper not available
            return _gtts_identifier(language), "gtts"
        # It's an explicit Piper model name, use it directly
        return requested_voice, "piper"

    preference, force_gtts, force_piper, explicit_voice = _analyse_voice_choice(requested_voice)

    # Handle explicit voice request
    if explicit_voice is not None:
        if _is_piper_voice(explicit_voice):
            return explicit_voice, "piper"
        elif explicit_voice.lower().startswith("gtts"):
            return explicit_voice, "gtts"
        else:
            return explicit_voice, "macos"

    # Handle forced gTTS
    if force_gtts:
        return _gtts_identifier(language), "gtts"

    # Handle forced Piper auto (e.g., "piper-auto", "piper-auto-male")
    if force_piper:
        piper_voice = _resolve_piper_auto_voice(language)
        if piper_voice:
            return piper_voice, "piper"
        # Fallback to gTTS if Piper not available for this language
        return _gtts_identifier(language), "gtts"

    # Auto-selection priority: gTTS -> Piper -> macOS
    # First try gTTS (most widely available)
    gtts_voice = _gtts_identifier(language)

    # Check if gTTS supports this language
    try:
        from gtts.lang import tts_langs

        available_langs = tts_langs()
        lang_short = language.lower().split("-")[0].split("_")[0]
        gtts_supported = lang_short in available_langs or language.lower() in available_langs
    except Exception:
        gtts_supported = True  # Assume supported if can't check

    if gtts_supported:
        return gtts_voice, "gtts"

    # Try Piper auto next
    piper_voice = _resolve_piper_auto_voice(language)
    if piper_voice:
        return piper_voice, "piper"

    # Final fallback: macOS voice selection
    selected_voice = select_voice(language, preference)
    if selected_voice.startswith("gTTS-"):
        return selected_voice, "gtts"
    return selected_voice, "macos"


def _load_gtts_languages() -> Tuple[Dict[str, str], ...]:
    """Return a cached tuple of available gTTS language entries."""

    try:
        languages = tts_langs()
    except Exception:  # pragma: no cover - defensive fallback
        languages = {}

    entries = tuple(
        {"code": code, "name": name}
        for code, name in sorted(languages.items(), key=lambda item: item[0])
    )
    return entries


_GTTS_LANGUAGES: Tuple[Dict[str, str], ...] = _load_gtts_languages()


def _load_piper_voices() -> list[Dict[str, str]]:
    """Return list of installed Piper voice models."""
    try:
        from modules.audio.backends.piper import PiperTTSBackend

        backend = PiperTTSBackend()
        voices = backend.list_available_voices()
        return [
            {"name": name, "lang": lang, "quality": quality}
            for name, lang, quality in voices
        ]
    except Exception:  # pragma: no cover - Piper may not be installed
        return []


@router.get("/voices", response_model=VoiceInventoryResponse)
def list_available_voices() -> VoiceInventoryResponse:  # noqa: D401 - FastAPI signature
    """Return cached macOS ``say`` voices, gTTS language entries, and Piper voices."""

    macos_voices = [MacOSVoice.model_validate(voice) for voice in get_say_voices()]
    gtts_languages = [GTTSLanguage.model_validate(entry) for entry in _GTTS_LANGUAGES]
    piper_voices = [PiperVoice.model_validate(voice) for voice in _load_piper_voices()]
    return VoiceInventoryResponse(macos=macos_voices, gtts=gtts_languages, piper=piper_voices)


@router.get("/match", response_model=VoiceMatchResponse)
def match_voice(
    language: str = Query(..., min_length=1, description="Language code to match"),
    preference: str = Query(
        "any",
        min_length=1,
        description="Voice preference (any, male, or female)",
    ),
) -> VoiceMatchResponse:
    """Return the identifier produced by :func:`modules.audio.tts.select_voice`."""

    voice = select_voice(language, preference)
    engine = "gtts" if voice.lower().startswith("gtts") else "macos"
    metadata = _lookup_macos_voice_details(voice) if engine == "macos" else None
    return VoiceMatchResponse(voice=voice, engine=engine, macos_voice=metadata)


@router.post("", response_class=FileResponse)
def synthesize_audio(payload: AudioSynthesisRequest):  # noqa: D401 - FastAPI signature
    """Generate synthesized speech for the supplied ``payload``."""

    config = cfg.load_configuration(verbose=False)
    text = payload.text.strip()
    language = resolve_language(payload.language, config)
    requested_voice = resolve_voice(payload.voice, config)
    speed = resolve_speed(payload.speed, config)

    selected_voice, engine = _resolve_voice(language, requested_voice)
    metadata = _lookup_macos_voice_details(selected_voice) if engine == "macos" else None
    fallback_from: Optional[str] = None

    if engine == "piper":
        log_mgr.console_info(
            "Piper voice selected: %s",
            selected_voice,
            logger_obj=logger,
        )
    elif engine == "macos":
        if metadata:
            log_mgr.console_info(
                "macOS voice selected: %s (%s, %s, %s)",
                metadata["name"],
                metadata["lang"],
                metadata.get("quality") or "Default",
                metadata.get("gender") or "Unknown",
                logger_obj=logger,
            )
        else:
            log_mgr.console_info(
                "macOS voice selected: %s (metadata unavailable)",
                selected_voice,
                logger_obj=logger,
            )
    else:
        log_mgr.console_info(
            "gTTS voice selected: %s",
            selected_voice,
            logger_obj=logger,
        )

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
        mp3_path = Path(handle.name)

    try:
        if engine == "piper":
            try:
                _synthesize_with_piper(text, selected_voice, language, speed, mp3_path)
            except HTTPException:
                fallback_from = "piper"
                selected_voice, engine = _gtts_identifier(language), "gtts"
                metadata = None
                log_mgr.console_warning(
                    "Piper synthesis failed; falling back to gTTS (%s).",
                    selected_voice,
                    logger_obj=logger,
                )
                _synthesize_with_gtts(text, selected_voice, mp3_path)
        elif engine == "macos":
            try:
                _synthesize_with_say(text, selected_voice, speed, mp3_path)
            except HTTPException:
                fallback_from = "macos"
                selected_voice, engine = _gtts_identifier(language), "gtts"
                metadata = None
                log_mgr.console_warning(
                    "macOS synthesis failed; falling back to gTTS (%s).",
                    selected_voice,
                    logger_obj=logger,
                )
                _synthesize_with_gtts(text, selected_voice, mp3_path)
        else:
            _synthesize_with_gtts(text, selected_voice, mp3_path)
    except HTTPException:
        _cleanup_file(mp3_path)
        raise
    except Exception as exc:  # pragma: no cover - defensive fallback
        _cleanup_file(mp3_path)
        raise HTTPException(status_code=500, detail="Audio synthesis failed") from exc

    background = BackgroundTask(_cleanup_file, mp3_path)
    headers = {
        "X-Synthesis-Engine": engine,
        "X-Selected-Voice": selected_voice,
    }
    if fallback_from:
        headers["X-Synthesis-Fallback-From"] = fallback_from
    if metadata:
        headers["X-MacOS-Voice-Name"] = metadata["name"]
        headers["X-MacOS-Voice-Lang"] = metadata["lang"]
        quality = metadata.get("quality")
        gender = metadata.get("gender")
        if quality:
            headers["X-MacOS-Voice-Quality"] = quality
        if gender:
            headers["X-MacOS-Voice-Gender"] = gender

    return FileResponse(
        path=mp3_path,
        media_type="audio/mpeg",
        filename="synthesis.mp3",
        background=background,
        headers=headers,
    )


__all__ = [
    "list_available_voices",
    "match_voice",
    "router",
    "synthesize_audio",
]
