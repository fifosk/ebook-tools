#!/usr/bin/env python3
"""Dry-run regex vs modern sentence splitter metrics for an EPUB or text file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.epub_parser import compare_sentence_splitter_modes, extract_text_from_epub


def _read_source(path: Path) -> str:
    if path.suffix.lower() == ".epub":
        return extract_text_from_epub(str(path))
    return path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="EPUB or UTF-8 text file to inspect")
    parser.add_argument("--max-words", type=int, default=18)
    parser.add_argument("--comma-semicolon", action="store_true")
    args = parser.parse_args()

    text = _read_source(args.source)
    report = compare_sentence_splitter_modes(
        text,
        max_words=args.max_words,
        extend_split_with_comma_semicolon=args.comma_semicolon,
    )
    report["source"] = str(args.source)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
