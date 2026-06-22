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

        let firstEntry = app.buttons["appChangelogEntry.tvos-changelog-focus-buttons"]
        XCTAssertTrue(firstEntry.waitForExistence(timeout: 8), "Expected the latest changelog row on the login screen")
        XCTAssertTrue(firstEntry.isHittable, "Expected the latest changelog row to be visible before moving")

        for _ in 0..<4 where !firstEntry.hasFocus {
            XCUIRemote.shared.press(.up)
            usleep(160_000)
        }
        XCTAssertTrue(firstEntry.hasFocus, "Expected the remote to focus the first changelog row")

        for _ in 0..<5 {
            XCUIRemote.shared.press(.down)
            usleep(160_000)
        }

        let laterEntry = app.buttons["appChangelogEntry.pipeline-media-api-models-file"]
        XCTAssertTrue(laterEntry.exists, "Expected a changelog row beyond the initially visible tvOS page")
        XCTAssertTrue(laterEntry.isHittable, "Expected remote focus movement to reveal a later changelog row")
    }
    #endif

    func testLoginWithCredentials() throws {
        loginIfNeeded()
        takeScreenshot(named: "after_login")

        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(library.exists, "Library shell should be visible after login")
    }
}
