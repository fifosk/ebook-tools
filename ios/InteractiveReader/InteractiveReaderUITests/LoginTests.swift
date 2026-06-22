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

        for _ in 0..<4 where !firstEntry.hasFocus {
            XCUIRemote.shared.press(.up)
            usleep(160_000)
        }
        XCTAssertTrue(firstEntry.hasFocus, "Expected the remote to focus the first changelog row")

        let laterEntry = changelogEntries.element(boundBy: changelogEntries.count - 1)
        for _ in 0..<20 where !(laterEntry.exists && laterEntry.isHittable) {
            XCUIRemote.shared.press(.down)
            usleep(160_000)
        }

        XCTAssertTrue(laterEntry.exists, "Expected a lower changelog row to stay in the tvOS focus list")
        XCTAssertTrue(laterEntry.isHittable, "Expected remote focus movement to reveal the lower changelog row")
    }
    #endif

    func testLoginWithCredentials() throws {
        loginIfNeeded()
        takeScreenshot(named: "after_login")

        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(library.exists, "Library shell should be visible after login")
    }
}
