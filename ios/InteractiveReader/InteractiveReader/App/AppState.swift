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
    @Published private(set) var isRestoring: Bool = false

    var apiBaseURL: URL? {
        URL(string: apiBaseURLString.trimmingCharacters(in: .whitespacesAndNewlines))
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

    func updateSession(_ session: SessionStatusResponse) {
        storedToken = session.token
        self.session = session
    }

    func signOut() {
        storedToken = ""
        session = nil
    }

    func restoreSessionIfNeeded() async {
        guard session == nil else { return }
        guard let apiBaseURL, let token = authToken else { return }
        isRestoring = true
        defer { isRestoring = false }
        do {
            let client = APIClient(configuration: APIClientConfiguration(apiBaseURL: apiBaseURL, authToken: token))
            let restored = try await client.fetchSessionStatus()
            session = restored
        } catch {
            signOut()
        }
    }
}
