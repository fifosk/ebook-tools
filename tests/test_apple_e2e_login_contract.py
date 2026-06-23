from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_HELPERS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReaderUITests"
    / "TestHelpers.swift"
)
JOURNEY_RUNNER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReaderUITests"
    / "JourneyRunner.swift"
)


def test_login_helper_clears_fields_before_typing_credentials() -> None:
    source = TEST_HELPERS.read_text(encoding="utf-8")

    assert "private func clearTextField(_ element: XCUIElement)" in source
    assert "XCUIKeyboardKey.delete.rawValue" in source
    assert "clearTextField(usernameField)\n        usernameField.typeText(username)" in source
    assert "clearTextField(passwordField)\n        passwordField.typeText(password)" in source


def test_journey_runner_can_tap_visible_but_not_hittable_ipad_controls() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "latestCandidate.exists && !latestCandidate.frame.isEmpty" in source
    assert "windowFrame.intersects(frame)" in source
    assert "coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()" in source


def test_journey_runner_uses_search_when_selecting_hidden_options() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "var didSearch = false" in source
    assert "searchForOption(optionLabel)" in source
    assert "app.searchFields.firstMatch" in source
    assert "searchField.typeText(optionLabel)" in source
