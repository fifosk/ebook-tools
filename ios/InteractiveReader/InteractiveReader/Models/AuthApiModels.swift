struct SessionUserPayload: Decodable, Equatable {
    let username: String
    let role: String
    let email: String?
    let firstName: String?
    let lastName: String?
    let lastLogin: String?
}

struct SessionStatusResponse: Decodable, Equatable {
    let token: String
    let user: SessionUserPayload
}

struct BackendRuntimeDescriptorResponse: Decodable, Equatable {
    struct AuthContract: Decodable, Equatable {
        let loginPath: String
        let sessionPath: String
        let tokenTransport: String
    }

    struct ClientConfig: Decodable, Equatable {
        let apiBaseUrlEnvironment: [String]
        let sessionTokenStorage: String
    }

    let status: String
    let app: String
    let service: String
    let version: String
    let healthPath: String
    let auth: AuthContract
    let clientConfig: ClientConfig
}

struct LoginRequestPayload: Encodable {
    let username: String
    let password: String
}

struct OAuthLoginRequestPayload: Encodable {
    let provider: String
    let idToken: String
    let email: String?
    let firstName: String?
    let lastName: String?

    enum CodingKeys: String, CodingKey {
        case provider
        case idToken = "id_token"
        case email
        case firstName = "first_name"
        case lastName = "last_name"
    }
}
