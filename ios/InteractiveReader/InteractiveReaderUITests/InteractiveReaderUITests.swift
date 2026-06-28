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
/// Expected format: ``{"username":"...","password":"...","auth_token":"...","api_base_url":"..."}``
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
        let profile: String?
        let username: String
        let password: String
        let auth_token: String?
        let api_base_url: String
        let allow_restored_session: Bool?
    }

    private struct E2EJourneyIdentity: Decodable {
        let id: String
    }

    var allowsRestoredSession: Bool {
        if config?.allow_restored_session == true {
            return true
        }
        let value = ProcessInfo.processInfo.environment["E2E_ALLOW_RESTORED_SESSION"]?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        return ["1", "true", "yes", "on"].contains(value)
    }

    var e2eProfileLabel: String {
        let value = config?.profile?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return value.isEmpty ? Self.e2eProfileName : value
    }

    var hasConfiguredE2EAuthToken: Bool {
        let value = config?.auth_token?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return !value.isEmpty
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
        if let authToken = config.auth_token?.trimmingCharacters(in: .whitespacesAndNewlines),
           !authToken.isEmpty {
            app.launchEnvironment["E2E_AUTH_TOKEN"] = authToken
        }
        app.launchEnvironment["E2E_API_BASE_URL"] = config.api_base_url
        if allowsRestoredSession {
            app.launchEnvironment["E2E_ALLOW_RESTORED_SESSION"] = "1"
        } else {
            app.launchEnvironment["E2E_DISABLE_SESSION_RESTORE"] = "1"
        }
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
