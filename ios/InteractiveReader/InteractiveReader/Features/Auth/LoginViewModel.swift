import AuthenticationServices
import Foundation

@MainActor
final class LoginViewModel: ObservableObject {
    @Published var username: String
    @Published var password: String = ""
    @Published var errorMessage: String?
    @Published var isLoading = false

    init(username: String = "") {
        self.username = username
    }

    func signIn(using appState: AppState) async {
        guard let apiBaseURL = appState.apiBaseURL else {
            errorMessage = "Enter a valid API base URL."
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
            errorMessage = "Enter a valid API base URL."
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
}
