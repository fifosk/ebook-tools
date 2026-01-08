#!/usr/bin/env python3
"""Validate googletrans support for maintained language list."""

from __future__ import annotations

import argparse
import time

import sys
from pathlib import Path

from googletrans import LANGUAGES

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.language_constants import LANGUAGE_CODES
from modules.retry_annotations import is_failure_annotation
import modules.translation_engine as translation_engine


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check googletrans translation support for maintained languages."
    )
    parser.add_argument(
        "--language",
        action="append",
        default=[],
        help="Filter by language name or code (repeatable, supports comma-separated values).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Seconds to sleep between translation requests.",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=1,
        help="Number of attempts per translation (default: 1).",
    )
    parser.add_argument(
        "--sample",
        default="This is a test sentence.",
        help="Sample sentence to translate.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-language results.",
    )
    return parser.parse_args()


def _select_languages(language_filters: list[str]) -> dict[str, str]:
    if not language_filters:
        return dict(LANGUAGE_CODES)

    tokens: list[str] = []
    for entry in language_filters:
        raw = (entry or "").strip()
        if not raw:
            continue
        tokens.extend(part.strip() for part in raw.split(",") if part.strip())

    if not tokens:
        return dict(LANGUAGE_CODES)

    name_lookup = {name.lower(): name for name in LANGUAGE_CODES}
    code_lookup = {code.lower(): name for name, code in LANGUAGE_CODES.items()}

    selected: list[str] = []
    unknown: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in name_lookup:
            selected.append(name_lookup[key])
        elif key in code_lookup:
            selected.append(code_lookup[key])
        else:
            unknown.append(token)

    if unknown:
        print(f"Unknown language filters: {', '.join(unknown)}", file=sys.stderr)

    if not selected:
        return {}

    seen = set()
    filtered: dict[str, str] = {}
    for name in selected:
        if name in seen:
            continue
        seen.add(name)
        filtered[name] = LANGUAGE_CODES[name]
    return filtered


def main() -> None:
    args = _parse_args()
    translation_engine._TRANSLATION_RESPONSE_ATTEMPTS = max(1, args.attempts)
    translation_engine._TRANSLATION_RETRY_DELAY_SECONDS = 0.0

    ok = []
    unsupported = []
    failed = []

    target_languages = _select_languages(args.language)
    if not target_languages:
        print("No matching languages to test.")
        return

    for name, code in target_languages.items():
        resolved = translation_engine._resolve_googletrans_language(name, fallback=None)
        resolved_lower = resolved.lower() if isinstance(resolved, str) else None
        if not resolved_lower or resolved_lower not in LANGUAGES:
            unsupported.append((name, code, resolved))
            if args.verbose:
                print(f"unsupported: {name} ({code}) -> {resolved or 'None'}")
            continue

        text, error = translation_engine._translate_with_googletrans(
            args.sample, "English", name
        )
        success = (
            error is None
            and not is_failure_annotation(text)
            and bool(str(text).strip())
        )
        if success:
            ok.append((name, resolved))
            if args.verbose:
                print(f"ok: {name} -> {resolved}")
        else:
            failed.append((name, resolved, error or text))
            if args.verbose:
                print(f"failed: {name} -> {resolved} ({error or text})")

        if args.delay:
            time.sleep(max(args.delay, 0.0))

    print(f"ok: {len(ok)}")
    print(f"unsupported: {len(unsupported)}")
    print(f"failed: {len(failed)}")
    if unsupported:
        print("\nunsupported languages:")
        for name, code, resolved in unsupported:
            print(f"- {name} ({code}) -> {resolved or 'None'}")
    if failed:
        print("\nfailed translations:")
        for name, resolved, error in failed:
            print(f"- {name} ({resolved}): {error}")


if __name__ == "__main__":
    main()
