import XCTest
#if canImport(UIKit)
import UIKit
#endif

/// Base class for all InteractiveReader UI tests.
///
/// Launches the app with E2E credentials read from a JSON config file
/// written by the Makefile before test execution.
///
/// Config file location: ``E2E_CONFIG_PATH`` or
/// ``/tmp/apple-device-app-pipeline/ebook-tools/<profile>/ios_e2e_config.json``.
/// Expected format: ``{"username":"...","password":"...","api_base_url":"..."}``
class InteractiveReaderUITests: XCTestCase {
    var app: XCUIApplication!

    static var configPath: String {
        if let value = ProcessInfo.processInfo.environment["E2E_CONFIG_PATH"], !value.isEmpty {
            return value
        }
        return "/tmp/apple-device-app-pipeline/ebook-tools/\(e2eProfileName)/ios_e2e_config.json"
    }

    static var e2eProfileName: String {
        #if os(tvOS)
        return "tvos"
        #else
        if UIDevice.current.userInterfaceIdiom == .pad {
            return "ipados"
        }
        return "iphone"
        #endif
    }

    struct E2EConfig: Decodable {
        let username: String
        let password: String
        let api_base_url: String
    }

    private struct E2EJourneyIdentity: Decodable {
        let id: String
    }

    /// Loaded once per test; available to helpers via ``config``.
    private(set) var config: E2EConfig!

    private func loadConfig() throws -> E2EConfig {
        let url = URL(fileURLWithPath: Self.configPath)
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(E2EConfig.self, from: data)
    }

    private func loadJourneyID() -> String? {
        let url = URL(fileURLWithPath: JourneyRunner.journeyPath)
        guard let data = try? Data(contentsOf: url),
              let journey = try? JSONDecoder().decode(E2EJourneyIdentity.self, from: data)
        else {
            return nil
        }
        return journey.id
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
        config = try loadConfig()
        app = XCUIApplication()

        app.launchEnvironment["E2E_USERNAME"] = config.username
        app.launchEnvironment["E2E_PASSWORD"] = config.password
        app.launchEnvironment["E2E_API_BASE_URL"] = config.api_base_url
        app.launchEnvironment["E2E_DISABLE_SESSION_RESTORE"] = "1"
        let journeyID = loadJourneyID()
        if ProcessInfo.processInfo.environment["E2E_MUSIC_BED_SYNC_TEST"] == "1" ||
            journeyID == "music_bed_sync" {
            app.launchEnvironment["E2E_MUSIC_BED_SYNC_TEST"] = "1"
        }
        if journeyID == "music_bed_sync" {
            app.launchEnvironment["E2E_START_BROWSE_SECTION"] = "Library"
        } else if let startSection = ProcessInfo.processInfo.environment["E2E_START_BROWSE_SECTION"],
           !startSection.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            app.launchEnvironment["E2E_START_BROWSE_SECTION"] = startSection
        }

        app.launch()
    }

    override func tearDownWithError() throws {
        takeScreenshot(named: "teardown")
    }
}
