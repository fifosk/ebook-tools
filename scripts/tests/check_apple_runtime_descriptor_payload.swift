import Foundation

@main
struct AppleRuntimeDescriptorPayloadCheck {
    static func main() throws {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        let currentRuntimeJSON = """
        {
          "status": "ok",
          "app": "ebook-tools",
          "service": "ebook-tools-api",
          "version": "test-version",
          "healthPath": "/_health",
          "auth": {
            "loginPath": "/api/auth/login",
            "oauthPath": "/api/auth/oauth",
            "sessionPath": "/api/auth/session",
            "logoutPath": "/api/auth/logout",
            "passwordPath": "/api/auth/password",
            "registerPath": "/api/auth/register",
            "tokenTransport": "Authorization: Bearer"
          },
          "clientConfig": {
            "apiBaseUrlEnvironment": [
              "INTERACTIVE_READER_API_BASE_URL",
              "EBOOK_TOOLS_API_BASE_URL",
              "E2E_API_BASE_URL"
            ],
            "credentialEnvironment": ["E2E_USERNAME", "E2E_PASSWORD", "E2E_AUTH_TOKEN", "EBOOKTOOLS_SESSION_TOKEN"],
            "sessionTokenStorage": "device-keychain",
            "legacyTokenMigration": "userdefaults-authToken"
          },
          "applePipeline": {
            "manifestId": "ebook-tools",
            "simulatorProfiles": ["ios", "ipados", "tvos", "tvos-cinema"],
            "deviceProfiles": ["iphone", "ipad", "appletv", "cinema"]
          },
          "creation": {
            "bookOptionsPath": "/api/books/options",
            "bookJobsPath": "/api/books/jobs",
            "pipelineFilesPath": "/api/pipelines/files",
            "pipelineFilesMinLimit": 1,
            "pipelineFilesDefaultLimit": 200,
            "pipelineFilesMaxLimit": 500,
            "pipelineContentIndexPath": "/api/pipelines/files/content-index",
            "pipelineUploadPath": "/api/pipelines/files/upload",
            "pipelineJobsPath": "/api/pipelines",
            "pipelineIntakeStatusPath": "/api/pipelines/intake/status",
            "pipelineDefaultsPath": "/api/pipelines/defaults",
            "pipelineLlmModelsPath": "/api/pipelines/llm-models",
            "pipelineSearchPath": "/api/pipelines/search",
            "imageNodeAvailabilityPath": "/api/pipelines/image-nodes/availability",
            "audioVoicesPath": "/api/audio/voices",
            "subtitleSourcesPath": "/api/subtitles/sources",
            "subtitleDeleteSourcePath": "/api/subtitles/delete-source",
            "subtitleModelsPath": "/api/subtitles/models",
            "subtitleJobsPath": "/api/subtitles/jobs",
            "youtubeLibraryPath": "/api/subtitles/youtube/library",
            "youtubeSubtitlesPath": "/api/subtitles/youtube/subtitles",
            "youtubeSubtitleDownloadPath": "/api/subtitles/youtube/download",
            "youtubeVideoDownloadPath": "/api/subtitles/youtube/video",
            "youtubeSubtitleStreamsPath": "/api/subtitles/youtube/subtitle-streams",
            "youtubeExtractSubtitlesPath": "/api/subtitles/youtube/extract-subtitles",
            "youtubeSubtitleDeletePath": "/api/subtitles/youtube/delete-subtitle",
            "youtubeVideoDeletePath": "/api/subtitles/youtube/delete-video",
            "subtitleTvMetadataPreviewPath": "/api/subtitles/metadata/tv/lookup",
            "subtitleTvMetadataCacheClearPath": "/api/subtitles/metadata/tv/cache/clear",
            "youtubeMetadataPreviewPath": "/api/subtitles/metadata/youtube/lookup",
            "youtubeMetadataCacheClearPath": "/api/subtitles/metadata/youtube/cache/clear",
            "youtubeDubPath": "/api/subtitles/youtube/dub",
            "acquisitionProvidersPath": "/api/acquisition/providers",
            "acquisitionDiscoverPath": "/api/acquisition/discover",
            "acquisitionAcquirePath": "/api/acquisition/acquire",
            "acquisitionArtifactPreparePathTemplate": "/api/acquisition/artifacts/{artifact_id}/prepare",
            "acquisitionJobsPath": "/api/acquisition/jobs",
            "acquisitionJobPathTemplate": "/api/acquisition/jobs/{task_id}",
            "templateListPath": "/api/creation/templates",
            "templatePathTemplate": "/api/creation/templates/{template_id}"
          },
          "offlineExports": {
            "createPath": "/api/exports",
            "downloadPathTemplate": "/api/exports/{export_id}/download",
            "sourceKinds": ["job", "library"],
            "playerTypes": ["interactive-text"]
          },
          "pipelineJobs": {
            "listPath": "/api/pipelines/jobs",
            "statusPathTemplate": "/api/pipelines/{job_id}",
            "eventStreamPathTemplate": "/api/pipelines/{job_id}/events",
            "deletePathTemplate": "/api/pipelines/jobs/{job_id}/delete",
            "restartPathTemplate": "/api/pipelines/jobs/{job_id}/restart",
            "cacheBusterQuery": "ts"
          },
          "pipelineMedia": {
            "jobMediaPathTemplate": "/api/pipelines/jobs/{job_id}/media",
            "jobMediaLivePathTemplate": "/api/pipelines/jobs/{job_id}/media/live",
            "jobMediaChunkPathTemplate": "/api/pipelines/jobs/{job_id}/media/chunks/{chunk_id}",
            "libraryMediaPathTemplate": "/api/library/media/{job_id}",
            "libraryMediaFilePathTemplate": "/api/library/media/{job_id}/file/{file_path}",
            "jobTimingPathTemplate": "/api/jobs/{job_id}/timing",
            "subtitleTvMetadataPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/tv",
            "subtitleTvMetadataLookupPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/tv/lookup",
            "youtubeVideoMetadataPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/youtube",
            "youtubeVideoMetadataLookupPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/youtube/lookup",
            "subtitleJobResultPathTemplate": "/api/subtitles/jobs/{job_id}/result",
            "chunkOrdering": "sentenceRange"
          },
          "linguist": {
            "assistantLookupPath": "/api/assistant/lookup",
            "lookupCachePathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache",
            "lookupCacheWordPathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache/{word}",
            "lookupCacheBulkPathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache/bulk",
            "lookupCacheSummaryPathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache/summary",
            "audioSynthesisPath": "/api/audio"
          },
          "libraryActions": {
            "itemsPath": "/api/library/items",
            "itemMetadataPathTemplate": "/api/library/items/{job_id}",
            "sourceUploadPathTemplate": "/api/library/items/{job_id}/upload-source",
            "movePathTemplate": "/api/library/move/{job_id}",
            "removePathTemplate": "/api/library/remove/{job_id}",
            "isbnLookupPath": "/api/library/isbn/lookup",
            "isbnApplyPathTemplate": "/api/library/items/{job_id}/isbn",
            "metadataEnrichPathTemplate": "/api/library/items/{job_id}/enrich"
          },
          "playbackState": {
            "bookmarksPathTemplate": "/api/bookmarks/{job_id}",
            "bookmarkDeletePathTemplate": "/api/bookmarks/{job_id}/{bookmark_id}",
            "readingBedsPath": "/api/reading-beds",
            "resumeListPath": "/api/resume",
            "resumePathTemplate": "/api/resume/{job_id}",
            "resumeFilterQuery": "job_id"
          },
          "notifications": {
            "deviceRegistrationPath": "/api/notifications/devices",
            "deviceRemovalPathTemplate": "/api/notifications/devices/{device_id}",
            "testPath": "/api/notifications/test",
            "richTestPath": "/api/notifications/test/rich",
            "preferencesPath": "/api/notifications/preferences"
          }
        }
        """.data(using: .utf8)!

        let current = try decoder.decode(BackendRuntimeDescriptorResponse.self, from: currentRuntimeJSON)
        require(
            current.auth.loginPath == "/api/auth/login",
            "Apple runtime descriptor should decode login endpoint"
        )
        require(
            current.auth.sessionPath == "/api/auth/session",
            "Apple runtime descriptor should decode session endpoint"
        )
        require(
            current.auth.logoutPath == "/api/auth/logout",
            "Apple runtime descriptor should decode logout endpoint"
        )
        require(
            current.auth.passwordPath == "/api/auth/password",
            "Apple runtime descriptor should decode password endpoint"
        )
        require(
            current.auth.registerPath == "/api/auth/register",
            "Apple runtime descriptor should decode registration endpoint"
        )
        require(
            current.auth.tokenTransport == "Authorization: Bearer",
            "Apple runtime descriptor should decode token transport"
        )
        require(current.applePipeline?.manifestId == "ebook-tools", "Apple runtime descriptor should decode pipeline manifest id")
        require(
            current.applePipeline?.simulatorProfiles == ["ios", "ipados", "tvos", "tvos-cinema"],
            "Apple runtime descriptor should decode simulator profiles exactly"
        )
        require(
            current.applePipeline?.deviceProfiles == ["iphone", "ipad", "appletv", "cinema"],
            "Apple runtime descriptor should decode device profiles exactly"
        )
        require(
            current.clientConfig.apiBaseUrlEnvironment == ["INTERACTIVE_READER_API_BASE_URL", "EBOOK_TOOLS_API_BASE_URL", "E2E_API_BASE_URL"],
            "Apple runtime descriptor should decode API base URL environment names exactly"
        )
        require(
            current.clientConfig.credentialEnvironment == ["E2E_USERNAME", "E2E_PASSWORD", "E2E_AUTH_TOKEN", "EBOOKTOOLS_SESSION_TOKEN"],
            "Apple runtime descriptor should decode public credential environment names exactly"
        )
        require(
            current.clientConfig.sessionTokenStorage == "device-keychain",
            "Apple runtime descriptor should decode session token storage"
        )
        require(
            current.clientConfig.legacyTokenMigration == "userdefaults-authToken",
            "Apple runtime descriptor should decode legacy token migration"
        )
        require(
            current.auth.oauthPath == "/api/auth/oauth",
            "Apple runtime descriptor should decode OAuth endpoint"
        )
        require(
            current.creation?.bookOptionsPath == "/api/books/options",
            "Apple runtime descriptor should decode Create options endpoint"
        )
        require(
            current.creation?.bookJobsPath == "/api/books/jobs",
            "Apple runtime descriptor should decode Create jobs endpoint"
        )
        require(
            current.creation?.pipelineFilesPath == "/api/pipelines/files",
            "Apple runtime descriptor should decode pipeline source browser endpoint"
        )
        require(
            current.creation?.pipelineFilesMinLimit == 1,
            "Apple runtime descriptor should decode pipeline source browser min limit"
        )
        require(
            current.creation?.pipelineFilesDefaultLimit == 200,
            "Apple runtime descriptor should decode pipeline source browser default limit"
        )
        require(
            current.creation?.pipelineFilesMaxLimit == 500,
            "Apple runtime descriptor should decode pipeline source browser max limit"
        )
        require(
            current.creation?.pipelineContentIndexPath == "/api/pipelines/files/content-index",
            "Apple runtime descriptor should decode pipeline content-index endpoint"
        )
        require(
            current.creation?.pipelineUploadPath == "/api/pipelines/files/upload",
            "Apple runtime descriptor should decode pipeline upload endpoint"
        )
        require(
            current.creation?.pipelineJobsPath == "/api/pipelines",
            "Apple runtime descriptor should decode pipeline creation endpoint"
        )
        require(
            current.creation?.pipelineIntakeStatusPath == "/api/pipelines/intake/status",
            "Apple runtime descriptor should decode pipeline intake-status endpoint"
        )
        require(
            current.creation?.pipelineDefaultsPath == "/api/pipelines/defaults",
            "Apple runtime descriptor should decode pipeline defaults endpoint"
        )
        require(
            current.creation?.pipelineLlmModelsPath == "/api/pipelines/llm-models",
            "Apple runtime descriptor should decode pipeline LLM models endpoint"
        )
        require(
            current.creation?.pipelineSearchPath == "/api/pipelines/search",
            "Apple runtime descriptor should decode pipeline media-search endpoint"
        )
        require(
            current.creation?.imageNodeAvailabilityPath == "/api/pipelines/image-nodes/availability",
            "Apple runtime descriptor should decode image-node availability endpoint"
        )
        require(
            current.creation?.audioVoicesPath == "/api/audio/voices",
            "Apple runtime descriptor should decode audio voices endpoint"
        )
        require(
            current.creation?.subtitleSourcesPath == "/api/subtitles/sources",
            "Apple runtime descriptor should decode subtitle source picker endpoint"
        )
        require(
            current.creation?.subtitleModelsPath == "/api/subtitles/models",
            "Apple runtime descriptor should decode subtitle model inventory endpoint"
        )
        require(
            current.creation?.subtitleJobsPath == "/api/subtitles/jobs",
            "Apple runtime descriptor should decode subtitle jobs endpoint"
        )
        require(
            current.creation?.subtitleDeleteSourcePath == "/api/subtitles/delete-source",
            "Apple runtime descriptor should decode subtitle cleanup endpoint"
        )
        require(
            current.creation?.youtubeDubPath == "/api/subtitles/youtube/dub",
            "Apple runtime descriptor should decode YouTube dubbing endpoint"
        )
        require(
            current.creation?.youtubeLibraryPath == "/api/subtitles/youtube/library",
            "Apple runtime descriptor should decode YouTube NAS library endpoint"
        )
        require(
            current.creation?.youtubeSubtitlesPath == "/api/subtitles/youtube/subtitles",
            "Apple runtime descriptor should decode YouTube subtitle-track endpoint"
        )
        require(
            current.creation?.youtubeSubtitleDownloadPath == "/api/subtitles/youtube/download",
            "Apple runtime descriptor should decode YouTube subtitle download endpoint"
        )
        require(
            current.creation?.youtubeVideoDownloadPath == "/api/subtitles/youtube/video",
            "Apple runtime descriptor should decode YouTube video download endpoint"
        )
        require(
            current.creation?.youtubeSubtitleStreamsPath == "/api/subtitles/youtube/subtitle-streams",
            "Apple runtime descriptor should decode YouTube subtitle-stream endpoint"
        )
        require(
            current.creation?.youtubeExtractSubtitlesPath == "/api/subtitles/youtube/extract-subtitles",
            "Apple runtime descriptor should decode YouTube subtitle extraction endpoint"
        )
        require(
            current.creation?.youtubeSubtitleDeletePath == "/api/subtitles/youtube/delete-subtitle",
            "Apple runtime descriptor should decode YouTube subtitle delete endpoint"
        )
        require(
            current.creation?.youtubeVideoDeletePath == "/api/subtitles/youtube/delete-video",
            "Apple runtime descriptor should decode YouTube video delete endpoint"
        )
        require(
            current.creation?.subtitleTvMetadataPreviewPath == "/api/subtitles/metadata/tv/lookup",
            "Apple runtime descriptor should decode subtitle TV metadata lookup endpoint"
        )
        require(
            current.creation?.subtitleTvMetadataCacheClearPath == "/api/subtitles/metadata/tv/cache/clear",
            "Apple runtime descriptor should decode subtitle TV metadata cache-clear endpoint"
        )
        require(
            current.creation?.youtubeMetadataPreviewPath == "/api/subtitles/metadata/youtube/lookup",
            "Apple runtime descriptor should decode YouTube metadata lookup endpoint"
        )
        require(
            current.creation?.youtubeMetadataCacheClearPath == "/api/subtitles/metadata/youtube/cache/clear",
            "Apple runtime descriptor should decode YouTube metadata cache-clear endpoint"
        )
        require(
            current.creation?.acquisitionProvidersPath == "/api/acquisition/providers",
            "Apple runtime descriptor should decode acquisition provider registry endpoint"
        )
        require(
            current.creation?.acquisitionDiscoverPath == "/api/acquisition/discover",
            "Apple runtime descriptor should decode acquisition discovery endpoint"
        )
        require(
            current.creation?.acquisitionAcquirePath == "/api/acquisition/acquire",
            "Apple runtime descriptor should decode acquisition reviewed acquire endpoint"
        )
        require(
            current.creation?.acquisitionArtifactPreparePathTemplate == "/api/acquisition/artifacts/{artifact_id}/prepare",
            "Apple runtime descriptor should decode acquisition artifact-prepare endpoint template"
        )
        require(
            current.creation?.acquisitionJobsPath == "/api/acquisition/jobs",
            "Apple runtime descriptor should decode acquisition jobs endpoint"
        )
        require(
            current.creation?.acquisitionJobPathTemplate == "/api/acquisition/jobs/{task_id}",
            "Apple runtime descriptor should decode acquisition job status endpoint template"
        )
        require(
            current.creation?.templateListPath == "/api/creation/templates",
            "Apple runtime descriptor should decode creation template list endpoint"
        )
        require(
            current.creation?.templatePathTemplate == "/api/creation/templates/{template_id}",
            "Apple runtime descriptor should decode creation template detail endpoint template"
        )
        require(
            current.offlineExports?.createPath == "/api/exports",
            "Apple runtime descriptor should decode offline export create endpoint"
        )
        require(
            current.offlineExports?.downloadPathTemplate == "/api/exports/{export_id}/download",
            "Apple runtime descriptor should decode offline export download template"
        )
        require(
            current.offlineExports?.sourceKinds == ["job", "library"],
            "Apple runtime descriptor should decode offline export source kinds"
        )
        require(
            current.offlineExports?.playerTypes == ["interactive-text"],
            "Apple runtime descriptor should decode offline export player types"
        )
        require(
            current.pipelineJobs?.listPath == "/api/pipelines/jobs",
            "Apple runtime descriptor should decode pipeline jobs listing endpoint"
        )
        require(
            current.pipelineJobs?.statusPathTemplate == "/api/pipelines/{job_id}",
            "Apple runtime descriptor should decode pipeline job status endpoint template"
        )
        require(
            current.pipelineJobs?.eventStreamPathTemplate == "/api/pipelines/{job_id}/events",
            "Apple runtime descriptor should decode pipeline job event stream endpoint template"
        )
        require(
            current.pipelineJobs?.deletePathTemplate == "/api/pipelines/jobs/{job_id}/delete",
            "Apple runtime descriptor should decode pipeline job delete endpoint template"
        )
        require(
            current.pipelineJobs?.restartPathTemplate == "/api/pipelines/jobs/{job_id}/restart",
            "Apple runtime descriptor should decode pipeline job restart endpoint template"
        )
        require(
            current.pipelineJobs?.cacheBusterQuery == "ts",
            "Apple runtime descriptor should decode pipeline jobs cache-buster query"
        )
        require(
            current.pipelineMedia?.jobMediaPathTemplate == "/api/pipelines/jobs/{job_id}/media",
            "Apple runtime descriptor should decode job media endpoint template"
        )
        require(
            current.pipelineMedia?.jobMediaLivePathTemplate == "/api/pipelines/jobs/{job_id}/media/live",
            "Apple runtime descriptor should decode live job media endpoint template"
        )
        require(
            current.pipelineMedia?.jobMediaChunkPathTemplate == "/api/pipelines/jobs/{job_id}/media/chunks/{chunk_id}",
            "Apple runtime descriptor should decode job media chunk endpoint template"
        )
        require(
            current.pipelineMedia?.libraryMediaPathTemplate == "/api/library/media/{job_id}",
            "Apple runtime descriptor should decode library media endpoint template"
        )
        require(
            current.pipelineMedia?.libraryMediaFilePathTemplate == "/api/library/media/{job_id}/file/{file_path}",
            "Apple runtime descriptor should decode library media file endpoint template"
        )
        require(
            current.pipelineMedia?.jobTimingPathTemplate == "/api/jobs/{job_id}/timing",
            "Apple runtime descriptor should decode job timing endpoint template"
        )
        require(
            current.pipelineMedia?.subtitleTvMetadataPathTemplate == "/api/subtitles/jobs/{job_id}/metadata/tv",
            "Apple runtime descriptor should decode subtitle TV metadata endpoint template"
        )
        require(
            current.pipelineMedia?.subtitleTvMetadataLookupPathTemplate == "/api/subtitles/jobs/{job_id}/metadata/tv/lookup",
            "Apple runtime descriptor should decode subtitle TV metadata lookup endpoint template"
        )
        require(
            current.pipelineMedia?.youtubeVideoMetadataPathTemplate == "/api/subtitles/jobs/{job_id}/metadata/youtube",
            "Apple runtime descriptor should decode YouTube metadata endpoint template"
        )
        require(
            current.pipelineMedia?.youtubeVideoMetadataLookupPathTemplate == "/api/subtitles/jobs/{job_id}/metadata/youtube/lookup",
            "Apple runtime descriptor should decode YouTube metadata lookup endpoint template"
        )
        require(
            current.pipelineMedia?.subtitleJobResultPathTemplate == "/api/subtitles/jobs/{job_id}/result",
            "Apple runtime descriptor should decode subtitle job result endpoint template"
        )
        require(
            current.pipelineMedia?.chunkOrdering == "sentenceRange",
            "Apple runtime descriptor should decode sentence-range chunk ordering"
        )
        require(
            current.linguist?.assistantLookupPath == "/api/assistant/lookup",
            "Apple runtime descriptor should decode assistant lookup endpoint"
        )
        require(
            current.linguist?.lookupCachePathTemplate == "/api/pipelines/jobs/{job_id}/lookup-cache",
            "Apple runtime descriptor should decode lookup cache endpoint template"
        )
        require(
            current.linguist?.lookupCacheWordPathTemplate == "/api/pipelines/jobs/{job_id}/lookup-cache/{word}",
            "Apple runtime descriptor should decode lookup cache word endpoint template"
        )
        require(
            current.linguist?.lookupCacheBulkPathTemplate == "/api/pipelines/jobs/{job_id}/lookup-cache/bulk",
            "Apple runtime descriptor should decode lookup cache bulk endpoint template"
        )
        require(
            current.linguist?.lookupCacheSummaryPathTemplate == "/api/pipelines/jobs/{job_id}/lookup-cache/summary",
            "Apple runtime descriptor should decode lookup cache summary endpoint template"
        )
        require(
            current.linguist?.audioSynthesisPath == "/api/audio",
            "Apple runtime descriptor should decode audio synthesis endpoint"
        )
        require(
            current.libraryActions?.itemsPath == "/api/library/items",
            "Apple runtime descriptor should decode library item listing endpoint"
        )
        require(
            current.libraryActions?.itemMetadataPathTemplate == "/api/library/items/{job_id}",
            "Apple runtime descriptor should decode library metadata endpoint template"
        )
        require(
            current.libraryActions?.sourceUploadPathTemplate == "/api/library/items/{job_id}/upload-source",
            "Apple runtime descriptor should decode library source upload endpoint template"
        )
        require(
            current.libraryActions?.movePathTemplate == "/api/library/move/{job_id}",
            "Apple runtime descriptor should decode library move endpoint template"
        )
        require(
            current.libraryActions?.removePathTemplate == "/api/library/remove/{job_id}",
            "Apple runtime descriptor should decode library remove endpoint template"
        )
        require(
            current.libraryActions?.isbnLookupPath == "/api/library/isbn/lookup",
            "Apple runtime descriptor should decode library ISBN lookup endpoint"
        )
        require(
            current.libraryActions?.isbnApplyPathTemplate == "/api/library/items/{job_id}/isbn",
            "Apple runtime descriptor should decode library ISBN apply endpoint template"
        )
        require(
            current.libraryActions?.metadataEnrichPathTemplate == "/api/library/items/{job_id}/enrich",
            "Apple runtime descriptor should decode library metadata enrichment endpoint template"
        )
        require(
            current.playbackState?.bookmarksPathTemplate == "/api/bookmarks/{job_id}",
            "Apple runtime descriptor should decode bookmarks endpoint template"
        )
        require(
            current.playbackState?.bookmarkDeletePathTemplate == "/api/bookmarks/{job_id}/{bookmark_id}",
            "Apple runtime descriptor should decode bookmark delete endpoint template"
        )
        require(
            current.playbackState?.readingBedsPath == "/api/reading-beds",
            "Apple runtime descriptor should decode reading-bed catalog endpoint"
        )
        require(
            current.playbackState?.resumeListPath == "/api/resume",
            "Apple runtime descriptor should decode batch resume endpoint"
        )
        require(
            current.playbackState?.resumePathTemplate == "/api/resume/{job_id}",
            "Apple runtime descriptor should decode resume endpoint template"
        )
        require(
            current.playbackState?.resumeFilterQuery == "job_id",
            "Apple runtime descriptor should decode resume filter query"
        )
        require(
            current.notifications?.deviceRegistrationPath == "/api/notifications/devices",
            "Apple runtime descriptor should decode notification device registration endpoint"
        )
        require(
            current.notifications?.deviceRemovalPathTemplate == "/api/notifications/devices/{device_id}",
            "Apple runtime descriptor should decode notification device removal endpoint template"
        )
        require(
            current.notifications?.testPath == "/api/notifications/test",
            "Apple runtime descriptor should decode notification test endpoint"
        )
        require(
            current.notifications?.richTestPath == "/api/notifications/test/rich",
            "Apple runtime descriptor should decode rich notification test endpoint"
        )
        require(
            current.notifications?.preferencesPath == "/api/notifications/preferences",
            "Apple runtime descriptor should decode notification preferences endpoint"
        )

        let legacyRuntimeJSON = """
        {
          "status": "ok",
          "app": "ebook-tools",
          "service": "ebook-tools-api",
          "version": "legacy-version",
          "health_path": "/_health",
          "auth": {
            "login_path": "/api/auth/login",
            "session_path": "/api/auth/session",
            "token_transport": "Authorization: Bearer"
          },
          "client_config": {
            "api_base_url_environment": ["EBOOK_TOOLS_API_BASE_URL"],
            "session_token_storage": "device-keychain"
          }
        }
        """.data(using: .utf8)!

        let legacy = try decoder.decode(BackendRuntimeDescriptorResponse.self, from: legacyRuntimeJSON)
        require(legacy.applePipeline == nil, "Apple runtime descriptor should tolerate legacy payloads without pipeline metadata")
        require(legacy.creation == nil, "Apple runtime descriptor should tolerate legacy payloads without Create metadata")
        require(legacy.offlineExports == nil, "Apple runtime descriptor should tolerate legacy payloads without offline export metadata")
        require(legacy.pipelineJobs == nil, "Apple runtime descriptor should tolerate legacy payloads without pipeline jobs metadata")
        require(legacy.pipelineMedia == nil, "Apple runtime descriptor should tolerate legacy payloads without pipeline media metadata")
        require(legacy.linguist == nil, "Apple runtime descriptor should tolerate legacy payloads without linguist metadata")
        require(legacy.libraryActions == nil, "Apple runtime descriptor should tolerate legacy payloads without library action metadata")
        require(legacy.playbackState == nil, "Apple runtime descriptor should tolerate legacy payloads without playback state metadata")
        require(legacy.notifications == nil, "Apple runtime descriptor should tolerate legacy payloads without notification metadata")

        let stalePipelineMediaRuntimeJSON = """
        {
          "status": "ok",
          "app": "ebook-tools",
          "service": "ebook-tools-api",
          "version": "stale-media-contract",
          "healthPath": "/_health",
          "auth": {
            "loginPath": "/api/auth/login",
            "logoutPath": "/api/auth/logout",
            "passwordPath": "/api/auth/password",
            "registerPath": "/api/auth/register",
            "sessionPath": "/api/auth/session",
            "tokenTransport": "Authorization: Bearer"
          },
          "clientConfig": {
            "apiBaseUrlEnvironment": ["EBOOK_TOOLS_API_BASE_URL"],
            "sessionTokenStorage": "device-keychain"
          },
          "pipelineMedia": {
            "jobMediaPathTemplate": "/api/pipelines/jobs/{job_id}/media",
            "jobMediaLivePathTemplate": "/api/pipelines/jobs/{job_id}/media/live",
            "jobMediaChunkPathTemplate": "/api/pipelines/jobs/{job_id}/media/chunks/{chunk_id}",
            "libraryMediaPathTemplate": "/api/library/media/{job_id}",
            "libraryMediaFilePathTemplate": "/api/library/media/{job_id}/file/{file_path}",
            "jobTimingPathTemplate": "/api/jobs/{job_id}/timing",
            "subtitleTvMetadataPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/tv",
            "subtitleTvMetadataLookupPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/tv/lookup",
            "youtubeVideoMetadataPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/youtube",
            "youtubeVideoMetadataLookupPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/youtube/lookup",
            "subtitleJobResultPathTemplate": "/api/subtitles/jobs/{job_id}/result"
          }
        }
        """.data(using: .utf8)!

        let staleMedia = try decoder.decode(BackendRuntimeDescriptorResponse.self, from: stalePipelineMediaRuntimeJSON)
        require(staleMedia.pipelineMedia != nil, "Apple runtime descriptor should decode stale pipeline media contracts")
        require(staleMedia.pipelineMedia?.chunkOrdering == nil, "Apple runtime descriptor should surface missing chunk ordering as nil")

        print("apple runtime descriptor payload checks passed")
    }

    private static func require(_ condition: @autoclosure () -> Bool, _ message: String) {
        if !condition() {
            fputs("failure: \(message)\n", stderr)
            Foundation.exit(1)
        }
    }
}
