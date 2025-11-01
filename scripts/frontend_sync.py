"""Utilities for comparing frontend build state across machines."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Iterable

REPO_ROOT_MARKERS = {".git", "pyproject.toml"}


@dataclass(slots=True)
class GitSnapshot:
    """Represents the minimal git state required for parity checks."""

    branch: str | None
    commit: str | None
    dirty: bool
    tracked_changes: list[str]
    untracked_files: list[str]

    @classmethod
    def capture(cls, repo_root: Path) -> "GitSnapshot":
        branch = _run_git_command(("rev-parse", "--abbrev-ref", "HEAD"), repo_root)
        commit = _run_git_command(("rev-parse", "HEAD"), repo_root)
        status_output = _run_git_command(("status", "--short"), repo_root)
        status_lines = status_output.splitlines() if status_output else []

        tracked_changes: list[str] = []
        untracked_files: list[str] = []
        for line in status_lines:
            stripped = line.strip()
            if stripped.startswith("?? "):
                untracked_files.append(stripped[3:])
            else:
                tracked_changes.append(stripped)

        dirty = bool(tracked_changes)
        return cls(branch or None, commit or None, dirty, tracked_changes, untracked_files)


@dataclass(slots=True)
class EnvSnapshot:
    """Represents the parsed environment files under ``web/``."""

    filename: str
    variables: dict[str, str]


@dataclass(slots=True)
class BuildSnapshot:
    """Captures information about the Vite build output."""

    dist_dir: str
    manifest_hash: str | None


@dataclass(slots=True)
class RepositorySnapshot:
    """Aggregate snapshot ready for JSON serialisation."""

    repo_path: str
    git: GitSnapshot
    env_files: list[EnvSnapshot]
    build: BuildSnapshot
    api_version: str | None
    library_schema_hash: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_path": self.repo_path,
            "git": {
                "branch": self.git.branch,
                "commit": self.git.commit,
                "dirty": self.git.dirty,
                "tracked_changes": self.git.tracked_changes,
                "untracked_files": self.git.untracked_files,
            },
            "env_files": [
                {"filename": env.filename, "variables": env.variables}
                for env in self.env_files
            ],
            "build": {
                "dist_dir": self.build.dist_dir,
                "manifest_hash": self.build.manifest_hash,
            },
            "api_version": self.api_version,
            "library_schema_hash": self.library_schema_hash,
        }


def _run_git_command(args: Iterable[str], repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def _find_repo_root(path: Path) -> Path:
    path = path.resolve()
    if (path / ".git").exists():
        return path
    for parent in path.parents:
        if any((parent / marker).exists() for marker in REPO_ROOT_MARKERS):
            return parent
    raise ValueError(f"Unable to determine repository root from {path}")


def _parse_env_file(path: Path) -> dict[str, str]:
    variables: dict[str, str] = {}
    if not path.exists():
        return variables
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        variables[key.strip()] = value.strip()
    return variables


def _capture_env_snapshots(web_dir: Path) -> list[EnvSnapshot]:
    targets = [".env", ".env.local"]
    snapshots: list[EnvSnapshot] = []
    for filename in targets:
        env_path = web_dir / filename
        snapshots.append(EnvSnapshot(filename, _parse_env_file(env_path)))
    return snapshots


def _hash_manifest(dist_dir: Path) -> str | None:
    manifest_path = dist_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    digest = hashlib.sha256()
    digest.update(manifest_path.read_bytes())
    return digest.hexdigest()


def _capture_build_snapshot(web_dir: Path) -> BuildSnapshot:
    dist_dir = web_dir / "dist"
    return BuildSnapshot(str(dist_dir), _hash_manifest(dist_dir))


def _extract_api_version(repo_root: Path) -> str | None:
    application_path = repo_root / "modules" / "webapi" / "application.py"
    if not application_path.exists():
        return None
    for raw_line in application_path.read_text().splitlines():
        raw_line = raw_line.strip()
        if raw_line.startswith("app = FastAPI(") and "version=" in raw_line:
            start = raw_line.find("version=") + len("version=")
            fragment = raw_line[start:]
            # Expecting version="..."
            if fragment.startswith("\""):
                fragment = fragment[1:]
                end = fragment.find("\"")
                if end != -1:
                    return fragment[:end]
    return None


def _capture_library_schema(repo_root: Path) -> str | None:
    migrations_dir = repo_root / "modules" / "library" / "migrations"
    if not migrations_dir.exists():
        return None
    digest = hashlib.sha256()
    has_files = False
    for path in sorted(migrations_dir.glob("*.sql")):
        digest.update(path.read_bytes())
        has_files = True
    return digest.hexdigest() if has_files else None


def capture_snapshot(path: str) -> RepositorySnapshot:
    repo_root = _find_repo_root(Path(path))
    web_dir = repo_root / "web"
    git_snapshot = GitSnapshot.capture(repo_root)
    env_snapshots = _capture_env_snapshots(web_dir)
    build_snapshot = _capture_build_snapshot(web_dir)
    api_version = _extract_api_version(repo_root)
    library_schema_hash = _capture_library_schema(repo_root)
    return RepositorySnapshot(
        repo_path=str(repo_root),
        git=git_snapshot,
        env_files=env_snapshots,
        build=build_snapshot,
        api_version=api_version,
        library_schema_hash=library_schema_hash,
    )


def save_snapshot(snapshot: RepositorySnapshot, output: Path | None) -> None:
    serialised = snapshot.to_dict()
    json_output = json.dumps(serialised, indent=2, sort_keys=True)
    if output is None:
        print(json_output)
    else:
        output.write_text(json_output)
        print(f"Snapshot written to {output}")


def _load_snapshot(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def compare_snapshots(path_a: str, path_b: str) -> None:
    snapshot_a = _load_snapshot(Path(path_a))
    snapshot_b = _load_snapshot(Path(path_b))

    print("=== Frontend Sync Comparison ===")
    _compare_git(snapshot_a["git"], snapshot_b["git"])
    _compare_env(snapshot_a["env_files"], snapshot_b["env_files"])
    _compare_build(snapshot_a["build"], snapshot_b["build"])
    _compare_api_version(snapshot_a.get("api_version"), snapshot_b.get("api_version"))


def _compare_git(git_a: dict[str, object], git_b: dict[str, object]) -> None:
    print("\n[Git]")
    commit_a = git_a.get("commit")
    commit_b = git_b.get("commit")
    branch_a = git_a.get("branch")
    branch_b = git_b.get("branch")
    if commit_a == commit_b and branch_a == branch_b:
        print(f"✓ Matching commit {commit_a} on branch {branch_a}")
    else:
        print("⚠️ Git mismatch detected:")
        print(f"  Device A -> branch: {branch_a}, commit: {commit_a}")
        print(f"  Device B -> branch: {branch_b}, commit: {commit_b}")
    tracked_a = list(git_a.get("tracked_changes") or git_a.get("status_summary") or [])
    tracked_b = list(git_b.get("tracked_changes") or git_b.get("status_summary") or [])
    untracked_a = list(git_a.get("untracked_files") or [])
    untracked_b = list(git_b.get("untracked_files") or [])

    if git_a.get("dirty") and tracked_a:
        print("  Device A has tracked changes:")
        for line in tracked_a:
            print(f"    {line}")
    if git_b.get("dirty") and tracked_b:
        print("  Device B has tracked changes:")
        for line in tracked_b:
            print(f"    {line}")
    if untracked_a:
        print("  Device A has untracked files:")
        for path in untracked_a:
            print(f"    {path}")
    if untracked_b:
        print("  Device B has untracked files:")
        for path in untracked_b:
            print(f"    {path}")


def _compare_env(env_a: list[dict[str, object]], env_b: list[dict[str, object]]) -> None:
    print("\n[Environment]")
    env_index_b = {entry["filename"]: entry for entry in env_b}
    for entry_a in env_a:
        filename = entry_a["filename"]
        variables_a = entry_a.get("variables", {}) or {}
        entry_b = env_index_b.get(filename)
        if entry_b is None:
            print(f"⚠️ {filename} missing on device B")
            continue
        variables_b = entry_b.get("variables", {}) or {}
        _print_env_differences(filename, variables_a, variables_b)
    for filename, entry_b in env_index_b.items():
        if filename not in {entry["filename"] for entry in env_a}:
            print(f"⚠️ {filename} missing on device A")


def _print_env_differences(filename: str, vars_a: dict[str, str], vars_b: dict[str, str]) -> None:
    differing_keys = sorted(
        {key for key in vars_a if vars_a.get(key) != vars_b.get(key)}
        | {key for key in vars_b if vars_a.get(key) != vars_b.get(key)}
    )
    if not differing_keys:
        print(f"✓ {filename} matches on both devices")
        return
    print(f"⚠️ Differences found in {filename}:")
    for key in differing_keys:
        value_a = vars_a.get(key, "<missing>")
        value_b = vars_b.get(key, "<missing>")
        print(f"  {key}: device A -> {value_a}, device B -> {value_b}")
        if "URL" in key.upper():
            print("    ↳ API base URL mismatch may disable remote search")


def _compare_build(build_a: dict[str, object], build_b: dict[str, object]) -> None:
    print("\n[Build]")
    hash_a = build_a.get("manifest_hash")
    hash_b = build_b.get("manifest_hash")
    if not hash_a or not hash_b:
        print("⚠️ Build manifest missing on one or both devices. Run `npm install && npm run build`.")
        return
    if hash_a == hash_b:
        print(f"✓ Matching manifest hash: {hash_a}")
    else:
        print("⚠️ Build outputs differ. Rebuild the frontend and clear caches.")
        print(f"  Device A manifest hash: {hash_a}")
        print(f"  Device B manifest hash: {hash_b}")


def _compare_api_version(version_a: object, version_b: object) -> None:
    print("\n[API version]")
    if not version_a or not version_b:
        print("⚠️ Unable to determine API version for one or both devices.")
        print("    Restart the FastAPI backend to ensure it reads the latest settings.")
        return
    if version_a == version_b:
        print(f"✓ API versions match: {version_a}")
    else:
        print("⚠️ Backend versions differ; restart both services.")
        print(f"  Device A API version: {version_a}")
        print(f"  Device B API version: {version_b}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare frontend build state between machines to debug missing UI features.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser(
        "snapshot", help="Capture a snapshot of the current repository state."
    )
    snapshot_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the repository root (defaults to current directory).",
    )
    snapshot_parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path to write the snapshot JSON to.",
    )

    compare_parser = subparsers.add_parser(
        "compare", help="Compare two snapshot JSON files."
    )
    compare_parser.add_argument("snapshot_a", help="Snapshot JSON produced on device A.")
    compare_parser.add_argument("snapshot_b", help="Snapshot JSON produced on device B.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "snapshot":
        snapshot = capture_snapshot(args.path)
        save_snapshot(snapshot, args.output)
    elif args.command == "compare":
        compare_snapshots(args.snapshot_a, args.snapshot_b)


if __name__ == "__main__":
    main()
