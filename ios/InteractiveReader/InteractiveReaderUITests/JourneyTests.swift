import XCTest

/// Runs shared JSON user-journey definitions on the current platform.
///
/// The journey file is written by the Makefile and passed through
/// ``E2E_JOURNEY_PATH`` before test execution. Each abstract step (login,
/// navigate, play, etc.) is interpreted by ``JourneyRunner`` with
/// platform-specific behaviour for iPhone, iPad, and tvOS.
final class JourneyTests: InteractiveReaderUITests {

    func testJourney() throws {
        let journey = try JourneyRunner.loadJourney()
        let runner = JourneyRunner(app: app, test: self)
        try runner.run(journey)
    }
}
