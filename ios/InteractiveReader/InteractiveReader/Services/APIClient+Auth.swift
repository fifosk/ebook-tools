import Foundation

extension APIClient {
    func login(username: String, password: String) async throws -> SessionStatusResponse {
        let payload = LoginRequestPayload(username: username, password: password)
        let data = try await sendJSONRequest(path: "/api/auth/login", method: "POST", payload: payload)
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
        let data = try await sendJSONRequest(path: "/api/auth/oauth", method: "POST", payload: payload)
        return try decode(SessionStatusResponse.self, from: data)
    }

    func fetchSessionStatus() async throws -> SessionStatusResponse {
        let data = try await sendRequest(path: "/api/auth/session")
        return try decode(SessionStatusResponse.self, from: data)
    }

    func fetchBackendRuntimeDescriptor() async throws -> BackendRuntimeDescriptorResponse {
        let data = try await sendRequest(path: "/api/system/runtime")
        return try decode(BackendRuntimeDescriptorResponse.self, from: data)
    }
}
