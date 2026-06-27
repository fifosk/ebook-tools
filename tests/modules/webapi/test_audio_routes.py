"""Integration tests covering the `/api/audio` endpoint."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Dict, Iterable, Tuple

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from modules.webapi.application import create_app
from modules.webapi.routers import audio as audio_router

pytestmark = pytest.mark.webapi


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

_MACOS_INVENTORY: Tuple[Tuple[str, str, str, str], ...] = (
    ("Ava", "en_US", "Enhanced", "female"),
    ("Alex", "en_US", "Enhanced", "male"),
    ("Carla", "es_MX", "Enhanced", "female"),
    ("Miguel", "es_ES", "Enhanced", "male"),
    ("Kyoko", "ja_JP", "Premium", "female"),
    ("Ichiro", "ja_JP", "Premium", "male"),
)

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


def _expected_metadata(identifier: str) -> Dict[str, str]:
    name = _voice_name(identifier)
    for voice_name, locale, quality, gender in _MACOS_INVENTORY:
        if voice_name == name:
            return {
                "name": voice_name,
                "lang": locale,
                "quality": quality,
                "gender": gender.capitalize(),
            }
    raise AssertionError(f"No metadata for identifier {identifier}")


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


class _ListLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def info(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)

    def error(self, message: str, *args, **kwargs) -> None:
        self.messages.append(message % args if args else message)


class _FailingPiperBackend:
    def synthesize(self, **_kwargs):
        raise RuntimeError(
            "piper model failed at /Volumes/Data/private/piper.onnx with api_key=secret"
        )


@pytest.fixture()
def audio_client(monkeypatch) -> Iterable[TestClient]:
    monkeypatch.setattr(
        "modules.webapi.routers.audio.cfg.load_configuration",
        lambda verbose=False: {"selected_voice": "macOS-auto", "macos_reading_speed": 180},
    )
    monkeypatch.setattr("modules.webapi.routers.audio.select_voice", _fake_select_voice)
    monkeypatch.setattr("modules.webapi.routers.audio.subprocess.run", _fake_run)
    monkeypatch.setattr("modules.webapi.routers.audio.gTTS", _StubGTTS)
    monkeypatch.setattr(
        "modules.webapi.routers.audio.macos_voice_inventory",
        lambda: list(_MACOS_INVENTORY),
    )
    monkeypatch.setattr("modules.webapi.routers.audio.log_mgr.console_info", lambda *_, **__: None)

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

    # The voice resolution priority changed: gTTS is now preferred over macOS
    # for auto-selection. macOS-auto-female/male resolve to gTTS when the
    # language is supported by gTTS.
    identifier = response.headers["x-selected-voice"]
    engine = response.headers["x-synthesis-engine"]

    if case["force_gtts"] or engine == "gtts":
        expected_identifier = audio_router._gtts_identifier(language)
        assert identifier == expected_identifier
        assert engine == "gtts"
        expected = _build_gtts_bytes(
            audio_router._extract_gtts_language(identifier),
            text,
        )
        assert "x-macos-voice-name" not in response.headers
    else:
        assert identifier == _SELECT_VOICE_MAP[(language, preference)]
        assert engine == "macos"
        voice_name = _voice_name(identifier)
        expected = _build_mp3_bytes(_build_aiff_bytes(voice_name, text))
        metadata = _expected_metadata(identifier)
        assert response.headers["x-macos-voice-name"] == metadata["name"]
        assert response.headers["x-macos-voice-lang"] == metadata["lang"]
        assert response.headers["x-macos-voice-quality"] == metadata["quality"]
        assert response.headers["x-macos-voice-gender"] == metadata["gender"]

    assert response.content == expected
    assert int(response.headers.get("content-length", 0)) == len(expected)


def test_list_voices_returns_cached_inventory(audio_client: TestClient, monkeypatch) -> None:
    macos_voices = [
        {"name": "Alex", "lang": "en_US", "quality": "Enhanced", "gender": "Male"},
        {"name": "Sofia", "lang": "es_ES", "quality": None, "gender": None},
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


def test_list_voices_records_token_safe_telemetry(
    audio_client: TestClient,
    monkeypatch,
) -> None:
    logger = _ListLogger()
    macos_voices = [
        {"name": "SecretVoice", "lang": "en_US", "quality": "Enhanced", "gender": "Male"},
    ]
    gtts_languages = (
        {"code": "en", "name": "English"},
        {"code": "ja", "name": "Japanese"},
    )
    piper_voices = [
        {"name": "private-piper-model", "lang": "en_US", "quality": "medium"},
    ]

    monkeypatch.setattr(audio_router, "logger", logger)
    monkeypatch.setattr(audio_router, "get_say_voices", lambda: macos_voices)
    monkeypatch.setattr(audio_router, "_GTTS_LANGUAGES", gtts_languages)
    monkeypatch.setattr(audio_router, "_load_piper_voices", lambda: piper_voices)

    response = audio_client.get("/api/audio/voices")
    metrics_response = audio_client.get("/metrics")

    assert response.status_code == 200
    rendered_logs = "\n".join(logger.messages)
    assert "Audio route operation=voices result=success" in rendered_logs
    assert "macos=1" in rendered_logs
    assert "gtts=2" in rendered_logs
    assert "piper=1" in rendered_logs
    assert "SecretVoice" not in rendered_logs
    assert "private-piper-model" not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_audio_route_duration_seconds_count{operation="voices",result="success"}'
        in metrics_response.text
    )


def test_list_voices_failure_uses_generic_detail_and_token_safe_telemetry(
    audio_client: TestClient,
    monkeypatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(audio_router, "logger", logger)

    def fake_get_say_voices():
        raise RuntimeError("say inventory failed at /Volumes/Data/private/voices.plist")

    monkeypatch.setattr(audio_router, "get_say_voices", fake_get_say_voices)

    response = audio_client.get("/api/audio/voices")
    metrics_response = audio_client.get("/metrics")

    assert response.status_code == 503
    assert response.json() == {"detail": "Unable to load audio voice inventory."}
    rendered_logs = "\n".join(logger.messages)
    assert "Audio route operation=voices result=error" in rendered_logs
    assert "say inventory failed" not in rendered_logs
    assert "/Volumes/Data/private/voices.plist" not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_audio_route_duration_seconds_count{operation="voices",result="error"}'
        in metrics_response.text
    )


def test_piper_synthesis_failure_uses_generic_detail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "modules.audio.backends.piper.PiperTTSBackend",
        lambda: _FailingPiperBackend(),
    )

    with pytest.raises(HTTPException) as exc_info:
        audio_router._synthesize_with_piper(
            text="Hello",
            voice_identifier="en_US-private-medium",
            language="en",
            speed=180,
            destination=tmp_path / "preview.mp3",
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Piper synthesis failed"
    assert "/Volumes/Data" not in str(exc_info.value.detail)
    assert "api_key" not in str(exc_info.value.detail)
    assert "private" not in str(exc_info.value.detail)


def test_match_requires_language(audio_client: TestClient) -> None:
    response = audio_client.get("/api/audio/match", params={"preference": "any"})

    assert response.status_code == 422


def test_match_returns_macos_voice(audio_client: TestClient) -> None:
    response = audio_client.get(
        "/api/audio/match",
        params={"language": "en", "preference": "male"},
    )

    assert response.status_code == 200
    expected_voice = _SELECT_VOICE_MAP[("en", "male")]
    assert response.json() == {
        "engine": "macos",
        "voice": expected_voice,
        "macos_voice": _expected_metadata(expected_voice),
        "piper_voice": None,
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
        "macos_voice": None,
        "piper_voice": None,
    }


def test_match_records_token_safe_telemetry(
    audio_client: TestClient,
    monkeypatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(audio_router, "logger", logger)

    response = audio_client.get(
        "/api/audio/match",
        params={"language": "en", "preference": "male"},
    )
    metrics_response = audio_client.get("/metrics")

    assert response.status_code == 200
    rendered_logs = "\n".join(logger.messages)
    assert "Audio route operation=match result=success" in rendered_logs
    assert "engine=macos" in rendered_logs
    assert "Alex" not in rendered_logs
    assert "language=" not in rendered_logs
    assert "preference=" not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_audio_route_duration_seconds_count{operation="match",result="success"}'
        in metrics_response.text
    )


def test_match_failure_uses_generic_detail_and_token_safe_telemetry(
    audio_client: TestClient,
    monkeypatch,
) -> None:
    logger = _ListLogger()
    monkeypatch.setattr(audio_router, "logger", logger)

    def fake_select_voice(language: str, preference: str) -> str:
        raise RuntimeError(
            f"voice match failed for {language}/{preference} using secret-model"
        )

    monkeypatch.setattr(audio_router, "select_voice", fake_select_voice)

    response = audio_client.get(
        "/api/audio/match",
        params={"language": "de", "preference": "female"},
    )
    metrics_response = audio_client.get("/metrics")

    assert response.status_code == 503
    assert response.json() == {"detail": "Unable to match audio voice."}
    rendered_logs = "\n".join(logger.messages)
    assert "Audio route operation=match result=error" in rendered_logs
    assert "voice match failed" not in rendered_logs
    assert "secret-model" not in rendered_logs
    assert "de/female" not in rendered_logs
    assert "language=" not in rendered_logs
    assert "preference=" not in rendered_logs
    assert metrics_response.status_code == 200
    assert (
        'ebook_tools_audio_route_duration_seconds_count{operation="match",result="error"}'
        in metrics_response.text
    )
