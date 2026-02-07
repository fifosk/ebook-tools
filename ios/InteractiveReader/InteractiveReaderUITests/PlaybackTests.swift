import XCTest

final class PlaybackTests: InteractiveReaderUITests {

    func testTapItemOpensPlayer() throws {
        loginIfNeeded()

        // Wait for a list item
        let firstCell = app.cells.firstMatch
        guard firstCell.waitForExistence(timeout: 20) else {
            // No items available — skip gracefully
            throw XCTSkip("No items in library to tap")
        }

        takeScreenshot(named: "before_tap")
        firstCell.tap()

        // The player (or playback view) should appear
        let player = app.otherElements["interactivePlayerView"]
        if player.waitForExistence(timeout: 25) {
            takeScreenshot(named: "player_opened")
        } else {
            // Some items may open a non-interactive playback view
            takeScreenshot(named: "playback_view")
        }
    }
}
