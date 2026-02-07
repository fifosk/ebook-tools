import XCTest

#if !os(tvOS)
// These hardcoded tests use iOS-only .tap() APIs.
// tvOS E2E tests run via the shared JourneyRunner instead.
final class LibraryTests: InteractiveReaderUITests {

    // MARK: - Jobs tab — browse all 3 sub-types

    func testBrowseJobsAllTypes() throws {
        loginIfNeeded()

        // Ensure we're on the Jobs tab (default after login)
        let jobsButton = app.buttons["Jobs"]
        if jobsButton.waitForExistence(timeout: 5) {
            jobsButton.tap()
        }

        // Video (default sub-tab)
        let videoButton = app.buttons["Video"]
        if videoButton.waitForExistence(timeout: 5) {
            videoButton.tap()
        }
        sleep(1)
        takeScreenshot(named: "jobs_video")

        // Books
        let booksButton = app.buttons["Books"]
        XCTAssertTrue(booksButton.waitForExistence(timeout: 5), "Books filter should exist")
        booksButton.tap()
        sleep(1)
        takeScreenshot(named: "jobs_books")

        // Subtitles
        let subtitlesButton = app.buttons["Subtitles"]
        XCTAssertTrue(subtitlesButton.waitForExistence(timeout: 5), "Subtitles filter should exist")
        subtitlesButton.tap()
        sleep(1)
        takeScreenshot(named: "jobs_subtitles")
    }

    // MARK: - Library tab — browse all 3 sub-types

    func testBrowseLibraryAllTypes() throws {
        loginIfNeeded()

        // Switch to Library tab
        let libraryButton = app.buttons["Library"]
        XCTAssertTrue(libraryButton.waitForExistence(timeout: 5), "Library tab should exist")
        libraryButton.tap()
        sleep(1)

        // Video (default sub-tab)
        let videoButton = app.buttons["Video"]
        if videoButton.waitForExistence(timeout: 5) {
            videoButton.tap()
        }
        sleep(1)
        takeScreenshot(named: "library_video")

        // Books
        let booksButton = app.buttons["Books"]
        XCTAssertTrue(booksButton.waitForExistence(timeout: 5), "Books filter should exist")
        booksButton.tap()
        sleep(1)
        takeScreenshot(named: "library_books")

        // Subtitles
        let subtitlesButton = app.buttons["Subtitles"]
        XCTAssertTrue(subtitlesButton.waitForExistence(timeout: 5), "Subtitles filter should exist")
        subtitlesButton.tap()
        sleep(1)
        takeScreenshot(named: "library_subtitles")
    }
}
#endif
