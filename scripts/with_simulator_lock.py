#!/usr/bin/env python3
"""Run a command while holding the shared Apple simulator mutation lock."""

from __future__ import annotations

import argparse
import fcntl
import os
import subprocess
import tempfile
from pathlib import Path


DEFAULT_LOCK = Path(tempfile.gettempdir()) / "apple-device-app-pipeline-simctl.lock"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lock-path",
        default=os.environ.get("E2E_SIMCTL_LOCK", str(DEFAULT_LOCK)),
        help="Lock path shared with the Apple device app pipeline.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --.")
    args = parser.parse_args()

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("missing command to run")

    lock_path = Path(args.lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return subprocess.run(command, check=False).returncode
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


if __name__ == "__main__":
    raise SystemExit(main())
