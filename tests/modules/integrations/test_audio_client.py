"""Tests for the audio API HTTP client."""

from __future__ import annotations

import logging
from typing import Any, Dict

from pydub import AudioSegment

from modules.integrations.audio_client import AudioAPIClient


class _FakeResponse:
    def __init__(self, *, headers: Dict[str, Any]):
        self.status_code = 200
        self.content = b"fake-binary"
        self.headers = headers
        self.text = ""


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.calls: list[Dict[str, Any]] = []

    def post(self, url: str, json: Dict[str, Any], headers: Dict[str, str], timeout: float):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return self._response


def test_audio_client_logs_voice_attributes(monkeypatch, caplog):
    headers = {
        "X-Selected-Voice": "Amy",
        "X-Synthesis-Engine": "macos",
        "X-MacOS-Voice-Name": "Amy",
        "X-MacOS-Voice-Lang": "en-US",
        "X-MacOS-Voice-Quality": "Premium",
        "X-MacOS-Voice-Gender": "female",
    }
    response = _FakeResponse(headers=headers)
    session = _FakeSession(response)

    monkeypatch.setattr(
        "modules.integrations.audio_client.AudioSegment.from_file",
        lambda *_args, **_kwargs: AudioSegment.silent(duration=10),
    )

    client = AudioAPIClient("https://audio.example", session=session)

    caplog.set_level(logging.INFO, logger="ebook_tools.integrations.audio")

    segment = client.synthesize(text="hello", voice="Amy", language="en", return_metadata=False)

    assert isinstance(segment, AudioSegment)
    assert session.calls, "Expected the fake session to be invoked"

    success_record = next(
        record
        for record in caplog.records
        if getattr(record, "event", "") == "integrations.audio.success"
    )
    attributes = success_record.attributes

    assert attributes["resolved_voice"] == "Amy"
    assert attributes["voice_name"] == "Amy"
    assert attributes["voice_engine"] == "macos"
    assert attributes["voice_language"] == "en-US"
    assert attributes["voice_quality"] == "Premium"
    assert attributes["voice_gender"] == "female"
