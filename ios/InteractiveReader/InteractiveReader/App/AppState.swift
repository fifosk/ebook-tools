import SwiftUI

@MainActor
final class AppState: ObservableObject {
    #if os(tvOS)
    @AppStorage("apiBaseURL") var apiBaseURLString: String = "https://api.langtools.fifosk.synology.me"
    #else
    @AppStorage("apiBaseURL") var apiBaseURLString: String = "https://api.langtools.fifosk.synology.me"
    #endif
    @AppStorage("lastUsername") var lastUsername: String = ""

    private let sessionTokenStore: SessionTokenStore
    private static let apiBaseURLLaunchEnvironmentKeys = [
        "INTERACTIVE_READER_API_BASE_URL",
        "EBOOK_TOOLS_API_BASE_URL",
        "E2E_API_BASE_URL"
    ]
    private static let disableSessionRestoreLaunchEnvironmentKey = "E2E_DISABLE_SESSION_RESTORE"
    @Published private var storedToken: String = ""
    @Published private(set) var session: SessionStatusResponse?
    /// Whether we're actively validating a stored session token
    /// This is a brief operation so startup can fall back to login quickly.
    @Published private(set) var isRestoring: Bool = false
    @Published var playerKeyboardShortcutsActive: Bool = false

    init(sessionTokenStore: SessionTokenStore = .shared) {
        self.sessionTokenStore = sessionTokenStore
        if Self.disablesSessionRestoreForE2E {
            sessionTokenStore.deleteToken()
            self.storedToken = ""
        } else {
            self.storedToken = sessionTokenStore.loadToken() ?? ""
        }
    }

    var apiBaseURL: URL? {
        for key in Self.apiBaseURLLaunchEnvironmentKeys {
            let value = ProcessInfo.processInfo.environment[key]?
                .trimmingCharacters(in: .whitespacesAndNewlines)
            if let value, !value.isEmpty {
                return URL(string: value)
            }
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
        sessionTokenStore.saveToken(session.token)
        self.session = session
        syncResumeStoreConfiguration()
    }

    func signOut() {
        storedToken = ""
        sessionTokenStore.deleteToken()
        session = nil
        PlaybackResumeStore.shared.configureAPI(nil)
    }

    func restoreSessionIfNeeded() async {
        guard !Self.disablesSessionRestoreForE2E else {
            signOut()
            return
        }
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
        } catch APIClientError.httpError(let statusCode, _) where statusCode == 401 || statusCode == 403 {
            signOut()
        } catch {
            // Preserve the stored token on transient connectivity/server errors.
            // The login screen still appears, but a later launch can restore without forcing re-entry.
        }
    }

    private func syncResumeStoreConfiguration() {
        PlaybackResumeStore.shared.configureAPI(configuration)
    }

    private static var disablesSessionRestoreForE2E: Bool {
        #if DEBUG
        let value = ProcessInfo.processInfo.environment[disableSessionRestoreLaunchEnvironmentKey]?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
        return ["1", "true", "yes"].contains(value)
        #else
        return false
        #endif
    }
}
