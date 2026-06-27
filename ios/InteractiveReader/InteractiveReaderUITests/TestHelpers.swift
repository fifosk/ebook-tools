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
            XCTFail("E2E credentials are empty in \(Self.configPath)")
            return
        }

        #if os(tvOS)
        // On tvOS: press Select to open keyboard, type, then navigate fields.
        XCTAssertTrue(focusElement(usernameField), "Username field should be focusable")
        XCUIRemote.shared.press(.select)  // activate keyboard for username
        sleep(1)
        clearTextField(usernameField)
        usernameField.typeText(username)

        // Dismiss keyboard by pressing Menu, then swipe down to password
        XCUIRemote.shared.press(.menu)
        sleep(1)

        let passwordField = app.secureTextFields["loginPasswordField"]
        XCTAssertTrue(passwordField.waitForExistence(timeout: 3),
                      "Password field not found")

        XCTAssertTrue(focusElement(passwordField), "Password field should be focusable")
        sleep(1)
        XCUIRemote.shared.press(.select) // activate keyboard for password
        sleep(1)
        clearTextField(passwordField)
        passwordField.typeText(password)

        // Dismiss keyboard and press sign-in
        XCUIRemote.shared.press(.menu)
        sleep(1)
        let signInButton = app.buttons["loginSignInButton"]
        XCTAssertTrue(signInButton.waitForExistence(timeout: 3), "Sign-in button not found")
        XCTAssertTrue(focusElement(signInButton), "Sign-in button should be focusable")
        sleep(1)
        XCUIRemote.shared.press(.select) // press sign-in
        #else
        usernameField.tap()
        clearTextField(usernameField)
        usernameField.typeText(username)

        let passwordField = app.secureTextFields["loginPasswordField"]
        XCTAssertTrue(passwordField.waitForExistence(timeout: 3),
                      "Password field not found")
        passwordField.tap()
        clearTextField(passwordField)
        passwordField.typeText(password)

        app.buttons["loginSignInButton"].tap()
        #endif

        // Wait for the library to appear (long timeout for network login)
        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(library.waitForExistence(timeout: 20),
                      "Library did not appear after login")
    }

    private func clearTextField(_ element: XCUIElement) {
        guard let value = element.value as? String, !value.isEmpty else { return }
        let deleteText = String(repeating: XCUIKeyboardKey.delete.rawValue, count: value.count)
        element.typeText(deleteText)
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

    /// Capture a screenshot and attach it to the test's xcresult bundle.
    func takeScreenshot(named name: String) {
        let screenshot = app.windows.firstMatch.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
