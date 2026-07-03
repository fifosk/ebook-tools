from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_build_metadata.py"
SPEC = importlib.util.spec_from_file_location("check_apple_build_metadata", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_build_metadata_accepts_matching_stamps(tmp_path: Path) -> None:
    app = tmp_path / "InteractiveReaderTV.app"
    app.mkdir()
    (app / "branch.stamp").write_text("main\n", encoding="utf-8")
    (app / "commit.stamp").write_text("2ec0089bf6d8\n", encoding="utf-8")

    assert module.verify_bundle(app, expected_branch="main", expected_commit="2ec0089bf6d8") == []


def test_build_metadata_rejects_missing_bundle(tmp_path: Path) -> None:
    missing = tmp_path / "Missing.app"

    assert module.verify_bundle(missing, expected_branch="main", expected_commit="abc") == [
        f"Apple app bundle does not exist: {missing}"
    ]


def test_build_metadata_rejects_stale_commit(tmp_path: Path) -> None:
    app = tmp_path / "InteractiveReader.app"
    app.mkdir()
    (app / "branch.stamp").write_text("main\n", encoding="utf-8")
    (app / "commit.stamp").write_text("oldsha\n", encoding="utf-8")

    assert module.verify_bundle(app, expected_branch="main", expected_commit="newsha") == [
        "Apple app bundle commit.stamp oldsha does not match newsha"
    ]
