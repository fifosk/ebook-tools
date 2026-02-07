import XCTest

#if !os(tvOS)
// These hardcoded tests use iOS-only .tap() and .coordinate() APIs.
// tvOS E2E tests run via the shared JourneyRunner instead.
final class PlaybackTests: InteractiveReaderUITests {

    func testStartBookPlaybackAndReturn() throws {
        loginIfNeeded()

        // Navigate to Jobs → Books
        let jobsButton = app.buttons["Jobs"]
        if jobsButton.waitForExistence(timeout: 5) {
            jobsButton.tap()
        }
        let booksButton = app.buttons["Books"]
        XCTAssertTrue(booksButton.waitForExistence(timeout: 5), "Books filter should exist")
        booksButton.tap()
        sleep(1)

        // Wait for at least one item
        let firstCell = app.cells.firstMatch
        guard firstCell.waitForExistence(timeout: 20) else {
            throw XCTSkip("No book jobs available to play")
        }
        takeScreenshot(named: "book_list")

        // Tap the first book job to open playback
        firstCell.tap()

        // Wait for the player or playback view to load
        let player = app.otherElements["interactivePlayerView"]
        if player.waitForExistence(timeout: 25) {
            takeScreenshot(named: "player_opened")
        } else {
            // Playback view may not have the accessibility id — still screenshot it
            sleep(2)
            takeScreenshot(named: "playback_view")
        }

        // Navigate back via left-edge swipe (nav bar is hidden in playback view)
        let window = app.windows.firstMatch
        let leftEdge = window.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.5))
        let center = window.coordinate(withNormalizedOffset: CGVector(dx: 0.7, dy: 0.5))
        leftEdge.press(forDuration: 0.1, thenDragTo: center)
        sleep(1)

        // Verify we're back on the library shell
        let library = app.otherElements["libraryShellView"]
        let backToMenu = library.waitForExistence(timeout: 10)
        takeScreenshot(named: "returned_to_menu")
        XCTAssertTrue(backToMenu, "Should return to library after dismissing player")
    }
}
#endif
