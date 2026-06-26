import Foundation

enum AppleAuthRuntimeContract {
    static let loginPath = "/api/auth/login"
    static let oauthPath = "/api/auth/oauth"
    static let sessionPath = "/api/auth/session"
    static let runtimeDescriptorPath = "/api/system/runtime"
}

extension APIClient {
    func login(username: String, password: String) async throws -> SessionStatusResponse {
        let payload = LoginRequestPayload(username: username, password: password)
        let data = try await sendJSONRequest(path: AppleAuthRuntimeContract.loginPath, method: "POST", payload: payload)
        return try decode(SessionStatusResponse.self, from: data)
    }

    func loginWithOAuth(
        provider: String,
        idToken: String,
        email: String?,
        firstName: String?,
        lastName: String?
    ) async throws -> SessionStatusResponse {
        let payload = OAuthLoginRequestPayload(
            provider: provider,
            idToken: idToken,
            email: email,
            firstName: firstName,
            lastName: lastName
        )
        let data = try await sendJSONRequest(path: AppleAuthRuntimeContract.oauthPath, method: "POST", payload: payload)
        return try decode(SessionStatusResponse.self, from: data)
    }

    func fetchSessionStatus() async throws -> SessionStatusResponse {
        let data = try await sendRequest(path: AppleAuthRuntimeContract.sessionPath)
        return try decode(SessionStatusResponse.self, from: data)
    }

    func fetchBackendRuntimeDescriptor() async throws -> BackendRuntimeDescriptorResponse {
        let data = try await sendRequest(path: AppleAuthRuntimeContract.runtimeDescriptorPath)
        return try decode(BackendRuntimeDescriptorResponse.self, from: data)
    }
}
