from __future__ import annotations

from pathlib import Path

from modules.webapi.runtime_descriptor import (
    CREATION_DESCRIPTOR,
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
    ]:
        assert f"let {key}: String?" in source
    assert "let applePipeline: ApplePipelineContract?" in source
    assert "let creation: CreationContract?" in source


def test_settings_surfaces_create_contract_runtime_status() -> None:
    source = PLAYBACK_SETTINGS_SECTIONS.read_text(encoding="utf-8")

    assert "enum BackendCreateContractState: Equatable" in source
    assert "case ready(summary: String)" in source
    assert "case mismatch(summary: String)" in source
    assert "case unavailable" in source
    assert 'title: "Create Contract"' in source
    assert 'accessibilityIdentifier: "settingsCreateContractRow"' in source


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
    }
    for key, path in expected_constants.items():
        assert f'static let {key} = "{path}"' in creation_source
        assert f"AppleCreateRuntimeContract.{key}" in settings_source
    assert "sendRequest(path: AppleCreateRuntimeContract.bookOptionsPath)" in creation_source
    assert "path: AppleCreateRuntimeContract.bookJobsPath" in creation_source
    assert '("bookOptionsPath", creation.bookOptionsPath, AppleCreateRuntimeContract.bookOptionsPath)' in settings_source
    assert '("bookJobsPath", creation.bookJobsPath, AppleCreateRuntimeContract.bookJobsPath)' in settings_source
    assert "return .mismatch(summary: mismatches.joined(separator: \" · \"))" in settings_source
