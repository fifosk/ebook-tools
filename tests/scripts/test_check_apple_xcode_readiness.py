from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_xcode_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_apple_xcode_readiness", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _fake_xcodebuild(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "xcodebuild"
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_validate_xcodebuild_accepts_ready_xcode(tmp_path: Path) -> None:
    xcodebuild = _fake_xcodebuild(tmp_path, "exit 0\n")

    assert module.validate_xcodebuild(str(xcodebuild)) == []


def test_validate_xcodebuild_reports_license_failure_without_raw_output(tmp_path: Path) -> None:
    xcodebuild = _fake_xcodebuild(
        tmp_path,
        "echo 'You have not agreed to the Xcode license agreements.' >&2\nexit 69\n",
    )

    errors = module.validate_xcodebuild(str(xcodebuild))

    assert errors == [
        "Xcode license is not accepted; run "
        "'sudo xcodebuild -license' or 'sudo xcodebuild -runFirstLaunch' on this Mac"
    ]
    assert "not agreed" not in errors[0]


def test_validate_xcodebuild_reports_missing_binary() -> None:
    errors = module.validate_xcodebuild("/missing/Xcode.app/xcodebuild")

    assert errors == ["xcodebuild not found at /missing/Xcode.app/xcodebuild"]
