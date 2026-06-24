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
          "health_path": "/_health",
          "auth": {
            "login_path": "/api/auth/login",
            "session_path": "/api/auth/session",
            "token_transport": "Authorization: Bearer"
          },
          "client_config": {
            "api_base_url_environment": [
              "INTERACTIVE_READER_API_BASE_URL",
              "EBOOK_TOOLS_API_BASE_URL",
              "E2E_API_BASE_URL"
            ],
            "credential_environment": ["E2E_USERNAME", "E2E_PASSWORD"],
            "session_token_storage": "device-keychain",
            "legacy_token_migration": "userdefaults-authToken"
          },
          "apple_pipeline": {
            "manifest_id": "ebook-tools",
            "simulator_profiles": ["ios", "ipados", "tvos", "tvos-cinema"],
            "device_profiles": ["iphone", "ipad", "appletv", "cinema"]
          },
          "creation": {
            "book_options_path": "/api/books/options",
            "book_jobs_path": "/api/books/jobs",
            "pipeline_files_path": "/api/pipelines/files",
            "pipeline_content_index_path": "/api/pipelines/files/content-index",
            "pipeline_upload_path": "/api/pipelines/files/upload",
            "pipeline_jobs_path": "/api/pipelines",
            "pipeline_intake_status_path": "/api/pipelines/intake/status",
            "subtitle_sources_path": "/api/subtitles/sources",
            "subtitle_delete_source_path": "/api/subtitles/delete-source",
            "subtitle_models_path": "/api/subtitles/models",
            "subtitle_jobs_path": "/api/subtitles/jobs",
            "youtube_library_path": "/api/subtitles/youtube/library",
            "youtube_dub_path": "/api/subtitles/youtube/dub"
          },
          "offline_exports": {
            "create_path": "/api/exports",
            "download_path_template": "/api/exports/{export_id}/download",
            "source_kinds": ["job", "library"],
            "player_types": ["interactive-text"]
          }
        }
        """.data(using: .utf8)!

        let current = try decoder.decode(BackendRuntimeDescriptorResponse.self, from: currentRuntimeJSON)
        require(current.applePipeline?.manifestId == "ebook-tools", "Apple runtime descriptor should decode pipeline manifest id")
        require(
            current.applePipeline?.simulatorProfiles.contains("ipados") == true,
            "Apple runtime descriptor should decode simulator profiles"
        )
        require(
            current.clientConfig.credentialEnvironment == ["E2E_USERNAME", "E2E_PASSWORD"],
            "Apple runtime descriptor should decode public credential environment names"
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

        print("apple runtime descriptor payload checks passed")
    }

    private static func require(_ condition: @autoclosure () -> Bool, _ message: String) {
        if !condition() {
            fputs("failure: \(message)\n", stderr)
            Foundation.exit(1)
        }
    }
}
