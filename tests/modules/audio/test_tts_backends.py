import types

import pytest
from pydub import AudioSegment

from modules.audio.backends import GTTSBackend, MacOSTTSBackend, TTSBackendError, get_tts_backend
from modules.media.exceptions import CommandExecutionError


def test_get_tts_backend_prefers_config_override():
    backend = get_tts_backend({"tts_backend": "gtts"})
    assert isinstance(backend, GTTSBackend)


def test_get_tts_backend_auto_uses_platform_default(monkeypatch):
    monkeypatch.setattr("modules.audio.backends.sys.platform", "darwin")

    settings = types.SimpleNamespace(tts_backend="auto", tts_executable_path=None)
    monkeypatch.setattr("modules.audio.backends.cfg.get_settings", lambda: settings)

    backend = get_tts_backend()
    assert isinstance(backend, MacOSTTSBackend)


def test_get_tts_backend_respects_executable_override():
    backend = get_tts_backend(
        {"tts_backend": "macos", "tts_executable_path": "/custom/say"}
    )
    assert isinstance(backend, MacOSTTSBackend)
    assert backend.executable_path == "/custom/say"


def test_get_tts_backend_accepts_new_backend_name():
    backend = get_tts_backend({"tts_backend": "macos_say"})
    assert isinstance(backend, MacOSTTSBackend)


def test_get_tts_backend_defaults_when_unset(monkeypatch):
    monkeypatch.setattr("modules.audio.backends.sys.platform", "linux")

    settings = types.SimpleNamespace(tts_backend=None, tts_executable_path=None)
    monkeypatch.setattr("modules.audio.backends.cfg.get_settings", lambda: settings)

    backend = get_tts_backend({})
    assert isinstance(backend, GTTSBackend)


def test_macos_backend_invokes_command_with_expected_arguments(monkeypatch, tmp_path):
    invoked_commands: list[list[str]] = []

    def fake_run_command(command, **kwargs):
        invoked_commands.append(list(command))
        assert kwargs.get("check", True) is True

    dummy_audio = AudioSegment.silent(duration=100)

    def fake_from_file(path, format):
        assert format == "aiff"
        return dummy_audio

    monkeypatch.setattr("modules.audio.backends.macos.run_command", fake_run_command)
    monkeypatch.setattr(
        "modules.audio.backends.macos.AudioSegment.from_file", fake_from_file
    )

    backend = MacOSTTSBackend(executable_path="/usr/bin/say")
    output_file = tmp_path / "output.aiff"

    result = backend.synthesize(
        text="Hello world",
        voice="Samantha",
        speed=180,
        lang_code="en",
        output_path=str(output_file),
    )

    assert invoked_commands == [
        ["/usr/bin/say", "-v", "Samantha", "-r", "180", "-o", str(output_file), "Hello world"]
    ]
    assert result == dummy_audio


def test_macos_backend_wraps_command_errors(monkeypatch, tmp_path):
    def failing_run_command(command, **kwargs):
        raise CommandExecutionError(command, returncode=1)

    monkeypatch.setattr("modules.audio.backends.macos.run_command", failing_run_command)
    dummy_audio = AudioSegment.silent(duration=100)
    monkeypatch.setattr(
        "modules.audio.backends.macos.AudioSegment.from_file",
        lambda path, format: dummy_audio,
    )

    backend = MacOSTTSBackend(executable_path="/usr/bin/say")

    with pytest.raises(TTSBackendError):
        backend.synthesize(
            text="Hello world",
            voice="Samantha",
            speed=180,
            lang_code="en",
            output_path=str(tmp_path / "output.aiff"),
        )

