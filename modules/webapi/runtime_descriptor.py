"""Public non-secret runtime descriptor for app pipeline preflights."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

API_BASE_URL_ENVIRONMENT = (
    "INTERACTIVE_READER_API_BASE_URL",
    "EBOOK_TOOLS_API_BASE_URL",
    "E2E_API_BASE_URL",
)
CREDENTIAL_ENVIRONMENT = ("E2E_USERNAME", "E2E_PASSWORD")
APPLE_PIPELINE_SIMULATOR_PROFILES = ("ios", "ipados", "tvos", "tvos-cinema")
APPLE_PIPELINE_DEVICE_PROFILES = ("iphone", "ipad", "appletv", "cinema")
AUTH_DESCRIPTOR = {
    "loginPath": "/api/auth/login",
    "sessionPath": "/api/auth/session",
    "tokenTransport": "Authorization: Bearer",
}
CLIENT_CONFIG_DESCRIPTOR = {
    "apiBaseUrlEnvironment": API_BASE_URL_ENVIRONMENT,
    "credentialEnvironment": CREDENTIAL_ENVIRONMENT,
    "sessionTokenStorage": "device-keychain",
    "legacyTokenMigration": "userdefaults-authToken",
}
APPLE_PIPELINE_DESCRIPTOR = {
    "manifestId": "ebook-tools",
    "simulatorProfiles": APPLE_PIPELINE_SIMULATOR_PROFILES,
    "deviceProfiles": APPLE_PIPELINE_DEVICE_PROFILES,
}
CREATION_DESCRIPTOR = {
    "bookOptionsPath": "/api/books/options",
    "bookJobsPath": "/api/books/jobs",
    "pipelineFilesPath": "/api/pipelines/files",
    "pipelineContentIndexPath": "/api/pipelines/files/content-index",
    "pipelineUploadPath": "/api/pipelines/files/upload",
    "pipelineJobsPath": "/api/pipelines",
    "pipelineIntakeStatusPath": "/api/pipelines/intake/status",
    "subtitleSourcesPath": "/api/subtitles/sources",
    "subtitleModelsPath": "/api/subtitles/models",
    "subtitleJobsPath": "/api/subtitles/jobs",
    "youtubeLibraryPath": "/api/subtitles/youtube/library",
    "youtubeSubtitleStreamsPath": "/api/subtitles/youtube/subtitle-streams",
    "youtubeExtractSubtitlesPath": "/api/subtitles/youtube/extract-subtitles",
    "youtubeDubPath": "/api/subtitles/youtube/dub",
}
ALLOWED_PUBLIC_METADATA_KEYS = frozenset(
    {
        "legacytokenmigration",
        "sessiontokenstorage",
        "tokentransport",
    }
)
SENSITIVE_KEY_MARKERS = ("password", "secret", "token")


def build_runtime_descriptor(version: str) -> dict[str, object]:
    """Return non-secret runtime facts safe for simulator/device preflights."""

    payload: dict[str, object] = {
        "status": "ok",
        "app": "ebook-tools",
        "service": "ebook-tools-api",
        "version": version,
        "healthPath": "/_health",
        "auth": _copy_public_descriptor_section(AUTH_DESCRIPTOR),
        "clientConfig": _copy_public_descriptor_section(CLIENT_CONFIG_DESCRIPTOR),
        "applePipeline": _copy_public_descriptor_section(APPLE_PIPELINE_DESCRIPTOR),
        "creation": _copy_public_descriptor_section(CREATION_DESCRIPTOR),
    }
    assert_runtime_descriptor_is_public(payload)
    return payload


def assert_runtime_descriptor_is_public(payload: object) -> None:
    """Raise if the public descriptor contains secret-like metadata keys."""

    exposed_keys = find_sensitive_descriptor_keys(payload)
    if exposed_keys:
        joined_keys = ", ".join(exposed_keys)
        raise ValueError(
            f"Runtime descriptor exposes secret-like metadata keys: {joined_keys}"
        )


def find_sensitive_descriptor_keys(payload: object) -> list[str]:
    """Return secret-like keys that are not allowed public metadata labels."""

    exposed_keys = {key.lower() for key in _walk_descriptor_keys(payload)}
    return sorted(
        key
        for key in exposed_keys
        if key not in ALLOWED_PUBLIC_METADATA_KEYS
        and any(marker in key for marker in SENSITIVE_KEY_MARKERS)
    )


def _walk_descriptor_keys(value: object) -> list[str]:
    if isinstance(value, Mapping):
        keys: list[str] = []
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_descriptor_keys(child))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        keys = []
        for child in value:
            keys.extend(_walk_descriptor_keys(child))
        return keys
    return []


def _copy_public_descriptor_section(section: Mapping[str, object]) -> dict[str, object]:
    return {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in section.items()
    }
