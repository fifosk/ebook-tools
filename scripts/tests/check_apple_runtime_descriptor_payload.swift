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
            "pipeline_defaults_path": "/api/pipelines/defaults",
            "pipeline_llm_models_path": "/api/pipelines/llm-models",
            "image_node_availability_path": "/api/pipelines/image-nodes/availability",
            "audio_voices_path": "/api/audio/voices",
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
          },
          "library_actions": {
            "items_path": "/api/library/items",
            "item_metadata_path_template": "/api/library/items/{job_id}",
            "source_upload_path_template": "/api/library/items/{job_id}/upload-source",
            "isbn_lookup_path": "/api/library/isbn/lookup",
            "isbn_apply_path_template": "/api/library/items/{job_id}/isbn",
            "metadata_enrich_path_template": "/api/library/items/{job_id}/enrich"
          },
          "playback_state": {
            "bookmarks_path_template": "/api/bookmarks/{job_id}",
            "bookmark_delete_path_template": "/api/bookmarks/{job_id}/{bookmark_id}",
            "resume_list_path": "/api/resume",
            "resume_path_template": "/api/resume/{job_id}",
            "resume_filter_query": "job_id"
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
            current.creation?.pipelineDefaultsPath == "/api/pipelines/defaults",
            "Apple runtime descriptor should decode pipeline defaults endpoint"
        )
        require(
            current.creation?.pipelineLlmModelsPath == "/api/pipelines/llm-models",
            "Apple runtime descriptor should decode pipeline LLM models endpoint"
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
        require(legacy.libraryActions == nil, "Apple runtime descriptor should tolerate legacy payloads without library action metadata")
        require(legacy.playbackState == nil, "Apple runtime descriptor should tolerate legacy payloads without playback state metadata")

        print("apple runtime descriptor payload checks passed")
    }

    private static func require(_ condition: @autoclosure () -> Bool, _ message: String) {
        if !condition() {
            fputs("failure: \(message)\n", stderr)
            Foundation.exit(1)
        }
    }
}
