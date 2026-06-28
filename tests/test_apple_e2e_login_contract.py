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
APP_STATE = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "App" / "AppState.swift"
LIBRARY_SHELL = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "LibraryShellView.swift"
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
    assert "No restored E2E session was available" in source
    assert "Configured E2E_AUTH_TOKEN was rejected or expired" in source
    assert "profile \\(e2eProfileLabel)" in source
    assert "allowsRestoredSession" in source
    assert "hasConfiguredE2EAuthToken" in source


def test_tvos_login_helper_actively_focuses_fields_before_typing() -> None:
    source = TEST_HELPERS.read_text(encoding="utf-8")

    assert "#if os(tvOS)" in source
    assert "XCTAssertTrue(focusElement(usernameField), \"Username field should be focusable\")" in source
    assert "XCTAssertTrue(focusElement(passwordField), \"Password field should be focusable\")" in source
    assert "XCTAssertTrue(focusElement(signInButton), \"Sign-in button should be focusable\")" in source
    assert "private func focusElement(_ element: XCUIElement" in source
    assert "private func currentFocusedElement() -> XCUIElement?" in source
    assert "private func direction(from focusedFrame: CGRect, to targetFrame: CGRect)" in source


def test_debug_e2e_login_bootstrap_uses_launch_credentials() -> None:
    source = APP_STATE.read_text(encoding="utf-8")

    assert 'private static let e2eUsernameLaunchEnvironmentKey = "E2E_USERNAME"' in source
    assert 'private static let e2ePasswordLaunchEnvironmentKey = "E2E_PASSWORD"' in source
    assert 'private static let e2eAuthTokenLaunchEnvironmentKeys = ["E2E_AUTH_TOKEN", "EBOOKTOOLS_SESSION_TOKEN"]' in source
    assert "#if DEBUG\n        if await bootstrapE2ELoginIfNeeded()" in source
    assert "private func bootstrapE2ELoginIfNeeded() async -> Bool" in source
    assert "private static func e2eAuthToken(from environment: [String: String]) -> String?" in source
    assert "ProcessInfo.processInfo.environment" in source
    assert "APIClientConfiguration(apiBaseURL: apiBaseURL, authToken: authToken)" in source
    assert "client.fetchSessionStatus()" in source
    assert "client.login(username: username, password: password)" in source
    assert "updateSession(authenticated)" in source
    assert "lastUsername = username" in source


def test_debug_e2e_can_start_on_library_for_stable_tvos_journeys() -> None:
    source = LIBRARY_SHELL.read_text(encoding="utf-8")

    assert "@State private var activeSection: BrowseSection = Self.initialBrowseSection" in source
    assert "@State private var lastBrowseSection: BrowseSection = Self.initialBrowseSection" in source
    assert "private static var initialBrowseSection: BrowseSection" in source
    assert "#if DEBUG" in source
    assert 'ProcessInfo.processInfo.environment["E2E_START_BROWSE_SECTION"]' in source
    assert "BrowseSection.allCases.first" in source
    assert "return .jobs" in source
    assert "@State private var didOpenE2EMusicBedLibraryItem = false" in source
    assert "openFirstLibraryBookForMusicBedE2EIfNeeded()" in source
    assert 'ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1"' in source
    assert "selectLibraryItem(item, mode: .startOver)" in source


def test_journey_runner_can_tap_visible_but_not_hittable_ipad_controls() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "latestCandidate.exists && !latestCandidate.frame.isEmpty" in source
    assert "windowFrame.intersects(frame)" in source
    assert "coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()" in source
    assert "let identifierQueries: [XCUIElementQuery]" in source
    assert "app.buttons.matching(identifier: identifier)" in source
    assert "app.otherElements.matching(identifier: identifier)" in source


def test_journey_runner_can_drive_raw_ipad_arrow_keys() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert 'case "left", "leftarrow", "left_arrow":' in source
    assert "app.typeKey(.leftArrow, modifierFlags: [])" in source
    assert 'case "right", "rightarrow", "right_arrow":' in source
    assert "app.typeKey(.rightArrow, modifierFlags: [])" in source


def test_tvos_play_first_item_prefers_stable_row_identifiers() -> None:
    runner = JOURNEY_RUNNER.read_text(encoding="utf-8")
    library = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Library"
        / "LibraryView.swift"
    ).read_text(encoding="utf-8")
    jobs = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Features"
        / "Jobs"
        / "JobsView.swift"
    ).read_text(encoding="utf-8")

    assert '.accessibilityIdentifier("libraryRowButton")' in library
    assert '.accessibilityIdentifier("jobRowButton")' in jobs
    assert 'element(withIdentifier: "libraryRowButton")' in runner
    assert 'element(withIdentifier: "jobRowButton")' in runner
    assert "preferredRows.first" in runner
    assert 'NSPredicate(format: "label == %@", identifier)' in runner


def test_journey_runner_can_press_tvos_play_pause_remote_button() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "var button: String?" in source
    assert "var count: Int?" in source
    assert "var interval_ms: Int?" in source
    assert 'case "press_remote_button":' in source
    assert "doPressRemoteButton(step)" in source
    assert "let pressCount = max(step.count ?? 1, 1)" in source
    assert "let intervalMicroseconds = max(step.interval_ms ?? 0, 0) * 1_000" in source
    assert "for index in 0..<pressCount" in source
    assert "usleep(useconds_t(intervalMicroseconds))" in source
    assert "private func remoteButton(named name: String) -> XCUIRemote.Button?" in source
    assert 'case "playpause", "play_pause", "play-pause":' in source
    assert "return .playPause" in source


def test_journey_runner_uses_search_when_selecting_hidden_options() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert "var didSearch = false" in source
    assert "searchForOption(optionLabel)" in source
    assert "app.searchFields.firstMatch" in source
    assert "searchField.typeText(optionLabel)" in source
