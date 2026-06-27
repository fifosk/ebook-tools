#!/usr/bin/env python3
"""Run focused test targets for the current Git changes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

BROAD_CHANGE_PREFIXES = (
    ".github/",
    "alembic/",
    "config/",
    "docker/",
    "helm/",
    "monitoring/",
)

BROAD_CHANGE_FILES = {
    "pyproject.toml",
    "tests/conftest.py",
    "docker-compose.yml",
}

PATH_TARGET_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("ios/", "tests/test_apple_", "tests/scripts/test_apple_", "tests/scripts/test_check_apple_", "tests/scripts/test_check_poc_readiness.py", "tests/scripts/test_generate_language_catalogs.py", "tests/scripts/test_ios_profile_capability_check.py", "tests/scripts/test_write_apple_e2e_config.py"), ("test-apple-contracts",)),
    (("web/",), ("test-web-full", "build-web-production")),
    (("modules/webapi/", "tests/modules/webapi/"), ("test-webapi",)),
    (("modules/services/", "tests/modules/services/"), ("test-services",)),
    (("modules/audio/", "tests/modules/audio/"), ("test-audio",)),
    (("modules/translation/", "tests/modules/translation/"), ("test-translation",)),
    (("modules/library/", "tests/modules/library/"), ("test-library",)),
    (("modules/render/", "tests/render/", "tests/modules/render/"), ("test-render",)),
    (("modules/media/", "tests/modules/media/"), ("test-media",)),
    (("modules/config", "config/", "tests/modules/config", "tests/modules/config_manager/"), ("test-config",)),
    (("modules/metadata", "tests/modules/metadata", "tests/test_library_metadata"), ("test-metadata",)),
    (("modules/search/",), ("test-backend-library-search-source-isbn",)),
    (("Makefile", "docs/testing.md", "PLAN.md", "AGENTS.md", "scripts/run_changed_tests.py", "tests/test_makefile_pytest_contract.py", "tests/test_web_video_dubbing_pipeline_contract.py", "tests/scripts/test_run_changed_tests.py"), ("test-makefile-contract",)),
)


def _run_git(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def changed_paths(base: str) -> list[str]:
    paths: set[str] = set()
    for args in (
        ["diff", "--name-only", "--diff-filter=ACMR", base, "--"],
        ["diff", "--name-only", "--diff-filter=ACMR", "--cached", "--"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        paths.update(_run_git(args))
    return sorted(paths)


def _matches(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def select_targets(paths: Iterable[str]) -> list[str]:
    normalized = sorted({path.strip().lstrip("./") for path in paths if path.strip()})
    if not normalized:
        return ["test-fast"]

    if any(path in BROAD_CHANGE_FILES or _matches(path, BROAD_CHANGE_PREFIXES) for path in normalized):
        return ["test-fast"]

    targets: list[str] = []
    for prefixes, candidate_targets in PATH_TARGET_RULES:
        if any(_matches(path, prefixes) for path in normalized):
            for target in candidate_targets:
                if target not in targets:
                    targets.append(target)

    return targets or ["test-fast"]


def run_targets(targets: list[str], *, dry_run: bool) -> int:
    print("Selected test targets: " + " ".join(targets), flush=True)
    if dry_run:
        return 0
    for target in targets:
        result = subprocess.run(["make", target], cwd=REPO_ROOT)
        if result.returncode:
            return result.returncode
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Git base revision for changed path detection. Defaults to HEAD.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected targets without running them.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional explicit paths to classify instead of reading Git changes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    paths = args.paths or changed_paths(args.base)
    return run_targets(select_targets(paths), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
