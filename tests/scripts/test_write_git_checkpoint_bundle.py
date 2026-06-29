from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "write_git_checkpoint_bundle.py"
SPEC = importlib.util.spec_from_file_location("write_git_checkpoint_bundle", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(path: Path) -> Path:
    repo = path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Tests")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")
    _git(repo, "tag", "origin-main")
    return repo


def test_write_checkpoint_bundle_creates_verified_bundle_and_manifest(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("base\ncheckpoint\n", encoding="utf-8")
    _git(repo, "commit", "-am", "checkpoint one")

    bundle_path, manifest_path = module.write_checkpoint_bundle(
        repo=repo,
        base="origin-main",
        head="HEAD",
        output_dir=tmp_path / "bundles",
        timestamp="20260629T120000Z",
    )

    assert bundle_path is not None
    assert manifest_path is not None
    assert bundle_path.exists()
    assert "checkpoint-main-origin-main-" in bundle_path.name
    assert _git(repo, "bundle", "verify", str(bundle_path))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["base"] == "origin-main"
    assert manifest["head"] == "HEAD"
    assert manifest["commit_count"] == 1
    assert manifest["commits"][0]["subject"] == "checkpoint one"
    assert manifest["bundle"] == str(bundle_path)


def test_write_checkpoint_bundle_rejects_dirty_tree_by_default(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")

    try:
        module.write_checkpoint_bundle(
            repo=repo,
            base="origin-main",
            head="HEAD",
            output_dir=tmp_path / "bundles",
        )
    except RuntimeError as exc:
        assert "working tree is dirty" in str(exc)
        assert "README.md" in str(exc)
    else:  # pragma: no cover - keeps the assertion message clear if behavior regresses
        raise AssertionError("dirty working tree should fail without allow_dirty")


def test_write_checkpoint_bundle_noops_when_head_is_in_base(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    bundle_path, manifest_path = module.write_checkpoint_bundle(
        repo=repo,
        base="origin-main",
        head="HEAD",
        output_dir=tmp_path / "bundles",
    )

    assert bundle_path is None
    assert manifest_path is None
