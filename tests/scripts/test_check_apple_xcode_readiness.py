from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_xcode_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_apple_xcode_readiness", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)

ATTENDED_ADMIN_HINT = (
    "If this check is running over SSH or CI, complete the command once "
    "in an attended admin terminal on that Mac, then rerun this preflight"
)
LICENSE_FAILURE_MESSAGE = (
    "Xcode license is not accepted; run "
    "'sudo xcodebuild -license' or 'sudo xcodebuild -runFirstLaunch' on this Mac. "
    + ATTENDED_ADMIN_HINT
)
FIRST_LAUNCH_FAILURE_MESSAGE = (
    "Xcode first-launch tasks are incomplete; run "
    "'sudo xcodebuild -runFirstLaunch' on this Mac. "
    + ATTENDED_ADMIN_HINT
)
ACCOUNT_CACHE_FAILURE_PREFIX = "macOS account/cache lookup is unhealthy for Xcode simulator builds"


def _fake_xcodebuild(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "xcodebuild"
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _skip_host_cache_check() -> list[str]:
    return []


def test_validate_xcodebuild_accepts_ready_xcode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "validate_macos_user_cache", _skip_host_cache_check)
    xcodebuild = _fake_xcodebuild(tmp_path, "exit 0\n")

    assert module.validate_xcodebuild(str(xcodebuild)) == []


def test_validate_xcodebuild_reports_license_failure_without_raw_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "validate_macos_user_cache", _skip_host_cache_check)
    xcodebuild = _fake_xcodebuild(
        tmp_path,
        "echo 'You have not agreed to the Xcode license agreements.' >&2\nexit 69\n",
    )

    errors = module.validate_xcodebuild(str(xcodebuild))

    assert errors == [LICENSE_FAILURE_MESSAGE]
    assert "not agreed" not in errors[0]


def test_validate_xcodebuild_checks_license_before_generic_first_launch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "validate_macos_user_cache", _skip_host_cache_check)
    xcodebuild = _fake_xcodebuild(
        tmp_path,
        """
if [ "$1" = "-license" ]; then
  echo 'You have not agreed to the Xcode license agreements.' >&2
  exit 69
fi
echo 'Xcode first launch tasks are incomplete.' >&2
exit 1
""",
    )

    errors = module.validate_xcodebuild(str(xcodebuild))

    assert errors == [LICENSE_FAILURE_MESSAGE]


def test_validate_xcodebuild_ignores_unsupported_license_check_when_ready(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "validate_macos_user_cache", _skip_host_cache_check)
    xcodebuild = _fake_xcodebuild(
        tmp_path,
        """
if [ "$1" = "-license" ]; then
  echo 'xcodebuild: error: invalid option check' >&2
  exit 64
fi
exit 0
""",
    )

    assert module.validate_xcodebuild(str(xcodebuild)) == []


def test_validate_xcodebuild_reports_first_launch_after_license_check_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(module, "validate_macos_user_cache", _skip_host_cache_check)
    xcodebuild = _fake_xcodebuild(
        tmp_path,
        """
if [ "$1" = "-license" ]; then
  exit 0
fi
echo 'Xcode first launch tasks are incomplete.' >&2
exit 1
""",
    )

    errors = module.validate_xcodebuild(str(xcodebuild))

    assert errors == [FIRST_LAUNCH_FAILURE_MESSAGE]


def test_validate_xcodebuild_reports_missing_binary(monkeypatch) -> None:
    monkeypatch.setattr(module, "validate_macos_user_cache", _skip_host_cache_check)
    errors = module.validate_xcodebuild("/missing/Xcode.app/xcodebuild")

    assert errors == ["xcodebuild not found at /missing/Xcode.app/xcodebuild"]


def test_validate_macos_user_cache_skips_non_macos(monkeypatch) -> None:
    monkeypatch.setattr(module.sys, "platform", "linux")

    assert module.validate_macos_user_cache() == []


def test_validate_macos_user_cache_reports_missing_passwd_entry(monkeypatch) -> None:
    monkeypatch.setattr(module.sys, "platform", "darwin")
    monkeypatch.setattr(module.os, "getuid", lambda: 501)

    def missing_user(uid: int) -> None:
        raise KeyError(uid)

    monkeypatch.setattr(module.pwd, "getpwuid", missing_user)

    errors = module.validate_macos_user_cache()

    assert len(errors) == 1
    assert errors[0].startswith(ACCOUNT_CACHE_FAILURE_PREFIX)
    assert "uid 501 has no passwd entry" in errors[0]


def test_validate_macos_user_cache_reports_broken_darwin_cache_lookup(monkeypatch) -> None:
    monkeypatch.setattr(module.sys, "platform", "darwin")
    monkeypatch.setattr(module.os, "getuid", lambda: 501)
    monkeypatch.setattr(module.pwd, "getpwuid", lambda uid: object())
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 71, "", "Input/output error"),
    )

    errors = module.validate_macos_user_cache()

    assert len(errors) == 1
    assert errors[0].startswith(ACCOUNT_CACHE_FAILURE_PREFIX)
    assert "DARWIN_USER_CACHE_DIR lookup failed" in errors[0]


def test_validate_xcodebuild_stops_before_xcode_when_host_cache_is_broken(tmp_path: Path, monkeypatch) -> None:
    xcodebuild = _fake_xcodebuild(tmp_path, "echo should-not-run >&2\nexit 1\n")
    monkeypatch.setattr(
        module,
        "validate_macos_user_cache",
        lambda: ["macOS account/cache lookup is unhealthy for Xcode simulator builds (test)"],
    )

    errors = module.validate_xcodebuild(str(xcodebuild))

    assert errors == ["macOS account/cache lookup is unhealthy for Xcode simulator builds (test)"]
