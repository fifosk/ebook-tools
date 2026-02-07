import XCTest

final class LibraryTests: InteractiveReaderUITests {

    func testLibraryLoads() throws {
        loginIfNeeded()

        let library = app.otherElements["libraryShellView"]
        XCTAssertTrue(library.waitForExistence(timeout: 15),
                      "Library shell should be visible")
        takeScreenshot(named: "library_loaded")
    }

    func testLibraryHasItems() throws {
        loginIfNeeded()

        // Wait for at least one cell/row to appear (jobs or library items)
        let firstCell = app.cells.firstMatch
        XCTAssertTrue(firstCell.waitForExistence(timeout: 20),
                      "At least one list item should appear")
        takeScreenshot(named: "library_with_items")
    }
}
