from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "write_apple_e2e_config.py"
SPEC = importlib.util.spec_from_file_location("write_apple_e2e_config", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_write_config_strips_env_quotes_and_copies_journey(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "E2E_USERNAME='alice'",
                'E2E_PASSWORD="secret"',
                "E2E_API_BASE_URL='https://example.test/'",
            ]
        ),
        encoding="utf-8",
    )
    journey_src = tmp_path / "create_readiness.json"
    journey_src.write_text('{"id":"create_readiness","steps":[]}', encoding="utf-8")
    config_path = tmp_path / "profile" / "ios_e2e_config.json"
    journey_path = tmp_path / "profile" / "ios_e2e_journey.json"
    fallback_config_path = tmp_path / "ipados" / "ios_e2e_config.json"
    fallback_journey_path = tmp_path / "ipados" / "ios_e2e_journey.json"

    monkeypatch.delenv("E2E_USERNAME", raising=False)
    monkeypatch.delenv("E2E_PASSWORD", raising=False)
    monkeypatch.delenv("E2E_API_BASE_URL", raising=False)

    config = module.write_config_and_journey(
        env_file=env_file,
        config_path=config_path,
        journey_src=journey_src,
        journey_path=journey_path,
        fallback_config_path=fallback_config_path,
        fallback_journey_path=fallback_journey_path,
    )

    assert config == {
        "username": "alice",
        "password": "secret",
        "api_base_url": "https://example.test/",
        "allow_restored_session": False,
    }
    assert json.loads(config_path.read_text(encoding="utf-8")) == config
    assert journey_path.read_text(encoding="utf-8") == journey_src.read_text(encoding="utf-8")
    assert json.loads(fallback_config_path.read_text(encoding="utf-8")) == config
    assert fallback_journey_path.read_text(encoding="utf-8") == journey_src.read_text(encoding="utf-8")


def test_environment_values_override_env_file(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "E2E_USERNAME=file-user",
                "E2E_PASSWORD=file-password",
                "E2E_API_BASE_URL=https://file.example",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("E2E_USERNAME", "env-user")
    monkeypatch.setenv("E2E_PASSWORD", "env-password")
    monkeypatch.setenv("E2E_API_BASE_URL", "https://env.example")

    assert module.resolve_config(env_file) == {
        "username": "env-user",
        "password": "env-password",
        "api_base_url": "https://env.example",
        "allow_restored_session": False,
    }


def test_missing_env_file_uses_public_default_api_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("E2E_USERNAME", raising=False)
    monkeypatch.delenv("E2E_PASSWORD", raising=False)
    monkeypatch.delenv("E2E_API_BASE_URL", raising=False)

    assert module.resolve_config(tmp_path / "missing.env") == {
        "username": "",
        "password": "",
        "api_base_url": module.DEFAULT_API_BASE_URL,
        "allow_restored_session": False,
    }


def test_restored_session_flag_is_written_from_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("E2E_USERNAME", raising=False)
    monkeypatch.delenv("E2E_PASSWORD", raising=False)
    monkeypatch.delenv("E2E_API_BASE_URL", raising=False)
    monkeypatch.setenv("E2E_ALLOW_RESTORED_SESSION", "1")

    config = module.resolve_config(tmp_path / "missing.env")

    assert config["allow_restored_session"] is True
