from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_e2e_config.py"
SPEC = importlib.util.spec_from_file_location("check_apple_e2e_config", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_validate_config_accepts_env_file_credentials(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("E2E_USERNAME", raising=False)
    monkeypatch.delenv("E2E_PASSWORD", raising=False)
    monkeypatch.delenv("E2E_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("EBOOKTOOLS_SESSION_TOKEN", raising=False)
    monkeypatch.delenv("E2E_API_BASE_URL", raising=False)
    env_file = tmp_path / ".env.e2e"
    env_file.write_text(
        "\n".join(
            [
                "E2E_USERNAME=editor",
                "E2E_PASSWORD=secret",
                "E2E_API_BASE_URL=https://api.example.test",
            ]
        ),
        encoding="utf-8",
    )

    assert module.validate_config(env_file) == []
    assert module.resolve_config(env_file) == (
        "editor",
        "secret",
        "",
        "https://api.example.test",
    )


def test_validate_config_reports_missing_credentials_without_secret_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("E2E_USERNAME", raising=False)
    monkeypatch.delenv("E2E_PASSWORD", raising=False)
    monkeypatch.delenv("E2E_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("EBOOKTOOLS_SESSION_TOKEN", raising=False)
    monkeypatch.setenv("E2E_API_BASE_URL", "not-a-url")
    env_file = tmp_path / ".env.missing"

    errors = module.validate_config(env_file)

    assert "E2E_USERNAME is required" in errors
    assert "E2E_PASSWORD is required" in errors
    assert "E2E_API_BASE_URL must be an absolute HTTP(S) URL" in errors
    assert "secret" not in "; ".join(errors)


def test_validate_config_allows_missing_credentials_for_restored_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("E2E_USERNAME", raising=False)
    monkeypatch.delenv("E2E_PASSWORD", raising=False)
    monkeypatch.delenv("E2E_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("EBOOKTOOLS_SESSION_TOKEN", raising=False)
    monkeypatch.setenv("E2E_API_BASE_URL", "https://api.example.test")
    env_file = tmp_path / ".env.restored"

    assert module.validate_config(env_file, allow_restored_session=True) == []
    assert module.is_truthy("1")
    assert module.is_truthy("true")
    assert not module.is_truthy("")


def test_environment_overrides_env_file(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env.e2e"
    env_file.write_text(
        "\n".join(
            [
                "E2E_USERNAME=file-user",
                "E2E_PASSWORD=file-secret",
                "E2E_API_BASE_URL=https://file.example.test",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("E2E_USERNAME", "env-user")
    monkeypatch.setenv("E2E_PASSWORD", "env-secret")
    monkeypatch.setenv("E2E_AUTH_TOKEN", "env-token")
    monkeypatch.setenv("E2E_API_BASE_URL", "http://localhost:8001")

    assert module.resolve_config(env_file) == (
        "env-user",
        "env-secret",
        "env-token",
        "http://localhost:8001",
    )


def test_validate_config_allows_auth_token_without_credentials(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("E2E_USERNAME", raising=False)
    monkeypatch.delenv("E2E_PASSWORD", raising=False)
    monkeypatch.setenv("E2E_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("E2E_API_BASE_URL", "https://api.example.test")
    env_file = tmp_path / ".env.token"

    assert module.validate_config(env_file) == []
    assert module.resolve_config(env_file) == (
        "",
        "",
        "secret-token",
        "https://api.example.test",
    )
