from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "check_apple_shared_pipeline_manifest.py"
)
SPEC = importlib.util.spec_from_file_location("check_apple_shared_pipeline_manifest", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _write_manifest(
    pipeline_root: Path,
    *,
    credential_environment: list[str] | None = None,
    remote_environment_allowlist: list[str] | None = None,
) -> Path:
    app_dir = pipeline_root / "apps"
    app_dir.mkdir(parents=True)
    path = app_dir / "ebook-tools.json"
    payload = {
        "id": "ebook-tools",
        "simulatorContract": {
            "credentialEnvironment": credential_environment
            if credential_environment is not None
            else ["E2E_USERNAME", "E2E_PASSWORD", "E2E_AUTH_TOKEN", "EBOOKTOOLS_SESSION_TOKEN"],
            "remoteEnvironmentAllowlist": remote_environment_allowlist
            if remote_environment_allowlist is not None
            else ["E2E_USERNAME", "E2E_PASSWORD", "E2E_AUTH_TOKEN", "EBOOKTOOLS_SESSION_TOKEN"],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_validate_manifest_accepts_token_env_keys(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path)

    assert module.validate_manifest(path) == []


def test_validate_manifest_reports_missing_token_env_keys(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        credential_environment=["E2E_USERNAME", "E2E_PASSWORD"],
        remote_environment_allowlist=["E2E_USERNAME", "E2E_PASSWORD", "E2E_AUTH_TOKEN"],
    )

    errors = module.validate_manifest(path)

    assert any("simulatorContract.credentialEnvironment missing token env keys" in error for error in errors)
    assert any("E2E_AUTH_TOKEN" in error for error in errors)
    assert any("EBOOKTOOLS_SESSION_TOKEN" in error for error in errors)
    assert any("simulatorContract.remoteEnvironmentAllowlist missing token env keys" in error for error in errors)


def test_main_skips_absent_manifest_by_default(tmp_path: Path, capsys) -> None:
    result = module.main(["--pipeline-root", str(tmp_path)])

    assert result == 0
    assert "checks skipped" in capsys.readouterr().out


def test_main_can_require_manifest(tmp_path: Path, capsys) -> None:
    result = module.main(["--pipeline-root", str(tmp_path), "--require"])

    assert result == 1
    assert "manifest not found" in capsys.readouterr().err
