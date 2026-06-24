from __future__ import annotations

import re
from pathlib import Path

from modules.shared import assets
from modules.language_constants import LANGUAGE_CODES
from modules.webapi.routers import create_book


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
APPLE_CREATE_SUPPORT = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSupport.swift"
)
APPLE_CREATE_LANGUAGE_OPTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateLanguageOptions.swift"
)
APPLE_CREATE_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateModels.swift"
)
APPLE_CREATE_SECTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateSections.swift"
)
APPLE_CREATE_LANGUAGE_SELECTOR = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Create"
    / "AppleBookCreateLanguageSelector.swift"
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
    web_menu_languages = assets.get_top_languages()

    assert len(backend_entries) >= 80
    assert ("Hindi", "hi") in backend_entries
    assert ("Chinese (Traditional)", "zh-TW") in backend_entries
    assert ("Persian", "fa") in backend_entries

    assert web_entries == backend_entries
    assert apple_entries == backend_entries
    assert len(web_menu_languages) == len(backend_entries)
    assert set(web_menu_languages) == set(LANGUAGE_CODES)
    assert set(web_menu_languages) == {name for name, _ in apple_entries}


def test_apple_create_language_options_include_full_web_catalog_fallback() -> None:
    models_source = APPLE_CREATE_MODELS.read_text(encoding="utf-8")
    language_options_source = APPLE_CREATE_LANGUAGE_OPTIONS.read_text(encoding="utf-8")
    support_source = APPLE_CREATE_SUPPORT.read_text(encoding="utf-8")

    assert "static let fallbackOptions: [AppleBookCreateLanguage] =" in models_source
    assert "AppleLanguageCatalog.orderedLanguageNames.compactMap { AppleBookCreateLanguage($0) }" in models_source
    assert "static let allCases = fallbackOptions" in models_source
    assert (
        "for language in supported.compactMap(AppleBookCreateLanguage.init(backendValue:)) + fallbackOptions"
        in models_source
    )
    assert "static func availableInputLanguages(" in language_options_source
    assert "availableLanguages(options?.supportedInputLanguages ?? [])" in language_options_source
    assert "static func availableTargetLanguages(" in language_options_source
    assert "availableLanguages(options?.supportedOutputLanguages ?? [])" in language_options_source
    assert "AppleBookCreateLanguage.options(from: supported)" in language_options_source
    assert "static func availableInputLanguages(" not in support_source
    assert "static func availableTargetLanguages(" not in support_source


def test_book_creation_options_advertise_full_language_catalog() -> None:
    options = create_book._build_creation_options({})
    expected_languages = list(LANGUAGE_CODES)

    assert options.supported_input_languages == expected_languages
    assert options.supported_output_languages == expected_languages
    assert set(options.supported_input_languages) == set(assets.get_top_languages())
    assert set(options.supported_output_languages) == set(assets.get_top_languages())


def test_apple_create_language_controls_share_available_lists_across_surfaces() -> None:
    source = APPLE_CREATE_SECTIONS.read_text(encoding="utf-8")
    selector_source = APPLE_CREATE_LANGUAGE_SELECTOR.read_text(encoding="utf-8")

    tvos_block = re.search(
        r"#if os\(tvOS\)(?P<body>.*?)#else",
        source,
        flags=re.S,
    )
    assert tvos_block is not None
    assert 'Picker("Input", selection: $inputLanguage)' in tvos_block.group("body")
    assert "ForEach(availableInputLanguages)" in tvos_block.group("body")
    assert 'Picker("Target", selection: $targetLanguage)' in tvos_block.group("body")
    assert "ForEach(availableTargetLanguages)" in tvos_block.group("body")

    non_tvos_block = re.search(
        r"#else(?P<body>.*?)#endif",
        source,
        flags=re.S,
    )
    assert non_tvos_block is not None
    assert "AppleBookCreateLanguageSelector(" in non_tvos_block.group("body")
    assert "options: availableInputLanguages" in non_tvos_block.group("body")
    assert "options: availableTargetLanguages" in non_tvos_block.group("body")
    assert 'Text("\\(options.count) available")' in selector_source
    assert '.accessibilityValue("\\(selection.label), \\(options.count) available")' in selector_source
