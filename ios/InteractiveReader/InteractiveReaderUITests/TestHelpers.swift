import XCTest

extension InteractiveReaderUITests {

    /// Log in via the UI if the login screen is visible.  No-op if already
    /// past the login screen (session restored).
    func loginIfNeeded() {
        let usernameField = app.textFields["loginUsernameField"]

        // If the login view doesn't appear within 5 s we're already logged in.
        guard usernameField.waitForExistence(timeout: 5) else { return }

        let username = config.username
        let password = config.password
        guard !username.isEmpty, !password.isEmpty else {
            XCTFail("E2E credentials are empty in /tmp/ios_e2e_config.json")
            return
        }

        usernameField.tap()
        usernameField.typeText(username)

        let passwordField = app.secureTextFields["loginPasswordField"]
        XCTAssertTrue(passwordField.waitForExistence(timeout: 3),
                      "Password field not found")
        passwordField.tap()
        passwordField.typeText(password)

        app.buttons["loginSignInButton"].tap()

        // Wait for the library to appear (long timeout for network login)
        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(library.waitForExistence(timeout: 20),
                      "Library did not appear after login")
    }

    /// Capture a screenshot and attach it to the test's xcresult bundle.
    func takeScreenshot(named name: String) {
        let screenshot = app.windows.firstMatch.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
