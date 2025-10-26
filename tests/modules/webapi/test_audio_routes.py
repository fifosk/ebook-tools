"""Integration tests covering the `/api/audio` endpoint."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Dict, Iterable, Tuple

import pytest
from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.routers import audio as audio_router


_SELECT_VOICE_MAP: Dict[Tuple[str, str], str] = {
    ("ar", "any"): "gTTS-ar",
    ("en", "any"): "gTTS-en",
    ("en", "female"): "Ava - en_US - (Enhanced) - Female",
    ("en", "male"): "Alex - en_US - (Enhanced) - Male",
    ("es", "any"): "gTTS-es",
    ("es", "female"): "Carla - es_MX - (Enhanced) - Female",
    ("es", "male"): "Miguel - es_ES - (Enhanced) - Male",
    ("ja", "any"): "gTTS-ja",
    ("ja", "female"): "Kyoko - ja_JP - (Premium) - Female",
    ("ja", "male"): "Ichiro - ja_JP - (Premium) - Male",
}

_BRUNO_CASES = [
    {
        "name": "arabic-default",
        "payload": {"text": "مرحبا بالعالم!", "language": "ar"},
        "preference": "any",
        "force_gtts": False,
    },
    {
        "name": "gtts-english",
        "payload": {
            "text": "Hello world, welcome to ebook-tools!",
            "language": "en",
            "voice": "gTTS",
        },
        "preference": "any",
        "force_gtts": True,
    },
    {
        "name": "gtts-spanish",
        "payload": {
            "text": "Hola mundo, bienvenidos a ebook-tools!",
            "language": "es",
            "voice": "gTTS",
        },
        "preference": "any",
        "force_gtts": True,
    },
    {
        "name": "gtts-japanese",
        "payload": {
            "text": "こんにちは、ebook-toolsへようこそ！",
            "language": "ja",
            "voice": "gTTS",
        },
        "preference": "any",
        "force_gtts": True,
    },
    {
        "name": "macos-female-english",
        "payload": {
            "text": "Hello world, welcome to ebook-tools!",
            "language": "en",
            "voice": "macOS-auto-female",
        },
        "preference": "female",
        "force_gtts": False,
    },
    {
        "name": "macos-female-spanish",
        "payload": {
            "text": "Hola mundo, bienvenidos a ebook-tools!",
            "language": "es",
            "voice": "macOS-auto-female",
        },
        "preference": "female",
        "force_gtts": False,
    },
    {
        "name": "macos-female-japanese",
        "payload": {
            "text": "こんにちは、ebook-toolsへようこそ！",
            "language": "ja",
            "voice": "macOS-auto-female",
        },
        "preference": "female",
        "force_gtts": False,
    },
    {
        "name": "macos-male-english",
        "payload": {
            "text": "Hello world, welcome to ebook-tools!",
            "language": "en",
            "voice": "macOS-auto-male",
        },
        "preference": "male",
        "force_gtts": False,
    },
    {
        "name": "macos-male-spanish",
        "payload": {
            "text": "Hola mundo, bienvenidos a ebook-tools!",
            "language": "es",
            "voice": "macOS-auto-male",
        },
        "preference": "male",
        "force_gtts": False,
    },
    {
        "name": "macos-male-japanese",
        "payload": {
            "text": "こんにちは、ebook-toolsへようこそ！",
            "language": "ja",
            "voice": "macOS-auto-male",
        },
        "preference": "male",
        "force_gtts": False,
    },
]


def _fake_select_voice(language: str, preference: str) -> str:
    key = (language, preference)
    if key not in _SELECT_VOICE_MAP:
        raise AssertionError(f"Unexpected select_voice call for {key}")
    return _SELECT_VOICE_MAP[key]


def _build_gtts_bytes(language: str, text: str) -> bytes:
    return f"GTTS:{language}:{len(text)}".encode("utf-8")


def _build_aiff_bytes(voice: str, text: str) -> bytes:
    return f"AIFF:{voice}:{len(text)}".encode("utf-8")


def _build_mp3_bytes(source: bytes) -> bytes:
    return b"MP3:" + source


def _voice_name(identifier: str) -> str:
    if " - " in identifier:
        return identifier.split(" - ", 1)[0].strip()
    return identifier.strip()


def _fake_run(cmd: Iterable[str], *args, **kwargs) -> CompletedProcess:
    command = list(cmd)
    if not command:
        raise AssertionError("Empty command passed to subprocess.run")

    if command[0] == "say":
        try:
            output_index = command.index("-o") + 1
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise AssertionError("say command missing output flag") from exc
        destination = Path(command[output_index])
        voice = command[2]
        text = command[-1]
        destination.write_bytes(_build_aiff_bytes(voice, text))
        return CompletedProcess(command, 0)

    if command[0] == "ffmpeg":
        try:
            input_index = command.index("-i") + 1
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise AssertionError("ffmpeg command missing input flag") from exc
        input_path = Path(command[input_index])
        output_path = Path(command[-1])
        output_path.write_bytes(_build_mp3_bytes(input_path.read_bytes()))
        return CompletedProcess(command, 0)

    raise AssertionError(f"Unexpected command: {' '.join(command)}")


class _StubGTTS:
    def __init__(self, *, text: str, lang: str) -> None:
        self.text = text
        self.lang = lang

    def save(self, filename: str) -> None:
        Path(filename).write_bytes(_build_gtts_bytes(self.lang, self.text))


@pytest.fixture()
def audio_client(monkeypatch) -> Iterable[TestClient]:
    monkeypatch.setattr(
        "modules.webapi.routers.audio.cfg.load_configuration",
        lambda verbose=False: {"selected_voice": "macOS-auto", "macos_reading_speed": 180},
    )
    monkeypatch.setattr("modules.webapi.routers.audio.select_voice", _fake_select_voice)
    monkeypatch.setattr("modules.webapi.routers.audio.subprocess.run", _fake_run)
    monkeypatch.setattr("modules.webapi.routers.audio.gTTS", _StubGTTS)

    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("case", _BRUNO_CASES, ids=lambda case: case["name"])
def test_bruno_cases_return_mp3(audio_client: TestClient, case: Dict[str, object]) -> None:
    payload = case["payload"]
    response = audio_client.post("/api/audio", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")

    language = payload["language"]
    text = payload["text"]
    preference = case["preference"]

    if case["force_gtts"]:
        identifier = audio_router._gtts_identifier(language)
    else:
        identifier = _SELECT_VOICE_MAP[(language, preference)]

    if identifier.startswith("gTTS-"):
        expected = _build_gtts_bytes(
            audio_router._extract_gtts_language(identifier),
            text,
        )
    else:
        voice_name = _voice_name(identifier)
        expected = _build_mp3_bytes(_build_aiff_bytes(voice_name, text))

    assert response.content == expected
    assert int(response.headers.get("content-length", 0)) == len(expected)


def test_list_voices_returns_cached_inventory(audio_client: TestClient, monkeypatch) -> None:
    macos_voices = [
        {"name": "Alex", "lang": "en_US", "quality": "Enhanced"},
        {"name": "Sofia", "lang": "es_ES", "quality": None},
    ]
    gtts_languages = (
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
    )

    monkeypatch.setattr(audio_router, "get_say_voices", lambda: macos_voices)
    monkeypatch.setattr(audio_router, "_GTTS_LANGUAGES", gtts_languages)

    response = audio_client.get("/api/audio/voices")

    assert response.status_code == 200
    payload = response.json()
    assert payload["macos"] == macos_voices
    assert payload["gtts"] == list(gtts_languages)


def test_match_requires_language(audio_client: TestClient) -> None:
    response = audio_client.get("/api/audio/match", params={"preference": "any"})

    assert response.status_code == 422


def test_match_returns_macos_voice(audio_client: TestClient) -> None:
    response = audio_client.get(
        "/api/audio/match",
        params={"language": "en", "preference": "male"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "engine": "macos",
        "voice": _SELECT_VOICE_MAP[("en", "male")],
    }


def test_match_returns_gtts_voice(audio_client: TestClient) -> None:
    response = audio_client.get(
        "/api/audio/match",
        params={"language": "es", "preference": "any"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "engine": "gtts",
        "voice": _SELECT_VOICE_MAP[("es", "any")],
    }
