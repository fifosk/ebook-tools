from __future__ import annotations

from pathlib import Path

from modules.webapi.runtime_descriptor import (
    CREATION_DESCRIPTOR,
    LIBRARY_ACTIONS_DESCRIPTOR,
    OFFLINE_EXPORTS_DESCRIPTOR,
    PLAYBACK_STATE_DESCRIPTOR,
    assert_runtime_descriptor_is_public,
    build_runtime_descriptor,
)

ROOT = Path(__file__).resolve().parents[1]
APPLE_AUTH_MODELS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Models"
    / "AuthApiModels.swift"
)
PLAYBACK_SETTINGS_SECTIONS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "PlaybackSettingsSections.swift"
)
PLAYBACK_SETTINGS_VIEW = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Library"
    / "PlaybackSettingsView.swift"
)
API_CLIENT_CREATION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+Creation.swift"
)
API_CLIENT_LIBRARY_JOBS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+LibraryJobs.swift"
)
API_CLIENT_PLAYBACK_STATE = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+PlaybackState.swift"
)
APPLE_SERVICES = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Services"


def test_runtime_descriptor_advertises_apple_pipeline_contract() -> None:
    descriptor = build_runtime_descriptor("test-version")

    assert descriptor["status"] == "ok"
    assert descriptor["app"] == "ebook-tools"
    assert descriptor["service"] == "ebook-tools-api"
    assert descriptor["healthPath"] == "/_health"
    assert descriptor["auth"] == {
        "loginPath": "/api/auth/login",
        "sessionPath": "/api/auth/session",
        "tokenTransport": "Authorization: Bearer",
    }
    assert descriptor["clientConfig"]["sessionTokenStorage"] == "device-keychain"
    assert descriptor["clientConfig"]["legacyTokenMigration"] == "userdefaults-authToken"
    assert descriptor["applePipeline"]["manifestId"] == "ebook-tools"
    assert descriptor["creation"] == CREATION_DESCRIPTOR
    assert descriptor["offlineExports"] == {
        "createPath": "/api/exports",
        "downloadPathTemplate": "/api/exports/{export_id}/download",
        "sourceKinds": ["job", "library"],
        "playerTypes": ["interactive-text"],
    }
    assert descriptor["offlineExports"] == OFFLINE_EXPORTS_DESCRIPTOR | {
        "sourceKinds": ["job", "library"],
        "playerTypes": ["interactive-text"],
    }
    assert descriptor["libraryActions"] == LIBRARY_ACTIONS_DESCRIPTOR
    assert descriptor["playbackState"] == PLAYBACK_STATE_DESCRIPTOR
    assert_runtime_descriptor_is_public(descriptor)


def test_apple_runtime_descriptor_model_decodes_create_contract() -> None:
    source = APPLE_AUTH_MODELS.read_text(encoding="utf-8")

    assert "struct ApplePipelineContract: Decodable, Equatable" in source
    assert "let manifestId: String" in source
    assert "let simulatorProfiles: [String]" in source
    assert "let deviceProfiles: [String]" in source
    assert "struct CreationContract: Decodable, Equatable" in source
    assert "let bookOptionsPath: String" in source
    assert "let bookJobsPath: String" in source
    for key in [
        "pipelineFilesPath",
        "pipelineContentIndexPath",
        "pipelineUploadPath",
        "pipelineJobsPath",
        "pipelineIntakeStatusPath",
        "pipelineDefaultsPath",
        "pipelineLlmModelsPath",
        "imageNodeAvailabilityPath",
        "audioVoicesPath",
        "subtitleSourcesPath",
        "subtitleDeleteSourcePath",
        "subtitleModelsPath",
        "subtitleJobsPath",
        "youtubeLibraryPath",
        "youtubeSubtitleStreamsPath",
        "youtubeExtractSubtitlesPath",
        "subtitleTvMetadataPreviewPath",
        "subtitleTvMetadataCacheClearPath",
        "youtubeMetadataPreviewPath",
        "youtubeMetadataCacheClearPath",
        "youtubeDubPath",
        "acquisitionProvidersPath",
        "acquisitionDiscoverPath",
        "acquisitionAcquirePath",
        "acquisitionArtifactPreparePathTemplate",
        "acquisitionJobsPath",
        "acquisitionJobPathTemplate",
        "templateListPath",
        "templatePathTemplate",
    ]:
        assert f"let {key}: String?" in source
    assert "let applePipeline: ApplePipelineContract?" in source
    assert "let creation: CreationContract?" in source
    assert "struct OfflineExportContract: Decodable, Equatable" in source
    assert "let createPath: String" in source
    assert "let downloadPathTemplate: String" in source
    assert "let sourceKinds: [String]" in source
    assert "let playerTypes: [String]" in source
    assert "let offlineExports: OfflineExportContract?" in source
    assert "struct LibraryActionsContract: Decodable, Equatable" in source
    assert "let itemsPath: String" in source
    assert "let itemMetadataPathTemplate: String" in source
    assert "let sourceUploadPathTemplate: String" in source
    assert "let isbnLookupPath: String" in source
    assert "let isbnApplyPathTemplate: String" in source
    assert "let metadataEnrichPathTemplate: String" in source
    assert "let libraryActions: LibraryActionsContract?" in source
    assert "struct PlaybackStateContract: Decodable, Equatable" in source
    assert "let bookmarksPathTemplate: String" in source
    assert "let bookmarkDeletePathTemplate: String" in source
    assert "let resumeListPath: String" in source
    assert "let resumePathTemplate: String" in source
    assert "let resumeFilterQuery: String" in source
    assert "let playbackState: PlaybackStateContract?" in source
    playback_state_source = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Models"
        / "PlaybackStateApiModels.swift"
    ).read_text(encoding="utf-8")
    assert "struct ResumePositionListResponse: Decodable" in playback_state_source
    assert "let entries: [ResumePositionEntry]" in playback_state_source


def test_settings_surfaces_create_contract_runtime_status() -> None:
    source = PLAYBACK_SETTINGS_SECTIONS.read_text(encoding="utf-8")

    assert "enum BackendRuntimeContractState: Equatable" in source
    assert "case ready(summary: String)" in source
    assert "case mismatch(summary: String)" in source
    assert "case unavailable" in source
    assert 'title: "Create Contract"' in source
    assert 'accessibilityIdentifier: "settingsCreateContractRow"' in source
    assert "var libraryActionsContractState: BackendRuntimeContractState?" in source
    assert 'title: "Library Contract"' in source
    assert 'accessibilityIdentifier: "settingsLibraryActionsContractRow"' in source
    assert "var offlineExportsContractState: BackendRuntimeContractState?" in source
    assert 'title: "Offline Export Contract"' in source
    assert 'accessibilityIdentifier: "settingsOfflineExportsContractRow"' in source
    assert "var playbackStateContractState: BackendRuntimeContractState?" in source
    assert 'title: "Playback State Contract"' in source
    assert 'accessibilityIdentifier: "settingsPlaybackStateContractRow"' in source


def test_apple_create_client_and_settings_share_runtime_contract_paths() -> None:
    creation_source = API_CLIENT_CREATION.read_text(encoding="utf-8")
    settings_source = PLAYBACK_SETTINGS_VIEW.read_text(encoding="utf-8")

    assert "enum AppleCreateRuntimeContract" in creation_source
    assert 'static let bookOptionsPath = "/api/books/options"' in creation_source
    assert 'static let bookJobsPath = "/api/books/jobs"' in creation_source
    expected_constants = {
        "pipelineFilesPath": "/api/pipelines/files",
        "pipelineContentIndexPath": "/api/pipelines/files/content-index",
        "pipelineUploadPath": "/api/pipelines/files/upload",
        "pipelineJobsPath": "/api/pipelines",
        "pipelineIntakeStatusPath": "/api/pipelines/intake/status",
        "pipelineDefaultsPath": "/api/pipelines/defaults",
        "pipelineLlmModelsPath": "/api/pipelines/llm-models",
        "imageNodeAvailabilityPath": "/api/pipelines/image-nodes/availability",
        "audioVoicesPath": "/api/audio/voices",
        "subtitleSourcesPath": "/api/subtitles/sources",
        "subtitleDeleteSourcePath": "/api/subtitles/delete-source",
        "subtitleModelsPath": "/api/subtitles/models",
        "subtitleJobsPath": "/api/subtitles/jobs",
        "youtubeLibraryPath": "/api/subtitles/youtube/library",
        "youtubeSubtitleStreamsPath": "/api/subtitles/youtube/subtitle-streams",
        "youtubeExtractSubtitlesPath": "/api/subtitles/youtube/extract-subtitles",
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
        "templatePathTemplate": "/api/creation/templates/{template_id}",
    }
    for key, path in expected_constants.items():
        assert f'static let {key} = "{path}"' in creation_source
        assert f"AppleCreateRuntimeContract.{key}" in settings_source
    assert "sendRequest(path: AppleCreateRuntimeContract.bookOptionsPath)" in creation_source
    assert "path: AppleCreateRuntimeContract.bookJobsPath" in creation_source
    assert "func checkImageNodeAvailability(baseURLs: [String])" in creation_source
    assert "ImageNodeAvailabilityRequest(baseUrls: baseURLs)" in creation_source
    assert "path: AppleCreateRuntimeContract.imageNodeAvailabilityPath" in creation_source
    assert "func acquireAcquisitionCandidate(" in creation_source
    assert "path: AppleCreateRuntimeContract.acquisitionAcquirePath" in creation_source
    assert "func prepareAcquisitionArtifact(" in creation_source
    assert "AppleCreateRuntimeContract.acquisitionArtifactPreparePath" in creation_source
    assert "func createAcquisitionJob(" in creation_source
    assert "path: AppleCreateRuntimeContract.acquisitionJobsPath" in creation_source
    assert "func fetchAcquisitionJobStatus(" in creation_source
    assert "AppleCreateRuntimeContract.acquisitionJobPath" in creation_source
    api_models_source = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Models"
        / "PipelineCreationApiModels.swift"
    ).read_text(encoding="utf-8")
    assert "struct ImageNodeAvailabilityRequest: Encodable, Equatable" in api_models_source
    assert 'case baseUrls = "base_urls"' in api_models_source
    assert "struct ImageNodeAvailabilityResponse: Decodable, Equatable" in api_models_source
    assert 'case candidateToken = "candidate_token"' in api_models_source
    linguist_source = (
        ROOT
        / "ios"
        / "InteractiveReader"
        / "InteractiveReader"
        / "Services"
        / "APIClient+Linguist.swift"
    ).read_text(encoding="utf-8")
    assert "sendRequest(path: AppleCreateRuntimeContract.pipelineLlmModelsPath)" in linguist_source
    assert "sendRequest(path: AppleCreateRuntimeContract.audioVoicesPath)" in linguist_source
    assert "let encodedWord = AppleAPIPathComponentEncoding.encode(word)" in linguist_source
    assert ".alphanumerics" not in linguist_source
    assert '("bookOptionsPath", creation.bookOptionsPath, AppleCreateRuntimeContract.bookOptionsPath)' in settings_source
    assert '("bookJobsPath", creation.bookJobsPath, AppleCreateRuntimeContract.bookJobsPath)' in settings_source
    assert "AppleCreateRuntimeContract.subtitleDeleteSourcePath" in settings_source
    assert "AppleCreateRuntimeContract.acquisitionProvidersPath" in settings_source
    assert "AppleCreateRuntimeContract.acquisitionDiscoverPath" in settings_source
    assert "AppleCreateRuntimeContract.acquisitionAcquirePath" in settings_source
    assert "return .mismatch(summary: mismatches.joined(separator: \" · \"))" in settings_source
    assert "\\(expectedPaths.count) endpoints" in settings_source


def test_apple_library_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_LIBRARY_JOBS.read_text(encoding="utf-8")

    assert "enum AppleLibraryRuntimeContract" in source
    assert 'static let itemsPath = "/api/library/items"' in source
    assert 'static let itemPathTemplate = "/api/library/items/{job_id}"' in source
    assert 'static let sourceUploadPathTemplate = "/api/library/items/{job_id}/upload-source"' in source
    assert 'static let isbnLookupPath = "/api/library/isbn/lookup"' in source
    assert 'static let isbnApplyPathTemplate = "/api/library/items/{job_id}/isbn"' in source
    assert 'static let metadataEnrichPathTemplate = "/api/library/items/{job_id}/enrich"' in source
    assert "static func itemPath(_ encodedJobId: String) -> String" in source
    assert "static func sourceUploadPath(_ encodedJobId: String) -> String" in source
    assert "static func isbnApplyPath(_ encodedJobId: String) -> String" in source
    assert "static func metadataEnrichPath(_ encodedJobId: String) -> String" in source
    assert "AppleLibraryRuntimeContract.itemsPath" in source
    assert "AppleLibraryRuntimeContract.itemPath(encoded)" in source
    assert "AppleLibraryRuntimeContract.sourceUploadPath(encoded)" in source
    assert "AppleLibraryRuntimeContract.isbnLookupPath" in source
    assert "AppleLibraryRuntimeContract.isbnApplyPath(encoded)" in source
    assert "AppleLibraryRuntimeContract.metadataEnrichPath(encoded)" in source


def test_apple_offline_export_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_LIBRARY_JOBS.read_text(encoding="utf-8")

    assert "enum AppleOfflineExportRuntimeContract" in source
    assert 'static let createPath = "/api/exports"' in source
    assert 'static let downloadPathTemplate = "/api/exports/{export_id}/download"' in source
    assert 'static let playerType = "interactive-text"' in source
    assert 'static let supportedSourceKinds = ["job", "library"]' in source
    assert "path: AppleOfflineExportRuntimeContract.createPath" in source
    assert "playerType: AppleOfflineExportRuntimeContract.playerType" in source


def test_apple_playback_state_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_PLAYBACK_STATE.read_text(encoding="utf-8")

    assert "enum ApplePlaybackStateRuntimeContract" in source
    assert "enum AppleAPIPathComponentEncoding" in source
    assert 'allowed.remove(charactersIn: "/?#")' in source
    assert "static func encode(_ value: String) -> String" in source
    assert 'static let bookmarksPathTemplate = "/api/bookmarks/{job_id}"' in source
    assert 'static let bookmarkDeletePathTemplate = "/api/bookmarks/{job_id}/{bookmark_id}"' in source
    assert 'static let resumeListPath = "/api/resume"' in source
    assert 'static let resumePathTemplate = "/api/resume/{job_id}"' in source
    assert 'static let resumeFilterQuery = "job_id"' in source
    assert "static func bookmarksPath(_ encodedJobId: String) -> String" in source
    assert "static func bookmarkDeletePath(" in source
    assert "static func resumePath(_ encodedJobId: String) -> String" in source
    assert "static func resumeListPath(jobIds: [String]) -> String" in source
    assert "URLQueryItem(name: resumeFilterQuery" in source
    assert "ApplePlaybackStateRuntimeContract.bookmarksPath(encoded)" in source
    assert "ApplePlaybackStateRuntimeContract.bookmarkDeletePath(" in source
    assert "ApplePlaybackStateRuntimeContract.resumePath(encoded)" in source
    assert "func fetchResumePositions(jobIds: [String]) async throws -> ResumePositionListResponse" in source
    assert "ApplePlaybackStateRuntimeContract.resumeListPath(jobIds: jobIds)" in source


def test_apple_service_clients_use_safe_path_component_encoding() -> None:
    for path in APPLE_SERVICES.glob("*.swift"):
        source = path.read_text(encoding="utf-8")
        assert "addingPercentEncoding(withAllowedCharacters: .urlPathAllowed)" not in source, path
    media_resolver_source = (
        ROOT
        / "ios/InteractiveReader/InteractiveReader/Utilities/MediaURLResolver.swift"
    ).read_text(encoding="utf-8")
    assert "addingPercentEncoding(withAllowedCharacters: .urlPathAllowed)" not in media_resolver_source
    assert "AppleAPIPathComponentEncoding.encode(jobId)" in media_resolver_source
    assert "AppleAPIPathComponentEncoding.encode(String($0))" in media_resolver_source

    for path in [
        APPLE_SERVICES / "APIClient+Creation.swift",
        APPLE_SERVICES / "APIClient+LibraryJobs.swift",
        APPLE_SERVICES / "APIClient+PipelineMedia.swift",
        APPLE_SERVICES / "APIClient+PlaybackState.swift",
        APPLE_SERVICES / "APIClient+Linguist.swift",
        APPLE_SERVICES / "APIClient+Notifications.swift",
        APPLE_SERVICES / "JobEventStreamClient.swift",
    ]:
        assert "AppleAPIPathComponentEncoding.encode(" in path.read_text(encoding="utf-8")


def test_settings_compares_runtime_contracts() -> None:
    source = PLAYBACK_SETTINGS_VIEW.read_text(encoding="utf-8")

    assert "libraryActionsContract: Self.libraryActionsContractState(from: descriptor.libraryActions)" in source
    assert "offlineExportsContract: Self.offlineExportsContractState(from: descriptor.offlineExports)" in source
    assert "playbackStateContract: Self.playbackStateContractState(from: descriptor.playbackState)" in source
    assert "private static func libraryActionsContractState(" in source
    assert "private static func offlineExportsContractState(" in source
    assert "private static func playbackStateContractState(" in source
    for key in [
        "itemPathTemplate",
        "sourceUploadPathTemplate",
        "isbnApplyPathTemplate",
        "metadataEnrichPathTemplate",
    ]:
        assert f"AppleLibraryRuntimeContract.{key}" in source
    assert "AppleOfflineExportRuntimeContract.downloadPathTemplate" in source
    assert "AppleOfflineExportRuntimeContract.supportedSourceKinds" in source
    assert "[AppleOfflineExportRuntimeContract.playerType]" in source
    for key in [
        "bookmarksPathTemplate",
        "bookmarkDeletePathTemplate",
        "resumeListPath",
        "resumePathTemplate",
        "resumeFilterQuery",
    ]:
        assert f"ApplePlaybackStateRuntimeContract.{key}" in source
