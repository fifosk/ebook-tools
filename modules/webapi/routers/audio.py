"""Audio synthesis HTTP routes."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from gtts import gTTS
from starlette.background import BackgroundTask

from modules import config_manager as cfg
from modules.audio.tts import select_voice
from modules.webapi.audio_utils import resolve_language, resolve_speed, resolve_voice
from modules.webapi.schemas import AudioSynthesisRequest


router = APIRouter(prefix="/api/audio", tags=["audio"])


def _cleanup_file(path: Path) -> None:
    """Remove ``path`` while ignoring missing files."""

    try:
        os.remove(path)
    except FileNotFoundError:  # pragma: no cover - defensive cleanup
        return


def _gtts_identifier(language: str) -> str:
    """Return canonical gTTS identifier for ``language``."""

    normalized = language.strip().lower()
    if not normalized:
        return "gTTS-en"
    short = normalized.replace("_", "-").split("-")[0]
    short = short or "en"
    return f"gTTS-{short}"


def _extract_gtts_language(identifier: str) -> str:
    """Return gTTS language code from ``identifier``."""

    parts = identifier.split("-", 1)
    if len(parts) == 2 and parts[1]:
        return parts[1]
    return "en"


def _analyse_voice_choice(voice: Optional[str]) -> Tuple[str, bool, Optional[str]]:
    """Return ``(preference, force_gtts, explicit_voice)`` for ``voice``."""

    if voice is None:
        return "any", False, None

    normalized = voice.strip()
    lowered = normalized.lower()

    if lowered == "macos-auto-female":
        return "female", False, None
    if lowered == "macos-auto-male":
        return "male", False, None
    if lowered == "macos-auto":
        return "any", False, None
    if lowered.startswith("gtts"):
        return "any", True, None

    return "any", False, normalized


def _voice_name_for_say(identifier: str) -> str:
    """Return the ``say`` voice name for ``identifier``."""

    if " - " in identifier:
        return identifier.split(" - ", 1)[0].strip()
    return identifier.strip()


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


def _resolve_voice(language: str, requested_voice: Optional[str]) -> Tuple[str, str]:
    """Return ``(voice_identifier, engine)`` for the synthesis request."""

    preference, force_gtts, explicit_voice = _analyse_voice_choice(requested_voice)
    selected_voice = select_voice(language, preference)

    if force_gtts:
        selected_voice = _gtts_identifier(language)
        engine = "gtts"
    elif explicit_voice is not None:
        selected_voice = explicit_voice
        engine = "gtts" if selected_voice.lower().startswith("gtts") else "macos"
    else:
        engine = "gtts" if selected_voice.startswith("gTTS-") else "macos"

    return selected_voice, engine


@router.post("", response_class=FileResponse)
def synthesize_audio(payload: AudioSynthesisRequest):  # noqa: D401 - FastAPI signature
    """Generate synthesized speech for the supplied ``payload``."""

    config = cfg.load_configuration(verbose=False)
    text = payload.text.strip()
    language = resolve_language(payload.language, config)
    requested_voice = resolve_voice(payload.voice, config)
    speed = resolve_speed(payload.speed, config)

    selected_voice, engine = _resolve_voice(language, requested_voice)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
        mp3_path = Path(handle.name)

    try:
        if engine == "macos":
            _synthesize_with_say(text, selected_voice, speed, mp3_path)
        else:
            _synthesize_with_gtts(text, selected_voice, mp3_path)
    except HTTPException:
        _cleanup_file(mp3_path)
        raise
    except Exception as exc:  # pragma: no cover - defensive fallback
        _cleanup_file(mp3_path)
        raise HTTPException(status_code=500, detail="Audio synthesis failed") from exc

    background = BackgroundTask(_cleanup_file, mp3_path)
    return FileResponse(
        path=mp3_path,
        media_type="audio/mpeg",
        filename="synthesis.mp3",
        background=background,
    )


__all__ = ["router", "synthesize_audio"]
