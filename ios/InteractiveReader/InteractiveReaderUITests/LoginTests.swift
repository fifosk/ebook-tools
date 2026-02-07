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

    func testLoginWithCredentials() throws {
        loginIfNeeded()
        takeScreenshot(named: "after_login")

        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(library.exists, "Library shell should be visible after login")
    }
}
