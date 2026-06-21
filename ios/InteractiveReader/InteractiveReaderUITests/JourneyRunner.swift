import XCTest

// MARK: - Journey data model

struct JourneyStep: Decodable {
    let action: String
    var tab: String?
    var filter: String?
    var screenshot: String?
    var skip_if_empty: Bool?
    var selector: String?
    var text: String?
    var timeout: Int?
    var ms: Int?
}

struct Journey: Decodable {
    let id: String
    let name: String
    let description: String
    let steps: [JourneyStep]
}

// MARK: - Platform detection

enum E2EPlatform: String {
    case iPhone
    case iPad
    case tvOS

    static var current: E2EPlatform {
        #if os(tvOS)
        return .tvOS
        #else
        if UIDevice.current.userInterfaceIdiom == .pad {
            return .iPad
        }
        return .iPhone
        #endif
    }
}

// MARK: - Journey runner

/// Interprets abstract journey steps against a running ``XCUIApplication``.
///
/// Platform-specific behaviour (gestures, element queries) is handled
/// internally so that the same JSON journey works on iPhone, iPad, and tvOS.
final class JourneyRunner {

    private let app: XCUIApplication
    private let test: InteractiveReaderUITests
    private let platform: E2EPlatform

    static var journeyPath: String {
        if let value = ProcessInfo.processInfo.environment["E2E_JOURNEY_PATH"], !value.isEmpty {
            return value
        }
        return "/tmp/apple-device-app-pipeline/ebook-tools/\(InteractiveReaderUITests.e2eProfileName)/ios_e2e_journey.json"
    }

    init(app: XCUIApplication, test: InteractiveReaderUITests) {
        self.app = app
        self.test = test
        self.platform = E2EPlatform.current
    }

    // MARK: - Loading

    static func loadJourney() throws -> Journey {
        let url = URL(fileURLWithPath: journeyPath)
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(Journey.self, from: data)
    }

    // MARK: - Execution

    func run(_ journey: Journey) throws {
        for step in journey.steps {
            try execute(step)
        }
    }

    private func execute(_ step: JourneyStep) throws {
        switch step.action {
        case "login":
            doLogin(step)
        case "navigate_tab":
            doNavigateTab(step)
        case "select_filter":
            doSelectFilter(step)
        case "play_first_item":
            try doPlayFirstItem(step)
        case "exercise_player_remote":
            doExercisePlayerRemote(step)
        case "go_back":
            doGoBack(step)
        case "assert_visible":
            doAssertVisible(step)
        case "enter_text":
            doEnterText(step)
        case "wait":
            doWait(step)
        default:
            XCTFail("Unknown journey action: \(step.action)")
        }

        if let name = step.screenshot {
            test.takeScreenshot(named: name)
        }
    }

    // MARK: - Step implementations

    private func doLogin(_ step: JourneyStep) {
        test.loginIfNeeded()
    }

    private func doNavigateTab(_ step: JourneyStep) {
        let tabName = step.tab ?? "Jobs"
        let button = tabButton(named: tabName, identifier: step.selector, timeout: 5)
        if button.waitForExistence(timeout: 5) {
            selectElement(button)
        }
        sleep(1)
    }

    private func doSelectFilter(_ step: JourneyStep) {
        let filterName = step.filter ?? "Books"
        let button = app.buttons[filterName]
        XCTAssertTrue(
            button.waitForExistence(timeout: 5),
            "\(filterName) filter should exist"
        )
        selectElement(button)
        sleep(1)
    }

    private func doPlayFirstItem(_ step: JourneyStep) throws {
        // Wait for at least one item to appear
        let firstItem: XCUIElement
        switch platform {
        case .tvOS:
            // On tvOS, list items are rendered as buttons
            firstItem = app.cells.firstMatch
            if !firstItem.waitForExistence(timeout: 5) {
                // Fallback: try buttons within the list
                let btn = app.buttons.element(boundBy: 2) // skip tab buttons
                guard btn.waitForExistence(timeout: 20) else {
                    if step.skip_if_empty == true {
                        throw XCTSkip("No items available to play")
                    }
                    XCTFail("No items found in list")
                    return
                }
                selectElement(btn)
                waitForPlayer()
                return
            }
        default:
            firstItem = app.cells.firstMatch
        }

        guard firstItem.waitForExistence(timeout: 20) else {
            if step.skip_if_empty == true {
                throw XCTSkip("No items available to play")
            }
            XCTFail("No items found in list")
            return
        }

        selectElement(firstItem)
        waitForPlayer()
    }

    private func waitForPlayer() {
        if waitForAnyPlayer(timeout: 25) != nil {
            return
        }

        // Allow some time for loading even without the accessibility ID.
        sleep(3)
    }

    private func waitForAnyPlayer(timeout: TimeInterval) -> XCUIElement? {
        let deadline = Date().addingTimeInterval(timeout)
        let candidates = [
            element(withIdentifier: "interactivePlayerView"),
            element(withIdentifier: "videoPlayerView"),
            element(withIdentifier: "libraryPlaybackView")
        ]

        while Date() < deadline {
            if let match = candidates.first(where: { $0.exists }) {
                return match
            }
            usleep(200_000)
        }

        return candidates.first(where: { $0.exists })
    }

    private func doExercisePlayerRemote(_ step: JourneyStep) {
        #if os(tvOS)
        guard let player = waitForAnyPlayer(timeout: TimeInterval(step.timeout ?? 10)) else {
            XCTFail("Expected an audio or video player before exercising tvOS remote")
            return
        }

        XCUIRemote.shared.press(.down)
        sleep(1)

        if element(withIdentifier: "videoPlayerView").exists {
            XCTAssertTrue(
                element(withIdentifier: "tvPlaybackControls").waitForExistence(timeout: 3),
                "Video player controls should appear after pressing Down on tvOS"
            )
        }

        XCUIRemote.shared.press(.left)
        XCUIRemote.shared.press(.right)
        XCUIRemote.shared.press(.up)
        XCTAssertTrue(player.exists, "Player should remain visible after remote navigation")
        #endif
    }

    private func doGoBack(_ step: JourneyStep) {
        #if os(tvOS)
        // Press Menu button on Siri Remote
        XCUIRemote.shared.press(.menu)
        #else
        // Edge swipe from left (nav bar is hidden in playback)
        edgeSwipeBack()
        #endif

        sleep(1)

        // Verify we returned to the library shell
        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(
            library.waitForExistence(timeout: 10),
            "Should return to library after dismissing player"
        )
    }

    private func doAssertVisible(_ step: JourneyStep) {
        guard let identifier = step.selector else { return }
        let timeout = TimeInterval(step.timeout ?? 10)
        let element = element(withIdentifier: identifier)
        XCTAssertTrue(
            element.waitForExistence(timeout: timeout),
            "\(identifier) should be visible"
        )
    }

    private func doEnterText(_ step: JourneyStep) {
        guard let identifier = step.selector else {
            XCTFail("enter_text requires selector")
            return
        }
        let text = step.text ?? ""
        let timeout = TimeInterval(step.timeout ?? 10)
        let element = element(withIdentifier: identifier)
        XCTAssertTrue(
            element.waitForExistence(timeout: timeout),
            "\(identifier) should be visible before entering text"
        )

        #if os(tvOS)
        if !element.hasFocus {
            XCTAssertTrue(focusElement(element), "\(identifier) should be focusable")
        }
        XCUIRemote.shared.press(.select)
        #else
        element.tap()
        #endif

        element.typeText(text)

        #if os(tvOS)
        XCUIRemote.shared.press(.menu)
        #else
        dismissKeyboardIfPresent()
        #endif
    }

    private func doWait(_ step: JourneyStep) {
        let seconds = UInt32(step.ms ?? 1000) / 1000
        sleep(max(seconds, 1))
    }

    // MARK: - Helpers

    private func element(withIdentifier identifier: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: identifier).firstMatch
    }

    private func tabButton(named name: String, identifier: String?, timeout: TimeInterval) -> XCUIElement {
        if let identifier {
            let identifiedButton = element(withIdentifier: identifier)
            if identifiedButton.waitForExistence(timeout: min(timeout, 2)) {
                return identifiedButton
            }
        }

        let predicate = NSPredicate(format: "label == %@", name)
        let segmentedButton = app.segmentedControls.buttons.matching(predicate).firstMatch
        if segmentedButton.waitForExistence(timeout: min(timeout, 2)) {
            return segmentedButton
        }
        return app.buttons.matching(predicate).firstMatch
    }

    /// Platform-safe element activation: `.tap()` on iOS, remote select on tvOS.
    private func selectElement(_ element: XCUIElement) {
        #if os(tvOS)
        guard focusElement(element) else {
            XCTFail("Could not move tvOS focus to \(element)")
            return
        }
        XCUIRemote.shared.press(.select)
        #else
        element.tap()
        #endif
    }

    #if os(tvOS)
    private func focusElement(_ element: XCUIElement, timeout: TimeInterval = 8) -> Bool {
        guard element.exists else { return false }
        if elementOrDescendantHasFocus(element) { return true }

        let deadline = Date().addingTimeInterval(timeout)

        while Date() < deadline {
            guard element.exists else { return false }
            if elementOrDescendantHasFocus(element) {
                return true
            }

            if let focused = currentFocusedElement() {
                XCUIRemote.shared.press(direction(from: focused.frame, to: element.frame))
            } else {
                XCUIRemote.shared.press(.right)
            }
            usleep(180_000)
        }

        return element.exists && elementOrDescendantHasFocus(element)
    }

    private func elementOrDescendantHasFocus(_ element: XCUIElement) -> Bool {
        if element.exists && element.hasFocus {
            return true
        }
        guard let focused = currentFocusedElement() else { return false }
        let targetFrame = element.frame
        let focusedCenter = CGPoint(x: focused.frame.midX, y: focused.frame.midY)
        return targetFrame.contains(focusedCenter)
    }

    private func currentFocusedElement() -> XCUIElement? {
        let candidates =
            app.buttons.allElementsBoundByIndex
            + app.cells.allElementsBoundByIndex
            + app.textFields.allElementsBoundByIndex
            + app.secureTextFields.allElementsBoundByIndex

        return candidates.first { candidate in
            candidate.exists && candidate.hasFocus
        }
    }

    private func direction(from focusedFrame: CGRect, to targetFrame: CGRect) -> XCUIRemote.Button {
        let dx = targetFrame.midX - focusedFrame.midX
        let dy = targetFrame.midY - focusedFrame.midY

        if abs(dy) > 80 {
            return dy > 0 ? .down : .up
        }
        if abs(dx) > 20 {
            return dx > 0 ? .right : .left
        }
        return .right
    }
    #endif

    // MARK: - Gestures

    #if !os(tvOS)
    private func edgeSwipeBack() {
        let window = app.windows.firstMatch
        let leftEdge = window.coordinate(
            withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5)
        )
        let center = window.coordinate(
            withNormalizedOffset: CGVector(dx: 0.7, dy: 0.5)
        )
        leftEdge.press(forDuration: 0.1, thenDragTo: center)
    }

    private func dismissKeyboardIfPresent() {
        let keyboard = app.keyboards.firstMatch
        guard keyboard.waitForExistence(timeout: 1) else { return }

        for label in ["Search", "Done", "Return"] {
            let button = keyboard.buttons[label]
            if button.exists && button.isHittable {
                button.tap()
                return
            }
        }

        app.windows.firstMatch.coordinate(
            withNormalizedOffset: CGVector(dx: 0.95, dy: 0.08)
        ).tap()
    }
    #endif
}
