from pathlib import Path

from scripts.check_release_version_contract import (
    latest_changelog_day_and_version,
    latest_swift_changelog_day_and_version,
    release_date_id,
    release_date_label,
    validate,
)


def test_release_version_contract_is_consistent() -> None:
    validate()


def test_release_version_contract_extracts_latest_changelog_day(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## 2026-06-25

### 2026.06.25.13

- Latest entry.

## 2026-06-24

### 2026.06.24.27

- Older entry.
""",
        encoding="utf-8",
    )

    assert latest_changelog_day_and_version(changelog) == (
        "2026-06-25",
        "2026.06.25.13",
    )


def test_release_version_contract_extracts_latest_swift_changelog_day(tmp_path: Path) -> None:
    swift_changelog = tmp_path / "AppChangelogData.swift"
    swift_changelog.write_text(
        """
enum AppChangelogData {
    static let days: [AppChangelogDay] = [
        AppChangelogDay(
            id: "2026-06-25",
            dateLabel: "June 25, 2026",
            version: "2026.06.25.13",
            entries: []
        )
    ]
}
""",
        encoding="utf-8",
    )

    assert latest_swift_changelog_day_and_version(swift_changelog) == (
        "2026-06-25",
        "June 25, 2026",
        "2026.06.25.13",
    )


def test_release_version_contract_derives_visible_release_day() -> None:
    release = "2026.06.25.13"

    assert release_date_id(release) == "2026-06-25"
    assert release_date_label(release) == "June 25, 2026"
