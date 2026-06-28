import XCTest

// MARK: - Journey data model

struct JourneyStep: Decodable {
    let action: String
    var tab: String?
    var filter: String?
    var screenshot: String?
    var skip_if_empty: Bool?
    var selector: String?
    var unless_visible: String?
    var text: String?
    var button: String?
    var placeholder: String?
    var timeout: Int?
    var ms: Int?
    var count: Int?
    var interval_ms: Int?
    var min_width: Double?
    var min_height: Double?
    var max_width: Double?
    var max_height: Double?
    var min_aspect_ratio: Double?
    var max_aspect_ratio: Double?
    var platforms: [String]?
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
        guard shouldRun(step) else {
            return
        }

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
        case "press_remote_button":
            doPressRemoteButton(step)
        case "go_back":
            doGoBack(step)
        case "assert_visible":
            doAssertVisible(step)
        case "assert_frame":
            doAssertFrame(step)
        case "tap":
            doTap(step)
        case "enter_text":
            doEnterText(step)
        case "select_option":
            doSelectOption(step)
        case "assert_non_empty_value":
            try doAssertNonEmptyValue(step)
        case "assert_value_contains":
            doAssertValueContains(step)
        case "wait":
            doWait(step)
        default:
            XCTFail("Unknown journey action: \(step.action)")
        }

        if let name = step.screenshot {
            test.takeScreenshot(named: name)
        }
    }

    private func shouldRun(_ step: JourneyStep) -> Bool {
        guard let platforms = step.platforms, !platforms.isEmpty else {
            return true
        }
        let current = platform.rawValue.lowercased()
        return platforms.contains { candidate in
            candidate.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == current
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
        if let unlessIdentifier = step.unless_visible?.trimmingCharacters(in: .whitespacesAndNewlines),
           !unlessIdentifier.isEmpty {
            let unlessElement = element(withIdentifier: unlessIdentifier)
            scrollElementIntoView(unlessElement, timeout: 2)
            if unlessElement.exists && !unlessElement.frame.isEmpty {
                waitForPlayer()
                return
            }
        }

        // Wait for at least one item to appear
        let firstItem: XCUIElement
        switch platform {
        case .tvOS:
            let preferredRows = [
                element(withIdentifier: "libraryRowButton"),
                element(withIdentifier: "jobRowButton")
            ]
            if let row = preferredRows.first(where: { $0.waitForExistence(timeout: 5) }) {
                selectElement(row)
                waitForPlayer()
                return
            }
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
            let preferredRows = [
                element(withIdentifier: "libraryRowButton"),
                element(withIdentifier: "jobRowButton")
            ]
            if let row = preferredRows.first(where: { $0.waitForExistence(timeout: 5) }) {
                selectElement(row)
                waitForPlayer()
                return
            }
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

    private func doPressRemoteButton(_ step: JourneyStep) {
        #if os(tvOS)
        let rawButton = (step.button ?? step.text ?? "select")
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        guard let button = remoteButton(named: rawButton) else {
            XCTFail("Unsupported tvOS remote button: \(rawButton)")
            return
        }
        let pressCount = max(step.count ?? 1, 1)
        let intervalMicroseconds = max(step.interval_ms ?? 0, 0) * 1_000
        for index in 0..<pressCount {
            XCUIRemote.shared.press(button)
            if index < pressCount - 1, intervalMicroseconds > 0 {
                usleep(useconds_t(intervalMicroseconds))
            }
        }
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
        scrollElementIntoView(element, timeout: min(timeout, 4))
        XCTAssertTrue(
            element.waitForExistence(timeout: timeout),
            "\(identifier) should be visible"
        )
    }

    private func doAssertFrame(_ step: JourneyStep) {
        guard let identifier = step.selector else {
            XCTFail("assert_frame requires selector")
            return
        }
        let timeout = TimeInterval(step.timeout ?? 10)
        let element = element(withIdentifier: identifier)
        XCTAssertTrue(
            element.waitForExistence(timeout: timeout),
            "\(identifier) should exist before frame assertion"
        )

        let frame = element.frame
        XCTAssertFalse(frame.isEmpty, "\(identifier) should have a non-empty frame")

        if let minWidth = step.min_width {
            XCTAssertGreaterThanOrEqual(
                frame.width,
                CGFloat(minWidth),
                "\(identifier) width \(frame.width) should be >= \(minWidth)"
            )
        }
        if let minHeight = step.min_height {
            XCTAssertGreaterThanOrEqual(
                frame.height,
                CGFloat(minHeight),
                "\(identifier) height \(frame.height) should be >= \(minHeight)"
            )
        }
        if let maxWidth = step.max_width {
            XCTAssertLessThanOrEqual(
                frame.width,
                CGFloat(maxWidth),
                "\(identifier) width \(frame.width) should be <= \(maxWidth)"
            )
        }
        if let maxHeight = step.max_height {
            XCTAssertLessThanOrEqual(
                frame.height,
                CGFloat(maxHeight),
                "\(identifier) height \(frame.height) should be <= \(maxHeight)"
            )
        }

        guard frame.height > 0 else { return }
        let aspectRatio = Double(frame.width / frame.height)
        if let minAspectRatio = step.min_aspect_ratio {
            XCTAssertGreaterThanOrEqual(
                aspectRatio,
                minAspectRatio,
                "\(identifier) aspect ratio \(aspectRatio) should be >= \(minAspectRatio)"
            )
        }
        if let maxAspectRatio = step.max_aspect_ratio {
            XCTAssertLessThanOrEqual(
                aspectRatio,
                maxAspectRatio,
                "\(identifier) aspect ratio \(aspectRatio) should be <= \(maxAspectRatio)"
            )
        }
    }

    private func doTap(_ step: JourneyStep) {
        guard let identifier = step.selector else {
            XCTFail("tap requires selector")
            return
        }
        let timeout = TimeInterval(step.timeout ?? 10)

        if let unlessIdentifier = step.unless_visible?.trimmingCharacters(in: .whitespacesAndNewlines),
           !unlessIdentifier.isEmpty {
            let unlessElement = element(withIdentifier: unlessIdentifier)
            scrollElementIntoView(unlessElement, timeout: min(timeout, 2))
            if unlessElement.exists && !unlessElement.frame.isEmpty {
                return
            }
        }

        let element = element(withIdentifier: identifier)
        scrollElementIntoView(element, timeout: min(timeout, 4))
        XCTAssertTrue(
            element.waitForExistence(timeout: timeout),
            "\(identifier) should be visible before tapping"
        )
        selectElement(element)
    }

    private func doEnterText(_ step: JourneyStep) {
        guard let identifier = step.selector else {
            XCTFail("enter_text requires selector")
            return
        }
        let text = step.text ?? ""
        let timeout = TimeInterval(step.timeout ?? 10)
        let element = element(withIdentifier: identifier)
        scrollElementIntoView(element, timeout: min(timeout, 4))
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

    private func doSelectOption(_ step: JourneyStep) {
        guard let identifier = step.selector else {
            XCTFail("select_option requires selector")
            return
        }
        guard let optionLabel = step.text?.trimmingCharacters(in: .whitespacesAndNewlines),
              !optionLabel.isEmpty else {
            XCTFail("select_option requires text")
            return
        }

        let timeout = TimeInterval(step.timeout ?? 10)
        let container = element(withIdentifier: identifier)
        scrollElementIntoView(container, timeout: min(timeout, 4))
        XCTAssertTrue(
            container.waitForExistence(timeout: timeout),
            "\(identifier) should be visible before selecting \(optionLabel)"
        )

        let option = waitForOption(label: optionLabel, in: container, timeout: timeout)
        guard option.waitForExistence(timeout: 1) else {
            XCTFail("\(optionLabel) option should exist in \(identifier)")
            return
        }
        scrollElementIntoView(option, timeout: min(timeout, 4))
        selectElement(option)
        sleep(1)
    }

    private func doAssertNonEmptyValue(_ step: JourneyStep) throws {
        guard let identifier = step.selector else {
            XCTFail("assert_non_empty_value requires selector")
            return
        }
        let timeout = TimeInterval(step.timeout ?? 10)
        let deadline = Date().addingTimeInterval(timeout)
        let element = element(withIdentifier: identifier)
        var latestValue = ""

        while Date() < deadline {
            if element.exists {
                latestValue = normalizedValue(for: element)
                if isMeaningfulValue(latestValue, placeholder: step.placeholder) {
                    return
                }
            }
            usleep(200_000)
        }

        if step.skip_if_empty == true {
            throw XCTSkip("\(identifier) did not receive a non-empty value")
        }
        XCTFail("\(identifier) should have a non-empty value; latest value was \(latestValue)")
    }

    private func doAssertValueContains(_ step: JourneyStep) {
        guard let identifier = step.selector else {
            XCTFail("assert_value_contains requires selector")
            return
        }
        guard let expectedText = step.text?.trimmingCharacters(in: .whitespacesAndNewlines),
              !expectedText.isEmpty else {
            XCTFail("assert_value_contains requires text")
            return
        }

        let timeout = TimeInterval(step.timeout ?? 10)
        let deadline = Date().addingTimeInterval(timeout)
        let element = element(withIdentifier: identifier)
        var latestValue = ""

        while Date() < deadline {
            if !element.exists {
                scrollElementIntoView(element, timeout: 1)
            }
            if element.exists {
                latestValue = normalizedValue(for: element)
                if latestValue.localizedCaseInsensitiveContains(expectedText) {
                    return
                }
            }
            usleep(200_000)
        }

        XCTFail("\(identifier) value should contain \(expectedText); latest value was \(latestValue)")
    }

    private func doWait(_ step: JourneyStep) {
        let seconds = UInt32(step.ms ?? 1000) / 1000
        sleep(max(seconds, 1))
    }

    // MARK: - Helpers

    private func element(withIdentifier identifier: String) -> XCUIElement {
        let identifierQueries: [XCUIElementQuery] = [
            app.buttons.matching(identifier: identifier),
            app.otherElements.matching(identifier: identifier),
            app.staticTexts.matching(identifier: identifier),
            app.textFields.matching(identifier: identifier),
            app.secureTextFields.matching(identifier: identifier)
        ]
        for query in identifierQueries {
            let element = query.firstMatch
            if element.exists {
                return element
            }
        }
        let identified = app.descendants(matching: .any).matching(identifier: identifier).firstMatch
        if identified.exists {
            return identified
        }
        let labelPredicate = NSPredicate(format: "label == %@", identifier)
        let labelQueries: [XCUIElementQuery] = [
            app.buttons.matching(labelPredicate),
            app.otherElements.matching(labelPredicate),
            app.staticTexts.matching(labelPredicate)
        ]
        for query in labelQueries {
            let element = query.firstMatch
            if element.exists {
                return element
            }
        }
        return app.descendants(matching: .any).matching(labelPredicate).firstMatch
    }

    private func normalizedValue(for element: XCUIElement) -> String {
        if let value = element.value as? String {
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                return trimmed
            }
        }
        return element.label.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func isMeaningfulValue(_ value: String, placeholder: String?) -> Bool {
        let normalized = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty else { return false }
        if let placeholder = placeholder?.trimmingCharacters(in: .whitespacesAndNewlines),
           !placeholder.isEmpty,
           normalized == placeholder {
            return false
        }
        return true
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

    private func waitForOption(
        label optionLabel: String,
        in container: XCUIElement,
        timeout: TimeInterval
    ) -> XCUIElement {
        let deadline = Date().addingTimeInterval(timeout)
        var didOpenContainer = false
        var didSearch = false
        var latestCandidate = optionElement(label: optionLabel, in: container)

        while Date() < deadline {
            latestCandidate = optionElement(label: optionLabel, in: container)
            if latestCandidate.exists && latestCandidate.isHittable {
                return latestCandidate
            }
            if latestCandidate.exists && !latestCandidate.frame.isEmpty {
                return latestCandidate
            }

            if !didOpenContainer {
                selectElement(container)
                didOpenContainer = true
            } else if !didSearch && searchForOption(optionLabel) {
                didSearch = true
            } else {
                scrollForward()
            }
            usleep(200_000)
        }

        return latestCandidate
    }

    private func optionElement(label optionLabel: String, in container: XCUIElement) -> XCUIElement {
        let predicate = NSPredicate(format: "label == %@", optionLabel)
        let scopedButton = container.descendants(matching: .button).matching(predicate).firstMatch
        if scopedButton.exists {
            return scopedButton
        }
        let globalButton = app.buttons.matching(predicate).firstMatch
        if globalButton.exists {
            return globalButton
        }
        let scopedStaticText = container.descendants(matching: .staticText).matching(predicate).firstMatch
        if scopedStaticText.exists {
            return scopedStaticText
        }
        let globalStaticText = app.staticTexts.matching(predicate).firstMatch
        if globalStaticText.exists {
            return globalStaticText
        }
        return globalButton
    }

    private func searchForOption(_ optionLabel: String) -> Bool {
        #if os(tvOS)
        return false
        #else
        let searchField = app.searchFields.firstMatch
        guard searchField.waitForExistence(timeout: 1) else { return false }
        selectElement(searchField)
        clearTextInput(searchField)
        searchField.typeText(optionLabel)
        dismissKeyboardIfPresent()
        return true
        #endif
    }

    #if !os(tvOS)
    private func clearTextInput(_ element: XCUIElement) {
        guard let value = element.value as? String, !value.isEmpty else { return }
        let deleteText = String(repeating: XCUIKeyboardKey.delete.rawValue, count: value.count)
        element.typeText(deleteText)
    }
    #endif

    /// Platform-safe element activation: `.tap()` on iOS, remote select on tvOS.
    private func selectElement(_ element: XCUIElement) {
        #if os(tvOS)
        if focusElement(element) {
            XCUIRemote.shared.press(.select)
            return
        }
        XCTFail("Could not move tvOS focus to \(element)")
        return
        #else
        if element.isHittable {
            element.tap()
            return
        }

        let frame = element.frame
        let windowFrame = app.windows.firstMatch.frame
        if !frame.isEmpty && windowFrame.intersects(frame) {
            element.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
            return
        }

        XCTFail("Could not tap \(element)")
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
            + app.staticTexts.allElementsBoundByIndex
            + app.otherElements.allElementsBoundByIndex

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

    private func remoteButton(named name: String) -> XCUIRemote.Button? {
        switch name {
        case "up":
            return .up
        case "down":
            return .down
        case "left":
            return .left
        case "right":
            return .right
        case "select":
            return .select
        case "menu", "back":
            return .menu
        case "playpause", "play_pause", "play-pause":
            return .playPause
        default:
            return nil
        }
    }
    #endif

    private func scrollElementIntoView(_ element: XCUIElement, timeout: TimeInterval) {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            guard element.exists else {
                scrollForward()
                usleep(200_000)
                continue
            }
            #if os(tvOS)
            if focusElement(element, timeout: 1) {
                return
            }
            #else
            if element.isHittable {
                return
            }
            #endif
            scrollForward()
            usleep(200_000)
        }
    }

    private func scrollForward() {
        #if os(tvOS)
        XCUIRemote.shared.press(.down)
        #else
        app.swipeUp()
        #endif
    }

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
