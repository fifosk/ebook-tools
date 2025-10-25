import importlib
import json
import sys
import types
from pathlib import Path

import pytest

from modules.user_management import AuthService, LocalUserStore, SessionManager


def _configure_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    user_store = tmp_path / "users.json"
    session_file = tmp_path / "sessions.json"
    active_file = tmp_path / "active_session"
    monkeypatch.setenv("EBOOKTOOLS_USER_STORE", str(user_store))
    monkeypatch.setenv("EBOOKTOOLS_SESSION_FILE", str(session_file))
    monkeypatch.setenv("EBOOKTOOLS_ACTIVE_SESSION_FILE", str(active_file))
    return user_store, session_file, active_file


@pytest.fixture()
def orchestrator_module(monkeypatch: pytest.MonkeyPatch):
    for name in list(sys.modules):
        if name in {"modules.cli.orchestrator", "modules.cli.pipeline_runner"}:
            sys.modules.pop(name)

    services_pkg = types.ModuleType("modules.services")
    services_pkg.__path__ = []  # type: ignore[attr-defined]
    pipeline_stub = types.ModuleType("modules.services.pipeline_service")

    class _StubPipelineResponse:
        def __init__(self, success: bool = False) -> None:
            self.success = success

    pipeline_stub.PipelineResponse = _StubPipelineResponse
    monkeypatch.setitem(sys.modules, "modules.services", services_pkg)
    monkeypatch.setitem(sys.modules, "modules.services.pipeline_service", pipeline_stub)

    stub = types.ModuleType("modules.cli.pipeline_runner")

    def _placeholder_run_pipeline_from_args(*args, **kwargs):
        raise RuntimeError("pipeline runner should be stubbed in tests")

    stub.run_pipeline_from_args = _placeholder_run_pipeline_from_args
    monkeypatch.setitem(sys.modules, "modules.cli.pipeline_runner", stub)

    progress_stub = types.ModuleType("modules.cli.progress")

    class _StubCLIProgressLogger:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def close(self) -> None:
            return None

    progress_stub.CLIProgressLogger = _StubCLIProgressLogger
    monkeypatch.setitem(sys.modules, "modules.cli.progress", progress_stub)

    from modules.progress_tracker import ProgressTracker

    if not hasattr(ProgressTracker, "close"):
        setattr(ProgressTracker, "close", lambda self: None)

    module = importlib.import_module("modules.cli.orchestrator")
    yield module
    sys.modules.pop("modules.cli.orchestrator", None)
    sys.modules.pop("modules.cli.pipeline_runner", None)
    sys.modules.pop("modules.services.pipeline_service", None)
    sys.modules.pop("modules.services", None)
    sys.modules.pop("modules.cli.progress", None)


def test_user_add_and_list_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, orchestrator_module
):
    _configure_env(monkeypatch, tmp_path)

    exit_code = orchestrator_module.run_cli(
        ["user", "add", "alice", "--password", "wonderland", "--role", "admin"]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Created user 'alice'" in captured.out

    exit_code = orchestrator_module.run_cli(["user", "list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Registered users" in captured.out
    assert "alice" in captured.out
    assert "admin" in captured.out


def test_user_login_and_logout_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, orchestrator_module
):
    _, session_file, active_file = _configure_env(monkeypatch, tmp_path)
    orchestrator_module.run_cli(["user", "add", "bob", "--password", "builder"])
    capsys.readouterr()

    exit_code = orchestrator_module.run_cli(["user", "login", "bob", "--password", "builder"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Login successful for 'bob'." in captured.out
    assert "Token:" in captured.out

    token = active_file.read_text(encoding="utf-8").strip()
    assert token
    sessions = json.loads(session_file.read_text(encoding="utf-8"))
    assert token in sessions.get("sessions", {})

    exit_code = orchestrator_module.run_cli(["user", "logout"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Session logged out successfully." in captured.out
    assert not active_file.exists()
    sessions = json.loads(session_file.read_text(encoding="utf-8"))
    assert token not in sessions.get("sessions", {})


def test_run_requires_active_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, orchestrator_module
):
    _configure_env(monkeypatch, tmp_path)

    exit_code = orchestrator_module.run_cli(["run"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "No active session" in captured.err

    orchestrator_module.run_cli(["user", "add", "carol", "--password", "p@ssw0rd"])
    capsys.readouterr()
    orchestrator_module.run_cli(["user", "login", "carol", "--password", "p@ssw0rd"])
    capsys.readouterr()

    called: dict[str, bool] = {}

    def _fake_run_pipeline(*args, **kwargs):
        called["invoked"] = True
        return type("_DummyResponse", (), {"success": True})()

    monkeypatch.setattr(orchestrator_module, "_run_pipeline", _fake_run_pipeline)

    exit_code = orchestrator_module.run_cli(["run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert called.get("invoked") is True
    assert "No active session" not in captured.err


def test_cli_sessions_share_auth_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, orchestrator_module
) -> None:
    user_store, session_file, active_file = _configure_env(monkeypatch, tmp_path)

    exit_code = orchestrator_module.run_cli(
        ["user", "add", "dana", "--password", "s3cret", "--role", "editor"]
    )
    assert exit_code == 0
    capsys.readouterr()

    exit_code = orchestrator_module.run_cli(
        ["user", "login", "dana", "--password", "s3cret"]
    )
    assert exit_code == 0
    capsys.readouterr()

    token = active_file.read_text(encoding="utf-8").strip()
    assert token

    auth = AuthService(LocalUserStore(user_store), SessionManager(session_file))
    user = auth.authenticate(token)
    assert user is not None
    assert user.username == "dana"
    assert "editor" in user.roles

    exit_code = orchestrator_module.run_cli(["user", "logout"])
    assert exit_code == 0
    capsys.readouterr()

    assert auth.authenticate(token) is None
