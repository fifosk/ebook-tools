from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate_language_catalogs.py"
SPEC = importlib.util.spec_from_file_location("generate_language_catalogs", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_build_web_language_codes_source_preserves_typescript_style() -> None:
    source = module.build_web_language_codes_source(
        [
            ("English", "en"),
            ("Chinese (Simplified)", "zh-CN"),
            ("Scottish Gaelic", "gd"),
        ]
    )

    assert source == "\n".join(
        [
            "export const LANGUAGE_CODES: Record<string, string> = {",
            "  English: 'en',",
            "  'Chinese (Simplified)': 'zh-CN',",
            "  'Scottish Gaelic': 'gd'",
            "};",
        ]
    )


def test_build_apple_language_entries_source_preserves_swift_style() -> None:
    source = module.build_apple_language_entries_source(
        [
            ("English", "en"),
            ("Chinese (Traditional)", "zh-TW"),
        ]
    )

    assert source == "\n".join(
        [
            "    static let entries: [(name: String, code: String)] = [",
            '        ("English", "en"),',
            '        ("Chinese (Traditional)", "zh-TW")',
            "    ]",
        ]
    )


def test_replace_language_catalog_blocks_updates_only_generated_sections() -> None:
    entries = [("English", "en"), ("Slovak", "sk")]
    web_source = "\n".join(
        [
            "export const LANGUAGE_CODES: Record<string, string> = {",
            "  Old: 'old'",
            "};",
            "",
            "const LANGUAGE_CODE_ALIASES: Record<string, string> = { eng: 'en' };",
        ]
    )
    apple_source = "\n".join(
        [
            "enum AppleLanguageCatalog {",
            "    static let entries: [(name: String, code: String)] = [",
            '        ("Old", "old")',
            "    ]",
            "",
            "    static let orderedLanguageNames = entries.map(\\.name)",
            "}",
        ]
    )

    assert "const LANGUAGE_CODE_ALIASES" in module.replace_web_language_codes(web_source, entries)
    assert '("Slovak", "sk")' in module.replace_apple_language_entries(apple_source, entries)


def test_expected_top_languages_preserves_existing_order_and_appends_new_backend_languages() -> None:
    entries = [("English", "en"), ("Arabic", "ar"), ("Slovak", "sk")]

    assert module.expected_top_languages(entries, ["Slovak", "Stale", "English"]) == [
        "Slovak",
        "English",
        "Arabic",
    ]


def test_replace_assets_top_languages_updates_only_when_membership_drifts() -> None:
    source = '{"top_languages":["Slovak","English"],"defaults":{"target_languages":["Arabic"]}}\n'

    updated = module.replace_assets_top_languages(source, [("English", "en"), ("Arabic", "ar"), ("Slovak", "sk")])

    assert '"top_languages": [' in updated
    assert updated.index('"Slovak"') < updated.index('"English"') < updated.index('"Arabic"')
    assert '"defaults": {' in updated
