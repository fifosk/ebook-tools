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
        let oauthPath: String?
        let sessionPath: String
        let tokenTransport: String
    }

    struct ClientConfig: Decodable, Equatable {
        let apiBaseUrlEnvironment: [String]
        let credentialEnvironment: [String]?
        let sessionTokenStorage: String
        let legacyTokenMigration: String?
    }

    struct ApplePipelineContract: Decodable, Equatable {
        let manifestId: String
        let simulatorProfiles: [String]
        let deviceProfiles: [String]
    }

    struct CreationContract: Decodable, Equatable {
        let bookOptionsPath: String
        let bookJobsPath: String
        let pipelineFilesPath: String?
        let pipelineContentIndexPath: String?
        let pipelineUploadPath: String?
        let pipelineJobsPath: String?
        let pipelineIntakeStatusPath: String?
        let pipelineDefaultsPath: String?
        let pipelineLlmModelsPath: String?
        let pipelineSearchPath: String?
        let imageNodeAvailabilityPath: String?
        let audioVoicesPath: String?
        let subtitleSourcesPath: String?
        let subtitleDeleteSourcePath: String?
        let subtitleModelsPath: String?
        let subtitleJobsPath: String?
        let youtubeLibraryPath: String?
        let youtubeSubtitleStreamsPath: String?
        let youtubeExtractSubtitlesPath: String?
        let subtitleTvMetadataPreviewPath: String?
        let subtitleTvMetadataCacheClearPath: String?
        let youtubeMetadataPreviewPath: String?
        let youtubeMetadataCacheClearPath: String?
        let youtubeDubPath: String?
        let acquisitionProvidersPath: String?
        let acquisitionDiscoverPath: String?
        let acquisitionAcquirePath: String?
        let acquisitionArtifactPreparePathTemplate: String?
        let acquisitionJobsPath: String?
        let acquisitionJobPathTemplate: String?
        let templateListPath: String?
        let templatePathTemplate: String?
    }

    struct OfflineExportContract: Decodable, Equatable {
        let createPath: String
        let downloadPathTemplate: String
        let sourceKinds: [String]
        let playerTypes: [String]
    }

    struct LibraryActionsContract: Decodable, Equatable {
        let itemsPath: String
        let itemMetadataPathTemplate: String
        let sourceUploadPathTemplate: String
        let movePathTemplate: String
        let removePathTemplate: String
        let isbnLookupPath: String
        let isbnApplyPathTemplate: String
        let metadataEnrichPathTemplate: String
    }

    struct PlaybackStateContract: Decodable, Equatable {
        let bookmarksPathTemplate: String
        let bookmarkDeletePathTemplate: String
        let readingBedsPath: String?
        let resumeListPath: String
        let resumePathTemplate: String
        let resumeFilterQuery: String
    }

    struct NotificationsContract: Decodable, Equatable {
        let deviceRegistrationPath: String
        let deviceRemovalPathTemplate: String
        let testPath: String
        let richTestPath: String
        let preferencesPath: String
    }

    let status: String
    let app: String
    let service: String
    let version: String
    let healthPath: String
    let auth: AuthContract
    let clientConfig: ClientConfig
    let applePipeline: ApplePipelineContract?
    let creation: CreationContract?
    let offlineExports: OfflineExportContract?
    let libraryActions: LibraryActionsContract?
    let playbackState: PlaybackStateContract?
    let notifications: NotificationsContract?
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
