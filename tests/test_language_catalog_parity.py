from __future__ import annotations

import re
from pathlib import Path

from modules.language_constants import LANGUAGE_CODES


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


def _web_language_codes() -> list[tuple[str, str]]:
    source = WEB_LANGUAGE_CODES.read_text(encoding="utf-8")
    match = re.search(
        r"export const LANGUAGE_CODES:[^{]+=\s*\{(?P<body>.*?)\};",
        source,
        flags=re.S,
    )
    assert match is not None, "Could not find Web LANGUAGE_CODES object"

    entries: list[tuple[str, str]] = []
    for line in match.group("body").splitlines():
        entry = re.search(
            r"^\s*(?:'(?P<quoted>[^']+)'|(?P<bare>[A-Za-z][A-Za-z0-9 ]*)):\s*'(?P<code>[^']+)'",
            line,
        )
        if entry is None:
            continue
        name = entry.group("quoted") or entry.group("bare")
        entries.append((name, entry.group("code")))
    return entries


def _apple_language_catalog() -> list[tuple[str, str]]:
    source = APPLE_LANGUAGE_CATALOG.read_text(encoding="utf-8")
    match = re.search(
        r"static let entries:.*?=\s*\[(?P<body>.*?)\n\s*\]",
        source,
        flags=re.S,
    )
    assert match is not None, "Could not find AppleLanguageCatalog.entries"
    return re.findall(r'\("([^"]+)",\s*"([^"]+)"\)', match.group("body"))


def test_language_catalogs_match_across_backend_web_and_apple() -> None:
    backend_entries = list(LANGUAGE_CODES.items())
    web_entries = _web_language_codes()
    apple_entries = _apple_language_catalog()

    assert len(backend_entries) >= 80
    assert ("Hindi", "hi") in backend_entries
    assert ("Chinese (Traditional)", "zh-TW") in backend_entries
    assert ("Persian", "fa") in backend_entries

    assert web_entries == backend_entries
    assert apple_entries == backend_entries
