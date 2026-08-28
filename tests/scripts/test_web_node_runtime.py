import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "scripts/run-web-npm.sh"
CHECK = ROOT / "web/scripts/check-node-runtime.mjs"


def _executable(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


@pytest.mark.parametrize("version", ["20.19.0", "22.12.0", "24.19.0", "18.20.0", "25.9.0", "26.0.0"])
def test_version_guard(version: str) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute the version guard")
    code = f"import {{ checkNodeRuntime }} from {json.dumps(CHECK.as_uri())}; checkNodeRuntime({json.dumps(version)});"
    result = subprocess.run([node, "--input-type=module", "-e", code], capture_output=True, text=True)
    if version.startswith(("20.", "22.", "24.")):
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
        assert f"Unsupported Node {version}" in result.stderr
        assert "WEB_NODE_BIN" in result.stderr


def test_wrapper_scopes_runtime_to_npm_and_children_and_preserves_exit(tmp_path: Path) -> None:
    selected = tmp_path / "selected runtime"
    other = tmp_path / "other"
    selected.mkdir()
    other.mkdir()
    log = tmp_path / "calls"
    _executable(selected / "node", 'printf "selected:%s\\n" "$*" >> "$PROBE_LOG"\n')
    _executable(other / "node", 'echo wrong-runtime >&2; exit 99\n')
    _executable(other / "npm", 'printf "npm:%s\\n" "$*" >> "$PROBE_LOG"\nnode child-probe\nexit 17\n')
    env = dict(os.environ, WEB_NODE_BIN=str(selected), PATH=f"{other}:/usr/bin:/bin", PROBE_LOG=str(log))
    result = subprocess.run([str(WRAPPER), "--prefix", "web", "test", "--", "an argument"], env=env, capture_output=True, text=True)
    assert result.returncode == 17
    assert log.read_text().splitlines() == [
        f"selected:{CHECK}", "npm:--prefix web test -- an argument", "selected:child-probe"
    ]


def test_wrapper_does_not_launch_npm_after_failed_guard(tmp_path: Path) -> None:
    _executable(tmp_path / "node", 'echo "unsupported runtime" >&2; exit 1\n')
    _executable(tmp_path / "npm", 'echo must-not-start >&2; exit 0\n')
    result = subprocess.run([str(WRAPPER), "test"], env=dict(os.environ, WEB_NODE_BIN=str(tmp_path)), capture_output=True, text=True)
    assert result.returncode == 1
    assert "unsupported runtime" in result.stderr
    assert "must-not-start" not in result.stderr


def test_wrapper_rejects_missing_selected_runtime(tmp_path: Path) -> None:
    result = subprocess.run([str(WRAPPER), "test"], env=dict(os.environ, WEB_NODE_BIN=str(tmp_path)), capture_output=True, text=True)
    assert result.returncode == 1
    assert "WEB_NODE_BIN must contain executable node" in result.stderr


def test_wrapper_rejects_missing_path_runtime(tmp_path: Path) -> None:
    env = dict(os.environ, PATH=str(tmp_path))
    env.pop("WEB_NODE_BIN", None)
    result = subprocess.run([str(WRAPPER), "test"], env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "Web gates require Node 24 and npm" in result.stderr
