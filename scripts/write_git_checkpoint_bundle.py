#!/usr/bin/env python3
"""Write a Git bundle for committed local checkpoints that are not on a base ref."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def sanitize_ref(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "ref"


def dirty_paths(repo: Path) -> list[str]:
    status = run_git(repo, ["status", "--porcelain=v1", "-uall"])
    return [line for line in status.splitlines() if line.strip()]


def commit_rows(repo: Path, base: str, head: str) -> list[dict[str, str]]:
    output = run_git(
        repo,
        [
            "log",
            "--reverse",
            "--format=%H%x00%h%x00%s",
            f"{base}..{head}",
        ],
    )
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        full, short, subject = line.split("\x00", 2)
        rows.append({"hash": full, "short": short, "subject": subject})
    return rows


def write_checkpoint_bundle(
    *,
    repo: Path,
    base: str,
    head: str,
    output_dir: Path,
    timestamp: str | None = None,
    allow_dirty: bool = False,
) -> tuple[Path | None, Path | None]:
    repo = repo.resolve()
    if not allow_dirty:
        paths = dirty_paths(repo)
        if paths:
            preview = "\n".join(paths[:10])
            raise RuntimeError(
                "working tree is dirty; commit or pass --allow-dirty to bundle committed changes only\n"
                + preview
            )

    base_sha = run_git(repo, ["rev-parse", "--verify", base])
    head_sha = run_git(repo, ["rev-parse", "--verify", head])
    commits = commit_rows(repo, base, head)
    if not commits:
        return None, None

    branch = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    stamp = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = (
        f"checkpoint-{sanitize_ref(branch)}-"
        f"{sanitize_ref(base)}-{base_sha[:8]}..{head_sha[:8]}-{stamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / f"{name}.bundle"
    manifest_path = output_dir / f"{name}.json"

    run_git(repo, ["bundle", "create", str(bundle_path), f"{base}..{head}"])
    run_git(repo, ["bundle", "verify", str(bundle_path)])
    manifest = {
        "repo": str(repo),
        "base": base,
        "base_sha": base_sha,
        "head": head,
        "head_sha": head_sha,
        "branch": branch,
        "created_at": stamp,
        "commit_count": len(commits),
        "commits": commits,
        "bundle": str(bundle_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle_path, manifest_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT, help="Git repository root")
    parser.add_argument("--base", default="origin/main", help="Base ref already pushed")
    parser.add_argument("--head", default="HEAD", help="Head ref to bundle")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "test-results" / "git-checkpoints",
        help="Directory for bundle and manifest output",
    )
    parser.add_argument("--timestamp", help="Override bundle timestamp for tests")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow dirty working trees; only committed changes are bundled",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bundle_path, manifest_path = write_checkpoint_bundle(
            repo=args.repo,
            base=args.base,
            head=args.head,
            output_dir=args.output_dir,
            timestamp=args.timestamp,
            allow_dirty=args.allow_dirty,
        )
    except RuntimeError as exc:
        print(f"git checkpoint bundle failed: {exc}", file=sys.stderr)
        return 1

    if bundle_path is None or manifest_path is None:
        print(f"No local commits to bundle: {args.head} is already contained in {args.base}.")
        return 0

    print(f"Wrote git checkpoint bundle: {bundle_path}")
    print(f"Wrote git checkpoint manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
