from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLE_ROOT = ROOT / "ios" / "InteractiveReader"
PROJECT_FILE = APPLE_ROOT / "InteractiveReader.xcodeproj" / "project.pbxproj"
SETTINGS_SECTIONS = (
    APPLE_ROOT
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "PlaybackSettingsSections.swift"
)
SETTINGS_VIEW = (
    APPLE_ROOT
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "PlaybackSettingsView.swift"
)
SHARED_ROOT = APPLE_ROOT / "InteractiveReader" / "Features" / "Shared"


def test_browse_chrome_does_not_ship_the_redundant_action_row() -> None:
    project = PROJECT_FILE.read_text(encoding="utf-8")
    assert "BrowseActionRow.swift" not in project
    assert not (SHARED_ROOT / "BrowseActionRow.swift").exists()


def test_settings_owns_session_resume_sync_actions() -> None:
    sections = SETTINGS_SECTIONS.read_text(encoding="utf-8")
    view = SETTINGS_VIEW.read_text(encoding="utf-8")

    assert 'Label("Sync Resume Positions", systemImage: "arrow.triangle.2.circlepath")' in sections
    assert 'accessibilityIdentifier("settingsSyncResumePositionsButton")' in sections
    assert 'Label("Log Out", systemImage: "rectangle.portrait.and.arrow.right")' in sections
    assert 'accessibilityIdentifier("settingsLogOutButton")' in sections
    assert "PlaybackResumeStore.shared.syncNow" in view
    assert "appState.signOut()" in view
