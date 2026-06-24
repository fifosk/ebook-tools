#!/usr/bin/env python3
"""Generate Web and Apple language catalog blocks from backend constants."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_LANGUAGE_CODES = ROOT / "web" / "src" / "constants" / "languageCodes.ts"
APPLE_LANGUAGE_CATALOG = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Shared"
    / "PlayerLanguageFlagResolver.swift"
)


def load_language_codes(root: Path) -> list[tuple[str, str]]:
    sys.path.insert(0, str(root))
    try:
        from modules.language_constants import LANGUAGE_CODES
    finally:
        try:
            sys.path.remove(str(root))
        except ValueError:
            pass
    return list(LANGUAGE_CODES.items())


def ts_key(name: str) -> str:
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name):
        return name
    return f"'{name}'"


def build_web_language_codes_source(entries: list[tuple[str, str]]) -> str:
    lines = ["export const LANGUAGE_CODES: Record<string, string> = {"]
    for index, (name, code) in enumerate(entries):
        suffix = "," if index < len(entries) - 1 else ""
        lines.append(f"  {ts_key(name)}: '{code}'{suffix}")
    lines.append("};")
    return "\n".join(lines)


def build_apple_language_entries_source(entries: list[tuple[str, str]]) -> str:
    lines = ["    static let entries: [(name: String, code: String)] = ["]
    for index, (name, code) in enumerate(entries):
        suffix = "," if index < len(entries) - 1 else ""
        lines.append(f'        ("{name}", "{code}"){suffix}')
    lines.append("    ]")
    return "\n".join(lines)


def replace_web_language_codes(source: str, entries: list[tuple[str, str]]) -> str:
    pattern = re.compile(
        r"export const LANGUAGE_CODES: Record<string, string> = \{.*?\n\};",
        flags=re.S,
    )
    updated, count = pattern.subn(build_web_language_codes_source(entries), source, count=1)
    if count != 1:
        raise ValueError("Could not find Web LANGUAGE_CODES block")
    return updated


def replace_apple_language_entries(source: str, entries: list[tuple[str, str]]) -> str:
    pattern = re.compile(
        r"    static let entries: \[\(name: String, code: String\)\] = \[.*?\n    \]",
        flags=re.S,
    )
    updated, count = pattern.subn(build_apple_language_entries_source(entries), source, count=1)
    if count != 1:
        raise ValueError("Could not find AppleLanguageCatalog entries block")
    return updated


def generate(root: Path, *, check: bool) -> list[Path]:
    entries = load_language_codes(root)
    updates: list[tuple[Path, str]] = []

    web_path = root / WEB_LANGUAGE_CODES.relative_to(ROOT)
    web_source = web_path.read_text(encoding="utf-8")
    web_updated = replace_web_language_codes(web_source, entries)
    updates.append((web_path, web_updated))

    apple_path = root / APPLE_LANGUAGE_CATALOG.relative_to(ROOT)
    apple_source = apple_path.read_text(encoding="utf-8")
    apple_updated = replace_apple_language_entries(apple_source, entries)
    updates.append((apple_path, apple_updated))

    changed = [path for path, updated in updates if path.read_text(encoding="utf-8") != updated]
    if check:
        return changed

    for path, updated in updates:
        path.write_text(updated, encoding="utf-8")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    parser.add_argument("--check", action="store_true", help="Fail if generated files are stale")
    args = parser.parse_args(argv)

    stale_paths = generate(args.root.resolve(), check=args.check)
    if stale_paths:
        for path in stale_paths:
            print(f"stale language catalog: {path}", file=sys.stderr)
        if args.check:
            print("Run scripts/generate_language_catalogs.py to refresh generated catalogs.", file=sys.stderr)
            return 1
    elif args.check:
        print("language catalogs are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
