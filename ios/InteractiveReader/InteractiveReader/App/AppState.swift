import SwiftUI

@MainActor
final class AppState: ObservableObject {
    #if os(tvOS)
    @AppStorage("apiBaseURL") var apiBaseURLString: String = "https://api.langtools.fifosk.synology.me"
    #else
    @AppStorage("apiBaseURL") var apiBaseURLString: String = "https://api.langtools.fifosk.synology.me"
    #endif
    @AppStorage("authToken") private var storedToken: String = ""
    @AppStorage("lastUsername") var lastUsername: String = ""

    @Published private(set) var session: SessionStatusResponse?
    /// Whether we're actively validating a stored session token
    /// This is now a brief operation (5s timeout) instead of blocking for 60s
    @Published private(set) var isRestoring: Bool = false

    var apiBaseURL: URL? {
        // Allow XCUITest to override the API URL via launch environment
        if let testURL = ProcessInfo.processInfo.environment["E2E_API_BASE_URL"],
           !testURL.isEmpty {
            return URL(string: testURL)
        }
        return URL(string: apiBaseURLString.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    var authToken: String? {
        storedToken.nonEmptyValue
    }

    var configuration: APIClientConfiguration? {
        guard let apiBaseURL else { return nil }
        return APIClientConfiguration(
            apiBaseURL: apiBaseURL,
            storageBaseURL: nil,
            authToken: authToken,
            userID: session?.user.username,
            userRole: session?.user.role
        )
    }

    var resumeUserKey: String? {
        let raw = session?.user.email?.nonEmptyValue
            ?? session?.user.username.nonEmptyValue
        return raw?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .nonEmptyValue
    }

    var resumeUserAliases: [String] {
        var aliases: [String] = []
        if let email = session?.user.email?.nonEmptyValue {
            aliases.append(email)
        }
        if let username = session?.user.username.nonEmptyValue {
            aliases.append(username)
        }
        return aliases
    }

    func updateSession(_ session: SessionStatusResponse) {
        storedToken = session.token
        self.session = session
        syncResumeStoreConfiguration()
    }

    func signOut() {
        storedToken = ""
        session = nil
        PlaybackResumeStore.shared.configureAPI(nil)
    }

    func restoreSessionIfNeeded() async {
        guard session == nil else { return }
        guard let apiBaseURL, let token = authToken else { return }

        #if DEBUG
        // In debug builds, use very aggressive timeout (2 seconds)
        // If server isn't reachable quickly, just show login screen
        let requestTimeout: TimeInterval = 2
        let resourceTimeout: TimeInterval = 4
        #else
        // In release builds, use slightly longer but still reasonable timeout
        let requestTimeout: TimeInterval = 5
        let resourceTimeout: TimeInterval = 8
        #endif

        isRestoring = true
        defer { isRestoring = false }

        // Use a dedicated URLSession with a short timeout for session restore
        let sessionConfig = URLSessionConfiguration.default
        sessionConfig.timeoutIntervalForRequest = requestTimeout
        sessionConfig.timeoutIntervalForResource = resourceTimeout
        let quickSession = URLSession(configuration: sessionConfig)

        do {
            let client = APIClient(
                configuration: APIClientConfiguration(apiBaseURL: apiBaseURL, authToken: token),
                urlSession: quickSession
            )
            let restored = try await client.fetchSessionStatus()
            session = restored
            syncResumeStoreConfiguration()
        } catch {
            // On timeout or error, sign out so user can re-authenticate
            signOut()
        }
    }

    private func syncResumeStoreConfiguration() {
        PlaybackResumeStore.shared.configureAPI(configuration)
    }
}
