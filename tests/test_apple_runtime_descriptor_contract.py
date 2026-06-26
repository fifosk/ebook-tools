from __future__ import annotations

from pathlib import Path

from modules.webapi.runtime_descriptor import (
    CREATION_DESCRIPTOR,
    LIBRARY_ACTIONS_DESCRIPTOR,
    LINGUIST_DESCRIPTOR,
    NOTIFICATIONS_DESCRIPTOR,
    OFFLINE_EXPORTS_DESCRIPTOR,
    PIPELINE_JOBS_DESCRIPTOR,
    PIPELINE_MEDIA_DESCRIPTOR,
    PLAYBACK_STATE_DESCRIPTOR,
    assert_runtime_descriptor_is_public,
    build_runtime_descriptor,
)

ROOT = Path(__file__).resolve().parents[1]
API_CLIENT_AUTH = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Services"
    / "APIClient+Auth.swift"
)
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
APPLE_RUNTIME_DESCRIPTOR_PAYLOAD_CHECK = (
    ROOT / "scripts" / "tests" / "check_apple_runtime_descriptor_payload.swift"
)


def test_runtime_descriptor_advertises_apple_pipeline_contract() -> None:
    descriptor = build_runtime_descriptor("test-version")

    assert descriptor["status"] == "ok"
    assert descriptor["app"] == "ebook-tools"
    assert descriptor["service"] == "ebook-tools-api"
    assert descriptor["healthPath"] == "/_health"
    assert descriptor["auth"] == {
        "loginPath": "/api/auth/login",
        "oauthPath": "/api/auth/oauth",
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
    assert descriptor["pipelineJobs"] == PIPELINE_JOBS_DESCRIPTOR
    assert descriptor["pipelineMedia"] == PIPELINE_MEDIA_DESCRIPTOR
    assert descriptor["linguist"] == LINGUIST_DESCRIPTOR
    assert descriptor["playbackState"] == PLAYBACK_STATE_DESCRIPTOR
    assert descriptor["notifications"] == NOTIFICATIONS_DESCRIPTOR
    assert_runtime_descriptor_is_public(descriptor)


def test_apple_runtime_descriptor_model_decodes_create_contract() -> None:
    source = APPLE_AUTH_MODELS.read_text(encoding="utf-8")

    assert "struct AuthContract: Decodable, Equatable" in source
    assert "let loginPath: String" in source
    assert "let oauthPath: String?" in source
    assert "let sessionPath: String" in source
    assert "let tokenTransport: String" in source
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
        "pipelineSearchPath",
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
    assert "struct PipelineJobsContract: Decodable, Equatable" in source
    assert "let listPath: String" in source
    assert "let statusPathTemplate: String" in source
    assert "let eventStreamPathTemplate: String" in source
    assert "let deletePathTemplate: String" in source
    assert "let restartPathTemplate: String" in source
    assert "let cacheBusterQuery: String" in source
    assert "let pipelineJobs: PipelineJobsContract?" in source
    assert "struct PipelineMediaContract: Decodable, Equatable" in source
    for key in [
        "jobMediaPathTemplate",
        "jobMediaLivePathTemplate",
        "jobMediaChunkPathTemplate",
        "libraryMediaPathTemplate",
        "libraryMediaFilePathTemplate",
        "jobTimingPathTemplate",
        "subtitleTvMetadataPathTemplate",
        "youtubeVideoMetadataPathTemplate",
    ]:
        assert f"let {key}: String" in source
    assert "let pipelineMedia: PipelineMediaContract?" in source
    assert "struct LinguistContract: Decodable, Equatable" in source
    for key in [
        "assistantLookupPath",
        "lookupCachePathTemplate",
        "lookupCacheWordPathTemplate",
        "lookupCacheBulkPathTemplate",
        "lookupCacheSummaryPathTemplate",
        "audioSynthesisPath",
    ]:
        assert f"let {key}: String" in source
    assert "let linguist: LinguistContract?" in source
    assert "struct LibraryActionsContract: Decodable, Equatable" in source
    assert "let itemsPath: String" in source
    assert "let itemMetadataPathTemplate: String" in source
    assert "let sourceUploadPathTemplate: String" in source
    assert "let movePathTemplate: String" in source
    assert "let removePathTemplate: String" in source
    assert "let isbnLookupPath: String" in source
    assert "let isbnApplyPathTemplate: String" in source
    assert "let metadataEnrichPathTemplate: String" in source
    assert "let libraryActions: LibraryActionsContract?" in source
    assert "struct PlaybackStateContract: Decodable, Equatable" in source
    assert "let bookmarksPathTemplate: String" in source
    assert "let bookmarkDeletePathTemplate: String" in source
    assert "let readingBedsPath: String?" in source
    assert "let resumeListPath: String" in source
    assert "let resumePathTemplate: String" in source
    assert "let resumeFilterQuery: String" in source
    assert "let playbackState: PlaybackStateContract?" in source
    assert "struct NotificationsContract: Decodable, Equatable" in source
    assert "let deviceRegistrationPath: String" in source
    assert "let deviceRemovalPathTemplate: String" in source
    assert "let testPath: String" in source
    assert "let richTestPath: String" in source
    assert "let preferencesPath: String" in source
    assert "let notifications: NotificationsContract?" in source
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
    assert "var pipelineJobsContractState: BackendRuntimeContractState?" in source
    assert 'title: "Jobs Contract"' in source
    assert 'accessibilityIdentifier: "settingsPipelineJobsContractRow"' in source
    assert "var pipelineMediaContractState: BackendRuntimeContractState?" in source
    assert 'title: "Media Contract"' in source
    assert 'accessibilityIdentifier: "settingsPipelineMediaContractRow"' in source
    assert "var linguistContractState: BackendRuntimeContractState?" in source
    assert 'title: "Linguist Contract"' in source
    assert 'accessibilityIdentifier: "settingsLinguistContractRow"' in source
    assert "var offlineExportsContractState: BackendRuntimeContractState?" in source
    assert 'title: "Offline Export Contract"' in source
    assert 'accessibilityIdentifier: "settingsOfflineExportsContractRow"' in source
    assert "var playbackStateContractState: BackendRuntimeContractState?" in source
    assert 'title: "Playback State Contract"' in source
    assert 'accessibilityIdentifier: "settingsPlaybackStateContractRow"' in source
    assert "var notificationsContractState: BackendRuntimeContractState?" in source
    assert 'title: "Notification Contract"' in source
    assert 'accessibilityIdentifier: "settingsNotificationsContractRow"' in source


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
        "pipelineSearchPath": "/api/pipelines/search",
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
    assert 'templatePathTemplate.replacingOccurrences(of: "{template_id}", with: encodedTemplateId)' in creation_source
    assert 'acquisitionJobPathTemplate.replacingOccurrences(of: "{task_id}", with: encodedTaskId)' in creation_source
    assert '"\\(templateListPath)/\\(encodedTemplateId)"' not in creation_source
    assert '"\\(acquisitionJobsPath)/\\(encodedTaskId)"' not in creation_source
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
    assert "sendRequest(path: \"\\(AppleCreateRuntimeContract.pipelineSearchPath)\\(suffix)\")" in linguist_source
    assert 'sendRequest(path: "/api/pipelines/search' not in linguist_source
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


def test_standalone_swift_runtime_descriptor_payload_check_covers_create_contract() -> None:
    source = APPLE_RUNTIME_DESCRIPTOR_PAYLOAD_CHECK.read_text(encoding="utf-8")
    assert '"healthPath": "/_health"' in source
    assert '"clientConfig": {' in source
    assert '"applePipeline": {' in source
    assert '"health_path": "/_health"' in source
    for key, path in CREATION_DESCRIPTOR.items():
        assert f'"{key}": "{path}"' in source
        assert f"current.creation?.{key} == \"{path}\"" in source


def test_apple_library_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_LIBRARY_JOBS.read_text(encoding="utf-8")

    assert "enum AppleLibraryRuntimeContract" in source
    assert 'static let itemsPath = "/api/library/items"' in source
    assert 'static let itemPathTemplate = "/api/library/items/{job_id}"' in source
    assert 'static let sourceUploadPathTemplate = "/api/library/items/{job_id}/upload-source"' in source
    assert 'static let movePathTemplate = "/api/library/move/{job_id}"' in source
    assert 'static let removePathTemplate = "/api/library/remove/{job_id}"' in source
    assert 'static let isbnLookupPath = "/api/library/isbn/lookup"' in source
    assert 'static let isbnApplyPathTemplate = "/api/library/items/{job_id}/isbn"' in source
    assert 'static let metadataEnrichPathTemplate = "/api/library/items/{job_id}/enrich"' in source
    assert "static func itemPath(_ encodedJobId: String) -> String" in source
    assert "static func sourceUploadPath(_ encodedJobId: String) -> String" in source
    assert "static func movePath(_ encodedJobId: String) -> String" in source
    assert "static func removePath(_ encodedJobId: String) -> String" in source
    assert "static func isbnApplyPath(_ encodedJobId: String) -> String" in source
    assert "static func metadataEnrichPath(_ encodedJobId: String) -> String" in source
    assert 'itemPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'sourceUploadPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'isbnApplyPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'metadataEnrichPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert "AppleLibraryRuntimeContract.itemsPath" in source
    assert "AppleLibraryRuntimeContract.itemPath(encoded)" in source
    assert "AppleLibraryRuntimeContract.sourceUploadPath(encoded)" in source
    assert "AppleLibraryRuntimeContract.movePath(encoded)" in source
    assert "AppleLibraryRuntimeContract.removePath(encoded)" in source
    assert "AppleLibraryRuntimeContract.isbnLookupPath" in source
    assert "AppleLibraryRuntimeContract.isbnApplyPath(encoded)" in source
    assert "AppleLibraryRuntimeContract.metadataEnrichPath(encoded)" in source
    assert '"\\(itemsPath)/\\(encodedJobId)"' not in source
    assert '"\\(itemPath(encodedJobId))/upload-source"' not in source
    assert '"\\(itemPath(encodedJobId))/isbn"' not in source
    assert '"\\(itemPath(encodedJobId))/enrich"' not in source
    assert '"/api/library/move/\\(encoded)"' not in source
    assert '"/api/library/remove/\\(encoded)"' not in source


def test_apple_pipeline_job_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_LIBRARY_JOBS.read_text(encoding="utf-8")

    assert "enum ApplePipelineJobsRuntimeContract" in source
    assert 'static let listPath = "/api/pipelines/jobs"' in source
    assert 'static let statusPathTemplate = "/api/pipelines/{job_id}"' in source
    assert 'static let eventStreamPathTemplate = "/api/pipelines/{job_id}/events"' in source
    assert 'static let deletePathTemplate = "/api/pipelines/jobs/{job_id}/delete"' in source
    assert 'static let restartPathTemplate = "/api/pipelines/jobs/{job_id}/restart"' in source
    assert "static func listPath(cacheBuster: Int) -> String" in source
    assert "static func statusPath(_ encodedJobId: String) -> String" in source
    assert "static func eventStreamPath(_ encodedJobId: String) -> String" in source
    assert "static func deletePath(_ encodedJobId: String) -> String" in source
    assert "static func restartPath(_ encodedJobId: String) -> String" in source
    assert "ApplePipelineJobsRuntimeContract.listPath(cacheBuster: cacheBuster)" in source
    assert "ApplePipelineJobsRuntimeContract.statusPath(encoded)" in source
    assert "ApplePipelineJobsRuntimeContract.eventStreamPath(encoded)" in (APPLE_SERVICES / "JobEventStreamClient.swift").read_text(encoding="utf-8")
    assert "ApplePipelineJobsRuntimeContract.deletePath(encoded)" in source
    assert "ApplePipelineJobsRuntimeContract.restartPath(encoded)" in source
    assert '"/api/pipelines/jobs?ts=' not in source
    assert '"/api/pipelines/\\(encoded)"' not in source
    assert '"api/pipelines/\\(encoded)/events"' not in (APPLE_SERVICES / "JobEventStreamClient.swift").read_text(encoding="utf-8")
    assert '"/api/pipelines/jobs/\\(encoded)/delete"' not in source
    assert '"/api/pipelines/jobs/\\(encoded)/restart"' not in source


def test_settings_validates_pipeline_jobs_runtime_contract() -> None:
    source = PLAYBACK_SETTINGS_VIEW.read_text(encoding="utf-8")

    assert "pipelineJobsContract: Self.pipelineJobsContractState(from: descriptor.pipelineJobs)" in source
    assert "private static func pipelineJobsContractState(" in source
    for key in [
        "listPath",
        "statusPathTemplate",
        "eventStreamPathTemplate",
        "deletePathTemplate",
        "restartPathTemplate",
    ]:
        assert f"ApplePipelineJobsRuntimeContract.{key}" in source
    assert '"cacheBusterQuery", pipelineJobs.cacheBusterQuery, "ts"' in source


def test_settings_validates_pipeline_media_runtime_contract() -> None:
    source = PLAYBACK_SETTINGS_VIEW.read_text(encoding="utf-8")

    assert "pipelineMediaContract: Self.pipelineMediaContractState(from: descriptor.pipelineMedia)" in source
    assert "private static func pipelineMediaContractState(" in source
    for key in [
        "jobMediaPathTemplate",
        "jobMediaLivePathTemplate",
        "jobMediaChunkPathTemplate",
        "libraryMediaPathTemplate",
        "libraryMediaFilePathTemplate",
        "jobTimingPathTemplate",
        "subtitleTvMetadataPathTemplate",
        "youtubeVideoMetadataPathTemplate",
    ]:
        assert f"ApplePipelineMediaRuntimeContract.{key}" in source


def test_settings_validates_linguist_runtime_contract() -> None:
    source = PLAYBACK_SETTINGS_VIEW.read_text(encoding="utf-8")

    assert "linguistContract: Self.linguistContractState(from: descriptor.linguist)" in source
    assert "private static func linguistContractState(" in source
    for key in [
        "assistantLookupPath",
        "lookupCachePathTemplate",
        "lookupCacheWordPathTemplate",
        "lookupCacheBulkPathTemplate",
        "lookupCacheSummaryPathTemplate",
        "audioSynthesisPath",
    ]:
        assert f"AppleLinguistRuntimeContract.{key}" in source


def test_apple_offline_export_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_LIBRARY_JOBS.read_text(encoding="utf-8")

    assert "enum AppleOfflineExportRuntimeContract" in source
    assert 'static let createPath = "/api/exports"' in source
    assert 'static let downloadPathTemplate = "/api/exports/{export_id}/download"' in source
    assert 'static let playerType = "interactive-text"' in source
    assert 'static let supportedSourceKinds = ["job", "library"]' in source
    assert "static func downloadPath(_ encodedExportId: String) -> String" in source
    assert 'downloadPathTemplate.replacingOccurrences(of: "{export_id}", with: encodedExportId)' in source
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
    assert 'static let readingBedsPath = "/api/reading-beds"' in source
    assert "sendRequest(path: ApplePlaybackStateRuntimeContract.readingBedsPath)" in source
    assert '"/api/bookmarks/\\(encodedJobId)"' not in source
    assert '"\\(bookmarksPath(encodedJobId))/\\(encodedBookmarkId)"' not in source
    assert '"\\(resumeListPath)/\\(encodedJobId)"' not in source
    assert 'sendRequest(path: "/api/reading-beds"' not in source


def test_apple_auth_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_AUTH.read_text(encoding="utf-8")

    assert "enum AppleAuthRuntimeContract" in source
    assert 'static let loginPath = "/api/auth/login"' in source
    assert 'static let oauthPath = "/api/auth/oauth"' in source
    assert 'static let sessionPath = "/api/auth/session"' in source
    assert 'static let runtimeDescriptorPath = "/api/system/runtime"' in source
    assert "sendJSONRequest(path: AppleAuthRuntimeContract.loginPath" in source
    assert "sendJSONRequest(path: AppleAuthRuntimeContract.oauthPath" in source
    assert "sendRequest(path: AppleAuthRuntimeContract.sessionPath)" in source
    assert "sendRequest(path: AppleAuthRuntimeContract.runtimeDescriptorPath)" in source
    for inline_path in [
        'sendJSONRequest(path: "/api/auth/login"',
        'sendJSONRequest(path: "/api/auth/oauth"',
        'sendRequest(path: "/api/auth/session"',
        'sendRequest(path: "/api/system/runtime"',
    ]:
        assert inline_path not in source


def test_apple_pipeline_media_client_uses_runtime_contract_constants() -> None:
    source = (APPLE_SERVICES / "APIClient+PipelineMedia.swift").read_text(encoding="utf-8")
    media_resolver = (
        ROOT
        / "ios/InteractiveReader/InteractiveReader/Utilities/MediaURLResolver.swift"
    ).read_text(encoding="utf-8")
    offline_store = (APPLE_SERVICES / "OfflineMediaStore.swift").read_text(encoding="utf-8")

    assert "enum ApplePipelineMediaRuntimeContract" in source
    assert 'static let jobMediaPathTemplate = "/api/pipelines/jobs/{job_id}/media"' in source
    assert 'static let jobMediaLivePathTemplate = "/api/pipelines/jobs/{job_id}/media/live"' in source
    assert 'static let jobMediaChunkPathTemplate = "/api/pipelines/jobs/{job_id}/media/chunks/{chunk_id}"' in source
    assert 'static let libraryMediaPathTemplate = "/api/library/media/{job_id}"' in source
    assert 'static let libraryMediaFilePathTemplate = "/api/library/media/{job_id}/file/{file_path}"' in source
    assert 'static let libraryMediaFilePrefixTemplate = "/api/library/media/{job_id}/file/"' in source
    assert 'static let libraryMediaPathPrefix = "/api/library/media/"' in source
    assert 'static let jobTimingPathTemplate = "/api/jobs/{job_id}/timing"' in source
    assert 'static let subtitleTvMetadataPathTemplate = "/api/subtitles/jobs/{job_id}/metadata/tv"' in source
    assert 'static let youtubeVideoMetadataPathTemplate = "/api/subtitles/jobs/{job_id}/metadata/youtube"' in source
    assert "ApplePipelineMediaRuntimeContract.jobMediaPath(encoded)" in source
    assert "ApplePipelineMediaRuntimeContract.jobMediaLivePath(encoded)" in source
    assert "ApplePipelineMediaRuntimeContract.jobMediaChunkPath(" in source
    assert "ApplePipelineMediaRuntimeContract.libraryMediaPath(encoded)" in source
    assert "static func libraryMediaFilePath(encodedJobId: String, encodedFilePath: String)" in source
    assert "static func libraryMediaFilePrefix(encodedJobId: String)" in source
    assert "ApplePipelineMediaRuntimeContract.jobTimingPath(encoded)" in source
    assert "ApplePipelineMediaRuntimeContract.subtitleTvMetadataPath(encoded)" in source
    assert "ApplePipelineMediaRuntimeContract.youtubeVideoMetadataPath(encoded)" in source
    assert "ApplePipelineMediaRuntimeContract.libraryMediaFilePath(" in media_resolver
    assert "ApplePipelineMediaRuntimeContract.libraryMediaPathPrefix" in media_resolver
    assert "ApplePipelineMediaRuntimeContract.libraryMediaFilePrefix(encodedJobId: candidate)" in offline_store
    for inline_path in [
        '"/api/pipelines/jobs/\\(encoded)/media"',
        '"/api/pipelines/jobs/\\(encoded)/media/live"',
        '"/api/pipelines/jobs/\\(encodedJob)/media/chunks/\\(encodedChunk)"',
        '"/api/library/media/\\(encoded)"',
        '"/api/jobs/\\(encoded)/timing"',
        '"/api/subtitles/jobs/\\(encoded)/metadata/tv"',
        '"/api/subtitles/jobs/\\(encoded)/metadata/youtube"',
    ]:
        assert inline_path not in source
    assert '"/api/library/media/\\(encodedJobId)/file/\\(encodedPath)"' not in media_resolver
    assert 'range(of: "/api/library/media/")' not in media_resolver
    assert '"/api/library/media/\\(candidate)/file/"' not in offline_store


def test_apple_linguist_client_uses_runtime_contract_constants() -> None:
    source = (APPLE_SERVICES / "APIClient+Linguist.swift").read_text(encoding="utf-8")

    assert "enum AppleLinguistRuntimeContract" in source
    assert 'static let assistantLookupPath = "/api/assistant/lookup"' in source
    assert 'static let lookupCachePathTemplate = "/api/pipelines/jobs/{job_id}/lookup-cache"' in source
    assert 'static let lookupCacheWordPathTemplate = "/api/pipelines/jobs/{job_id}/lookup-cache/{word}"' in source
    assert 'static let lookupCacheBulkPathTemplate = "/api/pipelines/jobs/{job_id}/lookup-cache/bulk"' in source
    assert 'static let lookupCacheSummaryPathTemplate = "/api/pipelines/jobs/{job_id}/lookup-cache/summary"' in source
    assert 'static let audioSynthesisPath = "/api/audio"' in source
    assert "AppleLinguistRuntimeContract.assistantLookupPath" in source
    assert "AppleLinguistRuntimeContract.lookupCacheWordPath(" in source
    assert "AppleLinguistRuntimeContract.lookupCacheBulkPath(encodedJob)" in source
    assert "AppleLinguistRuntimeContract.lookupCacheSummaryPath(encodedJob)" in source
    assert "AppleLinguistRuntimeContract.lookupCachePath(encodedJob)" in source
    assert "AppleLinguistRuntimeContract.audioSynthesisPath" in source
    for inline_path in [
        '"/api/pipelines/jobs/\\(encodedJob)/lookup-cache/\\(encodedWord)"',
        '"/api/pipelines/jobs/\\(encodedJob)/lookup-cache/bulk"',
        '"/api/pipelines/jobs/\\(encodedJob)/lookup-cache/summary"',
        '"/api/pipelines/jobs/\\(encodedJob)/lookup-cache"',
    ]:
        assert inline_path not in source
    assert 'sendJSONRequest(path: "/api/assistant/lookup"' not in source
    assert 'path: "/api/audio",' not in source


def test_apple_notification_client_uses_runtime_contract_constants() -> None:
    source = (APPLE_SERVICES / "APIClient+Notifications.swift").read_text(encoding="utf-8")

    assert "enum AppleNotificationsRuntimeContract" in source
    assert 'static let deviceRegistrationPath = "/api/notifications/devices"' in source
    assert 'static let deviceRemovalPathTemplate = "/api/notifications/devices/{device_id}"' in source
    assert 'static let testPath = "/api/notifications/test"' in source
    assert 'static let richTestPath = "/api/notifications/test/rich"' in source
    assert 'static let preferencesPath = "/api/notifications/preferences"' in source
    assert "AppleNotificationsRuntimeContract.deviceRegistrationPath" in source
    assert "AppleNotificationsRuntimeContract.deviceRemovalPath(encoded)" in source
    assert "AppleNotificationsRuntimeContract.testPath" in source
    assert "AppleNotificationsRuntimeContract.richTestRequestPath(queryItems: queryItems)" in source
    assert "AppleNotificationsRuntimeContract.preferencesPath" in source
    for inline_path in [
        'path: "/api/notifications/devices"',
        'path: "/api/notifications/devices/\\(encoded)"',
        'path: "/api/notifications/test"',
        'var path = "/api/notifications/test/rich"',
        'path: "/api/notifications/preferences"',
    ]:
        assert inline_path not in source


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
    assert "pipelineJobsContract: Self.pipelineJobsContractState(from: descriptor.pipelineJobs)" in source
    assert "pipelineMediaContract: Self.pipelineMediaContractState(from: descriptor.pipelineMedia)" in source
    assert "linguistContract: Self.linguistContractState(from: descriptor.linguist)" in source
    assert "offlineExportsContract: Self.offlineExportsContractState(from: descriptor.offlineExports)" in source
    assert "playbackStateContract: Self.playbackStateContractState(from: descriptor.playbackState)" in source
    assert "notificationsContract: Self.notificationsContractState(from: descriptor.notifications)" in source
    assert "private static func libraryActionsContractState(" in source
    assert "private static func pipelineJobsContractState(" in source
    assert "private static func pipelineMediaContractState(" in source
    assert "private static func linguistContractState(" in source
    assert "private static func offlineExportsContractState(" in source
    assert "private static func playbackStateContractState(" in source
    assert "private static func notificationsContractState(" in source
    for key in [
        "itemPathTemplate",
        "sourceUploadPathTemplate",
        "movePathTemplate",
        "removePathTemplate",
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
        "readingBedsPath",
        "resumeListPath",
        "resumePathTemplate",
        "resumeFilterQuery",
    ]:
        assert f"ApplePlaybackStateRuntimeContract.{key}" in source
    for key in [
        "deviceRegistrationPath",
        "deviceRemovalPathTemplate",
        "testPath",
        "richTestPath",
        "preferencesPath",
    ]:
        assert f"AppleNotificationsRuntimeContract.{key}" in source
