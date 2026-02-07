import XCTest

// MARK: - Journey data model

struct JourneyStep: Decodable {
    let action: String
    var tab: String?
    var filter: String?
    var screenshot: String?
    var skip_if_empty: Bool?
    var selector: String?
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

    static let journeyPath = "/tmp/ios_e2e_journey.json"

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
        case "go_back":
            doGoBack(step)
        case "assert_visible":
            doAssertVisible(step)
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
        let button = app.buttons[tabName]
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
        let player = app.otherElements["interactivePlayerView"]
        if player.waitForExistence(timeout: 25) {
            // Player loaded successfully
        } else {
            // Allow some time for loading even without the accessibility ID
            sleep(3)
        }
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
        let element = app.otherElements[identifier]
        XCTAssertTrue(
            element.waitForExistence(timeout: timeout),
            "\(identifier) should be visible"
        )
    }

    private func doWait(_ step: JourneyStep) {
        let seconds = UInt32(step.ms ?? 1000) / 1000
        sleep(max(seconds, 1))
    }

    // MARK: - Helpers

    /// Platform-safe element activation: `.tap()` on iOS, remote select on tvOS.
    private func selectElement(_ element: XCUIElement) {
        #if os(tvOS)
        XCUIRemote.shared.press(.select)
        #else
        element.tap()
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
    #endif
}
