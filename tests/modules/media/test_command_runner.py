import subprocess
import sys

import pytest

import modules.media.command_runner as command_runner_mod
from modules.media.command_runner import run_command
from modules.media.exceptions import CommandExecutionError


def test_run_command_success_captures_output():
    result = run_command([sys.executable, "-c", "print('ok')"])
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"


def test_run_command_raises_on_non_zero_exit():
    with pytest.raises(CommandExecutionError) as excinfo:
        run_command([sys.executable, "-c", "import sys; sys.exit(2)"])
    assert excinfo.value.returncode == 2
    assert "Command execution failed" in str(excinfo.value)


def test_run_command_timeout():
    with pytest.raises(CommandExecutionError) as excinfo:
        run_command(
            [sys.executable, "-c", "import time; time.sleep(0.2)"], timeout=0.05
        )
    assert excinfo.value.timeout is True


def test_run_command_retries_failures(monkeypatch):
    attempts = {"count": 0}

    def fake_run(command, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 2:
            return subprocess.CompletedProcess(command, 1, stdout="fail", stderr="err")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(command_runner_mod.subprocess, "run", fake_run)

    result = run_command(["dummy"], retries=1)
    assert attempts["count"] == 2
    assert result.stdout == "ok"


def test_run_command_propagates_after_retry_exhaustion(monkeypatch):
    def always_fail(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    monkeypatch.setattr(command_runner_mod.subprocess, "run", always_fail)

    with pytest.raises(CommandExecutionError):
        run_command(["dummy"], retries=1)


def test_run_command_respects_text_mode():
    result = run_command(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'bin')"],
        text=False,
    )
    assert isinstance(result.stdout, (bytes, bytearray))
    assert result.stdout == b"bin"


def test_run_command_maps_file_not_found():
    with pytest.raises(CommandExecutionError) as excinfo:
        run_command(["__definitely_missing_executable__"])
    assert isinstance(excinfo.value, CommandExecutionError)
    assert excinfo.value.cause is not None
