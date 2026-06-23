from __future__ import annotations

from pathlib import Path

from modules.webapi.runtime_descriptor import (
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
    assert descriptor["creation"] == {
        "bookOptionsPath": "/api/books/options",
        "bookJobsPath": "/api/books/jobs",
    }
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
    assert "let applePipeline: ApplePipelineContract?" in source
    assert "let creation: CreationContract?" in source


def test_settings_surfaces_create_contract_runtime_status() -> None:
    source = PLAYBACK_SETTINGS_SECTIONS.read_text(encoding="utf-8")

    assert "enum BackendCreateContractState: Equatable" in source
    assert "case ready(optionsPath: String, jobsPath: String)" in source
    assert "case mismatch(optionsPath: String, jobsPath: String)" in source
    assert "case unavailable" in source
    assert 'title: "Create Contract"' in source
    assert 'accessibilityIdentifier: "settingsCreateContractRow"' in source


def test_apple_create_client_and_settings_share_runtime_contract_paths() -> None:
    creation_source = API_CLIENT_CREATION.read_text(encoding="utf-8")
    settings_source = PLAYBACK_SETTINGS_VIEW.read_text(encoding="utf-8")

    assert "enum AppleCreateRuntimeContract" in creation_source
    assert 'static let bookOptionsPath = "/api/books/options"' in creation_source
    assert 'static let bookJobsPath = "/api/books/jobs"' in creation_source
    assert "sendRequest(path: AppleCreateRuntimeContract.bookOptionsPath)" in creation_source
    assert "path: AppleCreateRuntimeContract.bookJobsPath" in creation_source
    assert "optionsPath == AppleCreateRuntimeContract.bookOptionsPath" in settings_source
    assert "jobsPath == AppleCreateRuntimeContract.bookJobsPath" in settings_source
    assert "return .mismatch(optionsPath: optionsPath, jobsPath: jobsPath)" in settings_source
