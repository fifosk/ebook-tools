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
            "pipeline_search_path": "/api/pipelines/search",
            "image_node_availability_path": "/api/pipelines/image-nodes/availability",
            "audio_voices_path": "/api/audio/voices",
            "subtitle_sources_path": "/api/subtitles/sources",
            "subtitle_delete_source_path": "/api/subtitles/delete-source",
            "subtitle_models_path": "/api/subtitles/models",
            "subtitle_jobs_path": "/api/subtitles/jobs",
            "youtube_library_path": "/api/subtitles/youtube/library",
            "youtube_subtitle_streams_path": "/api/subtitles/youtube/subtitle-streams",
            "youtube_extract_subtitles_path": "/api/subtitles/youtube/extract-subtitles",
            "subtitle_tv_metadata_preview_path": "/api/subtitles/metadata/tv/lookup",
            "subtitle_tv_metadata_cache_clear_path": "/api/subtitles/metadata/tv/cache/clear",
            "youtube_metadata_preview_path": "/api/subtitles/metadata/youtube/lookup",
            "youtube_metadata_cache_clear_path": "/api/subtitles/metadata/youtube/cache/clear",
            "youtube_dub_path": "/api/subtitles/youtube/dub",
            "acquisition_providers_path": "/api/acquisition/providers",
            "acquisition_discover_path": "/api/acquisition/discover",
            "acquisition_acquire_path": "/api/acquisition/acquire",
            "acquisition_artifact_prepare_path_template": "/api/acquisition/artifacts/{artifact_id}/prepare",
            "acquisition_jobs_path": "/api/acquisition/jobs",
            "acquisition_job_path_template": "/api/acquisition/jobs/{task_id}",
            "template_list_path": "/api/creation/templates",
            "template_path_template": "/api/creation/templates/{template_id}"
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
            current.creation?.youtubeSubtitleStreamsPath == "/api/subtitles/youtube/subtitle-streams",
            "Apple runtime descriptor should decode YouTube subtitle-stream endpoint"
        )
        require(
            current.creation?.youtubeExtractSubtitlesPath == "/api/subtitles/youtube/extract-subtitles",
            "Apple runtime descriptor should decode YouTube subtitle extraction endpoint"
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
