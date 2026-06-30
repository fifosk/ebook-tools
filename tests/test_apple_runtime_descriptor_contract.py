from __future__ import annotations

import re
from pathlib import Path

from modules.webapi.runtime_descriptor import (
    APPLE_PIPELINE_DESCRIPTOR,
    AUTH_DESCRIPTOR,
    CLIENT_CONFIG_DESCRIPTOR,
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
WEB_CREATION_TEMPLATES_CLIENT = (
    ROOT / "web" / "src" / "api" / "client" / "creationTemplates.ts"
)
WEB_CREATE_BOOK_CLIENT = ROOT / "web" / "src" / "api" / "createBook.ts"
WEB_JOBS_CLIENT = ROOT / "web" / "src" / "api" / "client" / "jobs.ts"
WEB_SUBTITLES_CLIENT = ROOT / "web" / "src" / "api" / "client" / "subtitles.ts"
WEB_MEDIA_CLIENT = ROOT / "web" / "src" / "api" / "client" / "media.ts"
WEB_RESUME_CLIENT = ROOT / "web" / "src" / "api" / "client" / "resume.ts"
WEB_LIBRARY_CLIENT = ROOT / "web" / "src" / "api" / "client" / "library.ts"
WEB_AUTH_CLIENT = ROOT / "web" / "src" / "api" / "client" / "auth.ts"
WEB_RUNTIME_CONTRACT_CLIENT = (
    ROOT / "web" / "src" / "api" / "client" / "runtimeContract.ts"
)
RUNTIME_DESCRIPTOR_SWIFT_CHECK_SECTIONS = {
    "auth": ("current.auth", AUTH_DESCRIPTOR),
    "clientConfig": ("current.clientConfig", CLIENT_CONFIG_DESCRIPTOR),
    "applePipeline": ("current.applePipeline?", APPLE_PIPELINE_DESCRIPTOR),
    "creation": ("current.creation?", CREATION_DESCRIPTOR),
    "offlineExports": ("current.offlineExports?", OFFLINE_EXPORTS_DESCRIPTOR),
    "pipelineJobs": ("current.pipelineJobs?", PIPELINE_JOBS_DESCRIPTOR),
    "pipelineMedia": ("current.pipelineMedia?", PIPELINE_MEDIA_DESCRIPTOR),
    "linguist": ("current.linguist?", LINGUIST_DESCRIPTOR),
    "libraryActions": ("current.libraryActions?", LIBRARY_ACTIONS_DESCRIPTOR),
    "playbackState": ("current.playbackState?", PLAYBACK_STATE_DESCRIPTOR),
    "notifications": ("current.notifications?", NOTIFICATIONS_DESCRIPTOR),
}
RUNTIME_DESCRIPTOR_SWIFT_MODEL_SECTIONS = {
    "auth": (
        "AuthContract",
        AUTH_DESCRIPTOR,
        {"oauthPath", "logoutPath", "passwordPath", "registerPath"},
    ),
    "clientConfig": (
        "ClientConfig",
        CLIENT_CONFIG_DESCRIPTOR,
        {"credentialEnvironment", "legacyTokenMigration"},
    ),
    "applePipeline": ("ApplePipelineContract", APPLE_PIPELINE_DESCRIPTOR, set()),
    "creation": (
        "CreationContract",
        CREATION_DESCRIPTOR,
        set(CREATION_DESCRIPTOR) - {"bookOptionsPath", "bookJobsPath"},
    ),
    "offlineExports": ("OfflineExportContract", OFFLINE_EXPORTS_DESCRIPTOR, set()),
    "pipelineJobs": (
        "PipelineJobsContract",
        PIPELINE_JOBS_DESCRIPTOR,
        {
            "pausePathTemplate",
            "resumePathTemplate",
            "cancelPathTemplate",
            "accessPathTemplate",
            "metadataRefreshPathTemplate",
            "metadataEnrichPathTemplate",
            "bookMetadataPathTemplate",
            "bookMetadataLookupPathTemplate",
            "coverPathTemplate",
        },
    ),
    "pipelineMedia": (
        "PipelineMediaContract",
        PIPELINE_MEDIA_DESCRIPTOR,
        {
            "chunkOrdering",
            "sentenceImageInfoPathTemplate",
            "sentenceImageBatchPathTemplate",
            "sentenceImageRegeneratePathTemplate",
            "sentenceImageBatchQuery",
        },
    ),
    "linguist": ("LinguistContract", LINGUIST_DESCRIPTOR, set()),
    "libraryActions": (
        "LibraryActionsContract",
        LIBRARY_ACTIONS_DESCRIPTOR,
        {
            "accessPathTemplate",
            "removeMediaPathTemplate",
            "metadataRefreshPathTemplate",
            "reindexPath",
        },
    ),
    "playbackState": ("PlaybackStateContract", PLAYBACK_STATE_DESCRIPTOR, {"readingBedsPath"}),
    "notifications": ("NotificationsContract", NOTIFICATIONS_DESCRIPTOR, set()),
}
RUNTIME_DESCRIPTOR_SWIFT_CONSTANT_SECTIONS = {
    "auth": (API_CLIENT_AUTH, "AppleAuthRuntimeContract", AUTH_DESCRIPTOR, {}),
    "creation": (API_CLIENT_CREATION, "AppleCreateRuntimeContract", CREATION_DESCRIPTOR, {}),
    "offlineExports": (
        API_CLIENT_LIBRARY_JOBS,
        "AppleOfflineExportRuntimeContract",
        OFFLINE_EXPORTS_DESCRIPTOR,
        {
            "sourceKinds": "supportedSourceKinds",
            "playerTypes": "supportedPlayerTypes",
        },
    ),
    "pipelineJobs": (
        API_CLIENT_LIBRARY_JOBS,
        "ApplePipelineJobsRuntimeContract",
        PIPELINE_JOBS_DESCRIPTOR,
        {},
    ),
    "pipelineMedia": (
        APPLE_SERVICES / "APIClient+PipelineMedia.swift",
        "ApplePipelineMediaRuntimeContract",
        PIPELINE_MEDIA_DESCRIPTOR,
        {},
    ),
    "linguist": (
        APPLE_SERVICES / "APIClient+Linguist.swift",
        "AppleLinguistRuntimeContract",
        LINGUIST_DESCRIPTOR,
        {},
    ),
    "libraryActions": (
        API_CLIENT_LIBRARY_JOBS,
        "AppleLibraryRuntimeContract",
        LIBRARY_ACTIONS_DESCRIPTOR,
        {"itemMetadataPathTemplate": "itemPathTemplate"},
    ),
    "playbackState": (
        API_CLIENT_PLAYBACK_STATE,
        "ApplePlaybackStateRuntimeContract",
        PLAYBACK_STATE_DESCRIPTOR,
        {},
    ),
    "notifications": (
        APPLE_SERVICES / "APIClient+Notifications.swift",
        "AppleNotificationsRuntimeContract",
        NOTIFICATIONS_DESCRIPTOR,
        {},
    ),
}


def _assert_compact_source_contains(source: str, snippet: str) -> None:
    assert " ".join(snippet.split()) in " ".join(source.split())


def _swift_array_literal(values: object) -> str:
    assert isinstance(values, tuple)
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def _swift_model_fields(source: str, struct_name: str) -> dict[str, str]:
    match = re.search(
        rf"    struct {re.escape(struct_name)}: Decodable, Equatable \{{(?P<body>.*?)\n    \}}",
        source,
        re.S,
    )
    assert match is not None, struct_name
    return {
        field_match.group("name"): field_match.group("type")
        for field_match in re.finditer(
            r"        let (?P<name>[A-Za-z0-9_]+): (?P<type>\[?[A-Za-z0-9_]+\]?\??)",
            match.group("body"),
        )
    }


def _swift_model_type_for_descriptor_value(value: object, *, optional: bool) -> str:
    if isinstance(value, tuple):
        field_type = "[String]"
    elif isinstance(value, int):
        field_type = "Int"
    else:
        field_type = "String"
    return f"{field_type}?" if optional else field_type


def _swift_enum_static_lets(source: str, enum_name: str) -> dict[str, object]:
    match = re.search(
        rf"enum {re.escape(enum_name)} \{{(?P<body>.*?)\n\}}",
        source,
        re.S,
    )
    assert match is not None, enum_name
    values: dict[str, object] = {}
    for let_match in re.finditer(
        r"    static let (?P<name>[A-Za-z0-9_]+) = (?P<value>.+)",
        match.group("body"),
    ):
        raw_value = let_match.group("value").strip()
        if raw_value.startswith('"'):
            string_match = re.match(r'"(?P<value>[^"]*)"', raw_value)
            assert string_match is not None, raw_value
            values[let_match.group("name")] = string_match.group("value")
        elif raw_value.startswith("["):
            values[let_match.group("name")] = re.findall(r'"([^"]*)"', raw_value)
        elif re.match(r"\d+\b", raw_value):
            values[let_match.group("name")] = int(raw_value.split()[0])
    return values


def _runtime_descriptor_expected_constant_value(value: object) -> object:
    return list(value) if isinstance(value, tuple) else value


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
        "logoutPath": "/api/auth/logout",
        "passwordPath": "/api/auth/password",
        "registerPath": "/api/auth/register",
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
    assert "let logoutPath: String?" in source
    assert "let passwordPath: String?" in source
    assert "let registerPath: String?" in source
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
        "youtubeSubtitlesPath",
        "youtubeSubtitleDownloadPath",
        "youtubeVideoDownloadPath",
        "youtubeSubtitleStreamsPath",
        "youtubeExtractSubtitlesPath",
        "youtubeSubtitleDeletePath",
        "youtubeVideoDeletePath",
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
        "subtitleTvMetadataLookupPathTemplate",
        "youtubeVideoMetadataPathTemplate",
        "youtubeVideoMetadataLookupPathTemplate",
        "subtitleJobResultPathTemplate",
    ]:
        assert f"let {key}: String" in source
    assert "let chunkOrdering: String?" in source
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
    assert "let accessPathTemplate: String?" in source
    assert "let sourceUploadPathTemplate: String" in source
    assert "let movePathTemplate: String" in source
    assert "let removePathTemplate: String" in source
    assert "let removeMediaPathTemplate: String?" in source
    assert "let isbnLookupPath: String" in source
    assert "let isbnApplyPathTemplate: String" in source
    assert "let metadataRefreshPathTemplate: String?" in source
    assert "let metadataEnrichPathTemplate: String" in source
    assert "let reindexPath: String?" in source
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


def test_apple_runtime_descriptor_model_fields_match_backend_sections() -> None:
    source = APPLE_AUTH_MODELS.read_text(encoding="utf-8")

    for section, (struct_name, descriptor, optional_fields) in (
        RUNTIME_DESCRIPTOR_SWIFT_MODEL_SECTIONS.items()
    ):
        fields = _swift_model_fields(source, struct_name)
        assert set(fields) == set(descriptor), section
        for key, value in descriptor.items():
            assert fields[key] == _swift_model_type_for_descriptor_value(
                value,
                optional=key in optional_fields,
            ), f"{section}.{key}"


def test_apple_runtime_contract_constants_match_backend_sections() -> None:
    for section, (
        path,
        enum_name,
        descriptor,
        constant_name_overrides,
    ) in RUNTIME_DESCRIPTOR_SWIFT_CONSTANT_SECTIONS.items():
        constants = _swift_enum_static_lets(path.read_text(encoding="utf-8"), enum_name)
        for key, value in descriptor.items():
            constant_name = constant_name_overrides.get(key, key)
            assert constant_name in constants, f"{section}.{key}"
            assert constants[constant_name] == _runtime_descriptor_expected_constant_value(
                value
            ), f"{section}.{key}"


def test_settings_surfaces_create_contract_runtime_status() -> None:
    source = PLAYBACK_SETTINGS_SECTIONS.read_text(encoding="utf-8")

    assert "enum BackendRuntimeContractState: Equatable" in source
    assert "case ready(summary: String)" in source
    assert "case mismatch(summary: String)" in source
    assert "case unavailable" in source
    assert "var authContractState: BackendRuntimeContractState?" in source
    assert 'title: "Auth Contract"' in source
    assert 'accessibilityIdentifier: "settingsAuthContractRow"' in source
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
    web_templates_source = WEB_CREATION_TEMPLATES_CLIENT.read_text(encoding="utf-8")
    web_create_book_source = WEB_CREATE_BOOK_CLIENT.read_text(encoding="utf-8")
    web_jobs_source = WEB_JOBS_CLIENT.read_text(encoding="utf-8")
    web_subtitles_source = WEB_SUBTITLES_CLIENT.read_text(encoding="utf-8")
    web_media_source = WEB_MEDIA_CLIENT.read_text(encoding="utf-8")
    web_runtime_source = WEB_RUNTIME_CONTRACT_CLIENT.read_text(encoding="utf-8")

    assert "enum AppleCreateRuntimeContract" in creation_source
    assert 'static let bookOptionsPath = "/api/books/options"' in creation_source
    assert 'static let bookJobsPath = "/api/books/jobs"' in creation_source
    assert "static let pipelineFilesMinLimit = 1" in creation_source
    assert "static let pipelineFilesDefaultLimit = 200" in creation_source
    assert "static let pipelineFilesMaxLimit = 500" in creation_source
    assert "static func pipelineFilesListPath(limit: Int = pipelineFilesDefaultLimit) -> String" in creation_source
    assert 'URLQueryItem(name: "limit", value: "\\(boundedLimit)")' in creation_source
    assert "min(max(limit, pipelineFilesMinLimit), pipelineFilesMaxLimit)" in creation_source
    assert CREATION_DESCRIPTOR["pipelineFilesMinLimit"] == 1
    assert CREATION_DESCRIPTOR["pipelineFilesDefaultLimit"] == 200
    assert CREATION_DESCRIPTOR["pipelineFilesMaxLimit"] == 500
    apple_auth_models_source = APPLE_AUTH_MODELS.read_text(encoding="utf-8")
    assert "let pipelineFilesMinLimit: Int?" in apple_auth_models_source
    assert "let pipelineFilesDefaultLimit: Int?" in apple_auth_models_source
    assert "let pipelineFilesMaxLimit: Int?" in apple_auth_models_source
    assert "pipelineFilesMinLimit: 1" in web_runtime_source
    assert "pipelineFilesDefaultLimit: 200" in web_runtime_source
    assert "pipelineFilesMaxLimit: 500" in web_runtime_source
    assert (
        "export const MIN_PIPELINE_FILES_LIMIT = WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesMinLimit;"
        in web_jobs_source
    )
    assert (
        "export const DEFAULT_PIPELINE_FILES_LIMIT = WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesDefaultLimit;"
        in web_jobs_source
    )
    assert (
        "export const MAX_PIPELINE_FILES_LIMIT = WEB_CREATE_RUNTIME_CONTRACT.pipelineFilesMaxLimit;"
        in web_jobs_source
    )
    expected_constants = {
        "pipelineFilesPath": "/api/pipelines/files",
        "pipelineContentIndexPath": "/api/pipelines/files/content-index",
        "pipelineUploadPath": "/api/pipelines/files/upload",
        "pipelineCoverUploadPath": "/api/pipelines/covers/upload",
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
        "bookMetadataPreviewPath": "/api/pipelines/metadata/book/lookup",
        "bookMetadataCacheClearPath": "/api/pipelines/metadata/book/cache/clear",
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
    assert "func fetchPipelineFiles(limit: Int = AppleCreateRuntimeContract.pipelineFilesDefaultLimit)" in creation_source
    assert "sendRequest(path: AppleCreateRuntimeContract.pipelineFilesListPath(limit: limit))" in creation_source
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
    for key in [
        "bookOptionsPath",
        "bookJobsPath",
        "pipelineJobsPath",
        "pipelineFilesPath",
        "pipelineContentIndexPath",
        "pipelineUploadPath",
        "pipelineCoverUploadPath",
        "pipelineIntakeStatusPath",
        "pipelineDefaultsPath",
        "pipelineLlmModelsPath",
        "pipelineSearchPath",
        "imageNodeAvailabilityPath",
        "audioVoicesPath",
        "acquisitionProvidersPath",
        "acquisitionDiscoverPath",
        "acquisitionAcquirePath",
        "acquisitionArtifactPreparePathTemplate",
        "acquisitionJobsPath",
        "acquisitionJobPathTemplate",
        "subtitleSourcesPath",
        "subtitleDeleteSourcePath",
        "subtitleModelsPath",
        "subtitleTvMetadataPreviewPath",
        "subtitleTvMetadataCacheClearPath",
        "youtubeMetadataPreviewPath",
        "youtubeMetadataCacheClearPath",
        "bookMetadataPreviewPath",
        "bookMetadataCacheClearPath",
        "youtubeLibraryPath",
        "youtubeSubtitlesPath",
        "youtubeSubtitleDownloadPath",
        "youtubeVideoDownloadPath",
        "youtubeSubtitleStreamsPath",
        "youtubeExtractSubtitlesPath",
        "youtubeSubtitleDeletePath",
        "youtubeVideoDeletePath",
        "youtubeDubPath",
        "subtitleJobsPath",
        "templateListPath",
        "templatePathTemplate",
    ]:
        assert f"{key}: '{CREATION_DESCRIPTOR[key]}'" in web_runtime_source
        assert f"WEB_CREATE_RUNTIME_CONTRACT.{key}" in (
            web_jobs_source
            + web_media_source
            + web_subtitles_source
            + web_templates_source
            + web_create_book_source
        )
    for key in [
        "assistantLookupPath",
        "audioSynthesisPath",
    ]:
        assert f"{key}: '{LINGUIST_DESCRIPTOR[key]}'" in web_runtime_source
        assert f"WEB_LINGUIST_RUNTIME_CONTRACT.{key}" in (
            web_media_source + web_subtitles_source
        )
    assert (
        "replaceRuntimePathParameter("
        in web_templates_source + web_jobs_source
    )
    assert (
        "replaceRuntimePathParameter(\n"
        "      WEB_CREATE_RUNTIME_CONTRACT.acquisitionArtifactPreparePathTemplate"
        in web_jobs_source
    )
    assert (
        "replaceRuntimePathParameter(\n"
        "      WEB_CREATE_RUNTIME_CONTRACT.acquisitionJobPathTemplate"
        in web_jobs_source
    )
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
    assert (
        '("pipelineFilesMinLimit", creation.pipelineFilesMinLimit, AppleCreateRuntimeContract.pipelineFilesMinLimit)'
        in settings_source
    )
    assert (
        '("pipelineFilesDefaultLimit", creation.pipelineFilesDefaultLimit, AppleCreateRuntimeContract.pipelineFilesDefaultLimit)'
        in settings_source
    )
    assert (
        '("pipelineFilesMaxLimit", creation.pipelineFilesMaxLimit, AppleCreateRuntimeContract.pipelineFilesMaxLimit)'
        in settings_source
    )
    assert "return .mismatch(summary: allMismatches.joined(separator: \" · \"))" in settings_source
    assert "\\(expectedPaths.count) endpoints" in settings_source


def test_standalone_swift_runtime_descriptor_payload_check_covers_runtime_contract_sections() -> None:
    source = APPLE_RUNTIME_DESCRIPTOR_PAYLOAD_CHECK.read_text(encoding="utf-8")
    assert '"healthPath": "/_health"' in source
    assert '"health_path": "/_health"' in source
    for section, (accessor, descriptor) in RUNTIME_DESCRIPTOR_SWIFT_CHECK_SECTIONS.items():
        assert f'"{section}": {{' in source
        for key, value in descriptor.items():
            if isinstance(value, str):
                assert f'"{key}": "{value}"' in source
                _assert_compact_source_contains(
                    source,
                    f'{accessor}.{key} == "{value}"',
                )
                continue
            if isinstance(value, int):
                assert f'"{key}": {value}' in source
                _assert_compact_source_contains(
                    source,
                    f"{accessor}.{key} == {value}",
                )
                continue
            assert f'"{key}": [' in source
            for item in value:
                assert f'"{item}"' in source
            _assert_compact_source_contains(
                source,
                f"{accessor}.{key} == {_swift_array_literal(value)}",
            )


def test_web_auth_client_shares_runtime_contract_paths() -> None:
    source = WEB_AUTH_CLIENT.read_text(encoding="utf-8")
    runtime_source = WEB_RUNTIME_CONTRACT_CLIENT.read_text(encoding="utf-8")
    apple_source = API_CLIENT_AUTH.read_text(encoding="utf-8")

    assert "WEB_AUTH_RUNTIME_CONTRACT.loginPath" in source
    assert "WEB_AUTH_RUNTIME_CONTRACT.oauthPath" in source
    assert "WEB_AUTH_RUNTIME_CONTRACT.sessionPath" in source
    assert "WEB_AUTH_RUNTIME_CONTRACT.logoutPath" in source
    assert "WEB_AUTH_RUNTIME_CONTRACT.passwordPath" in source
    assert "WEB_AUTH_RUNTIME_CONTRACT.registerPath" in source
    assert f"loginPath: '{AUTH_DESCRIPTOR['loginPath']}'" in runtime_source
    assert f"oauthPath: '{AUTH_DESCRIPTOR['oauthPath']}'" in runtime_source
    assert f"sessionPath: '{AUTH_DESCRIPTOR['sessionPath']}'" in runtime_source
    assert f"logoutPath: '{AUTH_DESCRIPTOR['logoutPath']}'" in runtime_source
    assert f"passwordPath: '{AUTH_DESCRIPTOR['passwordPath']}'" in runtime_source
    assert f"registerPath: '{AUTH_DESCRIPTOR['registerPath']}'" in runtime_source
    assert "skipAuth: true" in source
    assert "sendJSONRequest(path: AppleAuthRuntimeContract.loginPath" in apple_source
    assert "sendJSONRequest(path: AppleAuthRuntimeContract.oauthPath" in apple_source
    assert "sendRequest(path: AppleAuthRuntimeContract.sessionPath" in apple_source
    assert 'static let logoutPath = "/api/auth/logout"' in apple_source
    assert 'static let passwordPath = "/api/auth/password"' in apple_source
    assert 'static let registerPath = "/api/auth/register"' in apple_source
    assert 'apiFetch(\'/api/auth/logout\'' not in source
    assert 'apiFetch(\'/api/auth/password\'' not in source
    assert "'/api/auth/register'" not in source
    assert 'sendRequest(path: "/api/auth/login"' not in apple_source
    assert 'sendRequest(path: "/api/auth/session"' not in apple_source


def test_web_playback_clients_share_runtime_contract_paths() -> None:
    jobs_source = WEB_JOBS_CLIENT.read_text(encoding="utf-8")
    media_source = WEB_MEDIA_CLIENT.read_text(encoding="utf-8")
    resume_source = WEB_RESUME_CLIENT.read_text(encoding="utf-8")
    subtitles_source = WEB_SUBTITLES_CLIENT.read_text(encoding="utf-8")
    runtime_source = WEB_RUNTIME_CONTRACT_CLIENT.read_text(encoding="utf-8")

    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.jobMediaPathTemplate" in media_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.jobMediaLivePathTemplate" in media_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.jobTimingPathTemplate" in jobs_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.subtitleTvMetadataPathTemplate" in subtitles_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.subtitleTvMetadataLookupPathTemplate" in subtitles_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.youtubeVideoMetadataPathTemplate" in subtitles_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.youtubeVideoMetadataLookupPathTemplate" in subtitles_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.subtitleJobResultPathTemplate" in subtitles_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.sentenceImageInfoPathTemplate" in media_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.sentenceImageBatchPathTemplate" in media_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.sentenceImageRegeneratePathTemplate" in media_source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.sentenceImageBatchQuery" in media_source
    assert (
        f"jobMediaPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['jobMediaPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"jobMediaLivePathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['jobMediaLivePathTemplate']}'"
        in runtime_source
    )
    assert (
        f"jobTimingPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['jobTimingPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"subtitleTvMetadataPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['subtitleTvMetadataPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"subtitleTvMetadataLookupPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['subtitleTvMetadataLookupPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"youtubeVideoMetadataPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['youtubeVideoMetadataPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"youtubeVideoMetadataLookupPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['youtubeVideoMetadataLookupPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"subtitleJobResultPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['subtitleJobResultPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"sentenceImageInfoPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['sentenceImageInfoPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"sentenceImageBatchPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['sentenceImageBatchPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"sentenceImageRegeneratePathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['sentenceImageRegeneratePathTemplate']}'"
        in runtime_source
    )
    assert (
        f"sentenceImageBatchQuery: '{PIPELINE_MEDIA_DESCRIPTOR['sentenceImageBatchQuery']}'"
        in runtime_source
    )
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.listPath" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.statusPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.eventStreamPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.pausePathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.resumePathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.cancelPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.restartPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.deletePathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.accessPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.metadataRefreshPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.metadataEnrichPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.bookMetadataPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.bookMetadataLookupPathTemplate" in jobs_source
    assert "WEB_PIPELINE_JOBS_RUNTIME_CONTRACT.coverPathTemplate" in jobs_source
    assert f"listPath: '{PIPELINE_JOBS_DESCRIPTOR['listPath']}'" in runtime_source
    assert (
        f"statusPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['statusPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"eventStreamPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['eventStreamPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"pausePathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['pausePathTemplate']}'"
        in runtime_source
    )
    assert (
        f"resumePathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['resumePathTemplate']}'"
        in runtime_source
    )
    assert (
        f"cancelPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['cancelPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"restartPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['restartPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"deletePathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['deletePathTemplate']}'"
        in runtime_source
    )
    assert (
        f"accessPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['accessPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"metadataRefreshPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['metadataRefreshPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"metadataEnrichPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['metadataEnrichPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"bookMetadataPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['bookMetadataPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"bookMetadataLookupPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['bookMetadataLookupPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"coverPathTemplate: '{PIPELINE_JOBS_DESCRIPTOR['coverPathTemplate']}'"
        in runtime_source
    )
    assert "WEB_CREATE_RUNTIME_CONTRACT.audioVoicesPath" in media_source
    assert f"audioVoicesPath: '{CREATION_DESCRIPTOR['audioVoicesPath']}'" in runtime_source
    assert "WEB_LINGUIST_RUNTIME_CONTRACT.audioSynthesisPath" in media_source
    assert f"audioSynthesisPath: '{LINGUIST_DESCRIPTOR['audioSynthesisPath']}'" in runtime_source
    assert "WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheWordPathTemplate" in jobs_source
    assert "WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheBulkPathTemplate" in jobs_source
    assert "WEB_LINGUIST_RUNTIME_CONTRACT.lookupCacheSummaryPathTemplate" in jobs_source
    assert (
        f"lookupCacheWordPathTemplate: '{LINGUIST_DESCRIPTOR['lookupCacheWordPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"lookupCacheBulkPathTemplate: '{LINGUIST_DESCRIPTOR['lookupCacheBulkPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"lookupCacheSummaryPathTemplate: '{LINGUIST_DESCRIPTOR['lookupCacheSummaryPathTemplate']}'"
        in runtime_source
    )
    assert "WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.bookmarksPathTemplate" in media_source
    assert "WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.bookmarkDeletePathTemplate" in media_source
    assert (
        f"bookmarksPathTemplate: '{PLAYBACK_STATE_DESCRIPTOR['bookmarksPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"bookmarkDeletePathTemplate: '{PLAYBACK_STATE_DESCRIPTOR['bookmarkDeletePathTemplate']}'"
        in runtime_source
    )
    assert "WEB_OFFLINE_EXPORT_RUNTIME_CONTRACT.createPath" in media_source
    assert "WEB_OFFLINE_EXPORT_RUNTIME_CONTRACT.downloadPathTemplate" in media_source
    assert f"createPath: '{OFFLINE_EXPORTS_DESCRIPTOR['createPath']}'" in runtime_source
    assert (
        f"downloadPathTemplate: '{OFFLINE_EXPORTS_DESCRIPTOR['downloadPathTemplate']}'"
        in runtime_source
    )
    assert "sourceKinds: ['job', 'library']" in runtime_source
    assert "playerTypes: ['interactive-text']" in runtime_source
    assert "resolveExportDownloadUrl" in media_source
    assert "replaceRuntimePathParameter(" in media_source
    assert "WEB_CREATE_RUNTIME_CONTRACT.pipelineSearchPath" in media_source
    assert "WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumeListPath" in resume_source
    assert "WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumePathTemplate" in resume_source
    assert "WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumeFilterQuery" in resume_source
    assert (
        f"resumeListPath: '{PLAYBACK_STATE_DESCRIPTOR['resumeListPath']}'"
        in runtime_source
    )
    assert (
        f"resumePathTemplate: '{PLAYBACK_STATE_DESCRIPTOR['resumePathTemplate']}'"
        in runtime_source
    )
    assert (
        f"resumeFilterQuery: '{PLAYBACK_STATE_DESCRIPTOR['resumeFilterQuery']}'"
        in runtime_source
    )
    assert "replaceRuntimePathParameter(" in media_source
    assert "replaceRuntimePathParameters(" in media_source
    assert "replaceRuntimePathParameter(" in resume_source
    assert "params.append(WEB_PLAYBACK_STATE_RUNTIME_CONTRACT.resumeFilterQuery, jobId)" in resume_source


def test_apple_library_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_LIBRARY_JOBS.read_text(encoding="utf-8")

    assert "enum AppleLibraryRuntimeContract" in source
    assert 'static let itemsPath = "/api/library/items"' in source
    assert 'static let itemPathTemplate = "/api/library/items/{job_id}"' in source
    assert 'static let accessPathTemplate = "/api/library/items/{job_id}/access"' in source
    assert 'static let sourceUploadPathTemplate = "/api/library/items/{job_id}/upload-source"' in source
    assert 'static let movePathTemplate = "/api/library/move/{job_id}"' in source
    assert 'static let removePathTemplate = "/api/library/remove/{job_id}"' in source
    assert 'static let removeMediaPathTemplate = "/api/library/remove-media/{job_id}"' in source
    assert 'static let isbnLookupPath = "/api/library/isbn/lookup"' in source
    assert 'static let isbnApplyPathTemplate = "/api/library/items/{job_id}/isbn"' in source
    assert 'static let metadataRefreshPathTemplate = "/api/library/items/{job_id}/refresh"' in source
    assert 'static let metadataEnrichPathTemplate = "/api/library/items/{job_id}/enrich"' in source
    assert 'static let reindexPath = "/api/library/reindex"' in source
    assert "static func itemPath(_ encodedJobId: String) -> String" in source
    assert "static func sourceUploadPath(_ encodedJobId: String) -> String" in source
    assert "static func accessPath(_ encodedJobId: String) -> String" in source
    assert "static func movePath(_ encodedJobId: String) -> String" in source
    assert "static func removePath(_ encodedJobId: String) -> String" in source
    assert "static func removeMediaPath(_ encodedJobId: String) -> String" in source
    assert "static func isbnApplyPath(_ encodedJobId: String) -> String" in source
    assert "static func metadataRefreshPath(_ encodedJobId: String) -> String" in source
    assert "static func metadataEnrichPath(_ encodedJobId: String) -> String" in source
    assert 'itemPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'accessPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'sourceUploadPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'removeMediaPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'isbnApplyPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
    assert 'metadataRefreshPathTemplate.replacingOccurrences(of: "{job_id}", with: encodedJobId)' in source
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


def test_web_library_client_shares_runtime_contract_paths() -> None:
    source = WEB_LIBRARY_CLIENT.read_text(encoding="utf-8")
    runtime_source = WEB_RUNTIME_CONTRACT_CLIENT.read_text(encoding="utf-8")

    for key, path in LIBRARY_ACTIONS_DESCRIPTOR.items():
        assert f"{key}: '{path}'" in runtime_source
    assert (
        f"libraryMediaPathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['libraryMediaPathTemplate']}'"
        in runtime_source
    )
    assert (
        f"libraryMediaFilePathTemplate: '{PIPELINE_MEDIA_DESCRIPTOR['libraryMediaFilePathTemplate']}'"
        in runtime_source
    )
    for key in [
        "movePathTemplate",
        "itemsPath",
        "removePathTemplate",
        "removeMediaPathTemplate",
        "itemMetadataPathTemplate",
        "accessPathTemplate",
        "metadataRefreshPathTemplate",
        "metadataEnrichPathTemplate",
        "reindexPath",
        "sourceUploadPathTemplate",
        "isbnApplyPathTemplate",
        "isbnLookupPath",
    ]:
        assert f"WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.{key}" in source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.libraryMediaFilePathTemplate" in source
    assert "WEB_PIPELINE_MEDIA_RUNTIME_CONTRACT.libraryMediaPathTemplate" in source
    assert "replaceRuntimePathParameter(" in source
    assert (
        "`${WEB_LIBRARY_ACTIONS_RUNTIME_CONTRACT.isbnLookupPath}?isbn=${encodeURIComponent(isbn)}`"
        in source
    )


def test_apple_pipeline_job_client_uses_runtime_contract_constants() -> None:
    source = API_CLIENT_LIBRARY_JOBS.read_text(encoding="utf-8")

    assert "enum ApplePipelineJobsRuntimeContract" in source
    assert 'static let listPath = "/api/pipelines/jobs"' in source
    assert 'static let statusPathTemplate = "/api/pipelines/{job_id}"' in source
    assert 'static let eventStreamPathTemplate = "/api/pipelines/{job_id}/events"' in source
    assert 'static let deletePathTemplate = "/api/pipelines/jobs/{job_id}/delete"' in source
    assert 'static let restartPathTemplate = "/api/pipelines/jobs/{job_id}/restart"' in source
    assert 'static let cacheBusterQuery = "ts"' in source
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
    assert "URLQueryItem(name: cacheBusterQuery" in source
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
        "cacheBusterQuery",
    ]:
        assert f"ApplePipelineJobsRuntimeContract.{key}" in source
    assert '"cacheBusterQuery", pipelineJobs.cacheBusterQuery, ApplePipelineJobsRuntimeContract.cacheBusterQuery' in source


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
        "subtitleTvMetadataLookupPathTemplate",
        "youtubeVideoMetadataPathTemplate",
        "youtubeVideoMetadataLookupPathTemplate",
        "subtitleJobResultPathTemplate",
        "chunkOrdering",
    ]:
        assert f"ApplePipelineMediaRuntimeContract.{key}" in source
    assert '"chunkOrdering", pipelineMedia.chunkOrdering, ApplePipelineMediaRuntimeContract.chunkOrdering' in source


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
    assert 'static let supportedPlayerTypes = ["interactive-text"]' in source
    assert "static let playerType = supportedPlayerTypes[0]" in source
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
    assert 'static let logoutPath = "/api/auth/logout"' in source
    assert 'static let passwordPath = "/api/auth/password"' in source
    assert 'static let registerPath = "/api/auth/register"' in source
    assert 'static let tokenTransport = "Authorization: Bearer"' in source
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
    assert 'static let sentenceImageInfoPathTemplate = "/api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}"' in source
    assert 'static let sentenceImageBatchPathTemplate = "/api/pipelines/jobs/{job_id}/media/images/sentences/batch"' in source
    assert 'static let sentenceImageRegeneratePathTemplate = "/api/pipelines/jobs/{job_id}/media/images/sentences/{sentence_number}/regenerate"' in source
    assert 'static let sentenceImageBatchQuery = "sentence_numbers"' in source
    assert 'static let subtitleTvMetadataPathTemplate = "/api/subtitles/jobs/{job_id}/metadata/tv"' in source
    assert 'static let youtubeVideoMetadataPathTemplate = "/api/subtitles/jobs/{job_id}/metadata/youtube"' in source
    assert "ApplePipelineMediaRuntimeContract.jobMediaPath(encoded)" in source
    assert "ApplePipelineMediaRuntimeContract.jobMediaLivePath(encoded)" in source
    assert "ApplePipelineMediaRuntimeContract.jobMediaChunkPath(" in source
    assert "static func sentenceImageInfoPath(encodedJobId: String, encodedSentenceNumber: String)" in source
    assert "static func sentenceImageBatchPath(_ encodedJobId: String)" in source
    assert "static func sentenceImageRegeneratePath(encodedJobId: String, encodedSentenceNumber: String)" in source
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

    assert "authContract: Self.authContractState(from: descriptor.auth)" in source
    assert "libraryActionsContract: Self.libraryActionsContractState(from: descriptor.libraryActions)" in source
    assert "pipelineJobsContract: Self.pipelineJobsContractState(from: descriptor.pipelineJobs)" in source
    assert "pipelineMediaContract: Self.pipelineMediaContractState(from: descriptor.pipelineMedia)" in source
    assert "linguistContract: Self.linguistContractState(from: descriptor.linguist)" in source
    assert "offlineExportsContract: Self.offlineExportsContractState(from: descriptor.offlineExports)" in source
    assert "playbackStateContract: Self.playbackStateContractState(from: descriptor.playbackState)" in source
    assert "notificationsContract: Self.notificationsContractState(from: descriptor.notifications)" in source
    assert "private static func authContractState(" in source
    assert "private static func libraryActionsContractState(" in source
    assert "private static func pipelineJobsContractState(" in source
    assert "private static func pipelineMediaContractState(" in source
    assert "private static func linguistContractState(" in source
    assert "private static func offlineExportsContractState(" in source
    assert "private static func playbackStateContractState(" in source
    assert "private static func notificationsContractState(" in source
    for key in [
        "itemPathTemplate",
        "accessPathTemplate",
        "sourceUploadPathTemplate",
        "movePathTemplate",
        "removePathTemplate",
        "removeMediaPathTemplate",
        "isbnApplyPathTemplate",
        "metadataRefreshPathTemplate",
        "metadataEnrichPathTemplate",
        "reindexPath",
    ]:
        assert f"AppleLibraryRuntimeContract.{key}" in source
    assert "AppleOfflineExportRuntimeContract.downloadPathTemplate" in source
    assert "AppleOfflineExportRuntimeContract.supportedSourceKinds" in source
    assert "AppleOfflineExportRuntimeContract.supportedPlayerTypes" in source
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
