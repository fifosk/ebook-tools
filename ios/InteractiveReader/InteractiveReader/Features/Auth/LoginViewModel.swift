import AuthenticationServices
import Foundation

@MainActor
final class LoginViewModel: ObservableObject {
    @Published var username: String
    @Published var password: String = ""
    @Published var errorMessage: String?
    @Published var isLoading = false
    @Published var serverStatus: LoginServerStatus = .checking

    init(username: String = "") {
        self.username = username
    }

    func refreshServerStatus(using appState: AppState) async {
        guard let apiBaseURL = appState.apiBaseURL else {
            serverStatus = .offline
            return
        }

        // Skip health check on simulators/debug builds to speed up development
        // The login attempt itself will reveal if the server is reachable
        #if DEBUG
        serverStatus = .online
        return
        #else
        serverStatus = .checking
        let healthURL = makeHealthURL(from: apiBaseURL)

        // Use a very short timeout for health check - it should be fast
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 3
        config.timeoutIntervalForResource = 5
        let quickSession = URLSession(configuration: config)

        var request = URLRequest(url: healthURL)
        request.timeoutInterval = 3

        do {
            let (_, response) = try await quickSession.data(for: request)
            if let httpResponse = response as? HTTPURLResponse,
               (200...299).contains(httpResponse.statusCode) {
                serverStatus = .online
            } else {
                serverStatus = .offline
            }
        } catch {
            serverStatus = .offline
        }
        #endif
    }

    func signIn(using appState: AppState) async {
        guard let apiBaseURL = appState.apiBaseURL else {
            errorMessage = "API server is unavailable."
            return
        }
        let trimmedUser = username.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPass = password.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedUser.isEmpty, !trimmedPass.isEmpty else {
            errorMessage = "Username and password are required."
            return
        }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let client = APIClient(configuration: APIClientConfiguration(apiBaseURL: apiBaseURL))
            let session = try await client.login(username: trimmedUser, password: trimmedPass)
            appState.lastUsername = trimmedUser
            appState.updateSession(session)
            password = ""
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func signInWithApple(credential: ASAuthorizationAppleIDCredential, using appState: AppState) async {
        guard let apiBaseURL = appState.apiBaseURL else {
            errorMessage = "API server is unavailable."
            return
        }
        guard let tokenData = credential.identityToken,
              let token = String(data: tokenData, encoding: .utf8),
              !token.isEmpty else {
            errorMessage = "Apple sign-in did not return a token."
            return
        }

        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        let email = credential.email?.trimmingCharacters(in: .whitespacesAndNewlines)
        let firstName = credential.fullName?.givenName?.trimmingCharacters(in: .whitespacesAndNewlines)
        let lastName = credential.fullName?.familyName?.trimmingCharacters(in: .whitespacesAndNewlines)

        do {
            let client = APIClient(configuration: APIClientConfiguration(apiBaseURL: apiBaseURL))
            let session = try await client.loginWithOAuth(
                provider: "apple",
                idToken: token,
                email: email?.nonEmptyValue,
                firstName: firstName?.nonEmptyValue,
                lastName: lastName?.nonEmptyValue
            )
            if let emailValue = email?.nonEmptyValue {
                appState.lastUsername = emailValue
            }
            appState.updateSession(session)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func makeHealthURL(from baseURL: URL) -> URL {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            return baseURL.appendingPathComponent("_health")
        }
        let trimmedPath = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = trimmedPath.isEmpty ? "/_health" : "/\(trimmedPath)/_health"
        return components.url ?? baseURL.appendingPathComponent("_health")
    }
}
