from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_xcodebuild_e2e.py"
SPEC = importlib.util.spec_from_file_location("run_xcodebuild_e2e", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _write_fake_command(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake_xcodebuild.py"
    script.write_text(body, encoding="utf-8")
    return script


def test_retryable_notification_proxy_failure_retries_and_cleans_paths(
    tmp_path: Path,
    capsys,
) -> None:
    count_path = tmp_path / "count.txt"
    cleanup_path = tmp_path / "stale.xcresult"
    cleanup_path.mkdir()
    fake_command = _write_fake_command(
        tmp_path,
        f"""
from pathlib import Path
import sys

count_path = Path({str(count_path)!r})
count = int(count_path.read_text() or "0") if count_path.exists() else 0
count += 1
count_path.write_text(str(count))
if count == 1:
    print('Failed to start remote service "com.apple.mobile.notification_proxy" on device.')
    print('Could not establish a secure connection to the device.')
    raise SystemExit(65)
print("retry succeeded")
""",
    )

    status = module.main(
        [
            "--attempts",
            "2",
            "--cleanup-path",
            str(cleanup_path),
            "--label",
            "tvOS E2E xcodebuild",
            "--",
            sys.executable,
            str(fake_command),
        ]
    )

    captured = capsys.readouterr()
    assert status == 0
    assert count_path.read_text() == "2"
    assert not cleanup_path.exists()
    assert "retrying attempt 2/2" in captured.err
    assert "retry succeeded" in captured.out


def test_non_retryable_failure_exits_without_second_attempt(tmp_path: Path) -> None:
    count_path = tmp_path / "count.txt"
    fake_command = _write_fake_command(
        tmp_path,
        f"""
from pathlib import Path

count_path = Path({str(count_path)!r})
count = int(count_path.read_text() or "0") if count_path.exists() else 0
count_path.write_text(str(count + 1))
print("ordinary app assertion failed")
raise SystemExit(7)
""",
    )

    status = module.main(
        [
            "--attempts",
            "2",
            "--",
            sys.executable,
            str(fake_command),
        ]
    )

    assert status == 7
    assert count_path.read_text() == "1"


def test_retryable_detection_requires_both_service_markers() -> None:
    assert module.is_retryable_xcode_service_failure(
        'Failed to start remote service "com.apple.mobile.notification_proxy" on device.\n'
        "Could not establish a secure connection to the device."
    )
    assert not module.is_retryable_xcode_service_failure(
        'Failed to start remote service "com.apple.mobile.notification_proxy" on device.'
    )
