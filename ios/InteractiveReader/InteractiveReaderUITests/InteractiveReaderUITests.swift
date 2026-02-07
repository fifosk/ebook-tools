import XCTest

/// Base class for all InteractiveReader UI tests.
///
/// Launches the app with E2E credentials read from a JSON config file
/// written by the Makefile before test execution.
///
/// Config file location: ``/tmp/ios_e2e_config.json``
/// Expected format: ``{"username":"...","password":"...","api_base_url":"..."}``
class InteractiveReaderUITests: XCTestCase {
    var app: XCUIApplication!

    private static let configPath = "/tmp/ios_e2e_config.json"

    struct E2EConfig: Decodable {
        let username: String
        let password: String
        let api_base_url: String
    }

    /// Loaded once per test; available to helpers via ``config``.
    private(set) var config: E2EConfig!

    private func loadConfig() throws -> E2EConfig {
        let url = URL(fileURLWithPath: Self.configPath)
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(E2EConfig.self, from: data)
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
        config = try loadConfig()
        app = XCUIApplication()

        app.launchEnvironment["E2E_USERNAME"] = config.username
        app.launchEnvironment["E2E_PASSWORD"] = config.password
        app.launchEnvironment["E2E_API_BASE_URL"] = config.api_base_url

        app.launch()
    }

    override func tearDownWithError() throws {
        takeScreenshot(named: "teardown")
    }
}
