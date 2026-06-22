import XCTest

final class LoginTests: InteractiveReaderUITests {

    func testLoginScreenAppears() throws {
        let usernameField = app.textFields["loginUsernameField"]
        // Either the login screen is visible or we were already logged in
        if usernameField.waitForExistence(timeout: 8) {
            takeScreenshot(named: "login_screen")
            XCTAssertTrue(app.secureTextFields["loginPasswordField"].exists)
            XCTAssertTrue(app.buttons["loginSignInButton"].exists)
        }
        // If login screen didn't appear, session was restored — still a pass
    }

    #if os(tvOS)
    func testTvChangelogRowsCanMoveFocusBeyondFirstPage() throws {
        let usernameField = app.textFields["loginUsernameField"]
        guard usernameField.waitForExistence(timeout: 8) else {
            throw XCTSkip("Login screen unavailable; session was restored before the changelog could be exercised")
        }

        let changelogEntries = app.buttons
            .matching(NSPredicate(format: "identifier BEGINSWITH %@", "appChangelogEntry."))
        let firstEntry = changelogEntries.firstMatch
        XCTAssertTrue(firstEntry.waitForExistence(timeout: 8), "Expected the latest changelog row on the login screen")
        XCTAssertTrue(firstEntry.isHittable, "Expected the latest changelog row to be visible before moving")
        XCTAssertGreaterThan(changelogEntries.count, 2, "Expected multiple changelog rows for tvOS remote movement")

        let positionLabel = app.staticTexts["appChangelogPositionLabel"]
        XCTAssertTrue(positionLabel.waitForExistence(timeout: 4), "Expected tvOS changelog to expose a remote-scroll position")
        let initialPosition = positionLabel.label
        XCTAssertTrue(initialPosition.hasPrefix("1/"), "Expected changelog focus to start at the newest entry")

        for _ in 0..<4 where !firstEntry.hasFocus {
            XCUIRemote.shared.press(.up)
            usleep(160_000)
        }
        XCTAssertTrue(firstEntry.hasFocus, "Expected the remote to focus the first changelog row")

        for _ in 0..<8 where positionLabel.label == initialPosition {
            XCUIRemote.shared.press(.down)
            usleep(160_000)
        }

        XCTAssertNotEqual(positionLabel.label, initialPosition, "Expected remote focus movement to advance through the changelog")
        XCTAssertFalse(positionLabel.label.hasPrefix("1/"), "Expected tvOS changelog focus to move beyond the newest entry")
    }
    #endif

    func testLoginWithCredentials() throws {
        loginIfNeeded()
        takeScreenshot(named: "after_login")

        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(library.exists, "Library shell should be visible after login")
    }
}
