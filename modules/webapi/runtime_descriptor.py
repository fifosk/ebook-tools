"""Public non-secret runtime descriptor for app pipeline preflights."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

API_BASE_URL_ENVIRONMENT = (
    "INTERACTIVE_READER_API_BASE_URL",
    "EBOOK_TOOLS_API_BASE_URL",
    "E2E_API_BASE_URL",
)
CREDENTIAL_ENVIRONMENT = (
    "E2E_USERNAME",
    "E2E_PASSWORD",
    "E2E_AUTH_TOKEN",
    "EBOOKTOOLS_SESSION_TOKEN",
)
APPLE_PIPELINE_SIMULATOR_PROFILES = ("ios", "ipados", "tvos", "tvos-cinema")
APPLE_PIPELINE_DEVICE_PROFILES = ("iphone", "ipad", "appletv", "cinema")
AUTH_DESCRIPTOR = {
    "loginPath": "/api/auth/login",
    "oauthPath": "/api/auth/oauth",
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
OFFLINE_EXPORTS_DESCRIPTOR = {
    "createPath": "/api/exports",
    "downloadPathTemplate": "/api/exports/{export_id}/download",
    "sourceKinds": ("job", "library"),
    "playerTypes": ("interactive-text",),
}
PIPELINE_JOBS_DESCRIPTOR = {
    "listPath": "/api/pipelines/jobs",
    "statusPathTemplate": "/api/pipelines/{job_id}",
    "eventStreamPathTemplate": "/api/pipelines/{job_id}/events",
    "deletePathTemplate": "/api/pipelines/jobs/{job_id}/delete",
    "restartPathTemplate": "/api/pipelines/jobs/{job_id}/restart",
    "cacheBusterQuery": "ts",
}
PIPELINE_MEDIA_DESCRIPTOR = {
    "jobMediaPathTemplate": "/api/pipelines/jobs/{job_id}/media",
    "jobMediaLivePathTemplate": "/api/pipelines/jobs/{job_id}/media/live",
    "jobMediaChunkPathTemplate": "/api/pipelines/jobs/{job_id}/media/chunks/{chunk_id}",
    "libraryMediaPathTemplate": "/api/library/media/{job_id}",
    "libraryMediaFilePathTemplate": "/api/library/media/{job_id}/file/{file_path}",
    "jobTimingPathTemplate": "/api/jobs/{job_id}/timing",
    "subtitleTvMetadataPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/tv",
    "youtubeVideoMetadataPathTemplate": "/api/subtitles/jobs/{job_id}/metadata/youtube",
    "chunkOrdering": "sentenceRange",
}
LINGUIST_DESCRIPTOR = {
    "assistantLookupPath": "/api/assistant/lookup",
    "lookupCachePathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache",
    "lookupCacheWordPathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache/{word}",
    "lookupCacheBulkPathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache/bulk",
    "lookupCacheSummaryPathTemplate": "/api/pipelines/jobs/{job_id}/lookup-cache/summary",
    "audioSynthesisPath": "/api/audio",
}
LIBRARY_ACTIONS_DESCRIPTOR = {
    "itemsPath": "/api/library/items",
    "itemMetadataPathTemplate": "/api/library/items/{job_id}",
    "sourceUploadPathTemplate": "/api/library/items/{job_id}/upload-source",
    "movePathTemplate": "/api/library/move/{job_id}",
    "removePathTemplate": "/api/library/remove/{job_id}",
    "isbnLookupPath": "/api/library/isbn/lookup",
    "isbnApplyPathTemplate": "/api/library/items/{job_id}/isbn",
    "metadataEnrichPathTemplate": "/api/library/items/{job_id}/enrich",
}
PLAYBACK_STATE_DESCRIPTOR = {
    "bookmarksPathTemplate": "/api/bookmarks/{job_id}",
    "bookmarkDeletePathTemplate": "/api/bookmarks/{job_id}/{bookmark_id}",
    "readingBedsPath": "/api/reading-beds",
    "resumeListPath": "/api/resume",
    "resumePathTemplate": "/api/resume/{job_id}",
    "resumeFilterQuery": "job_id",
}
NOTIFICATIONS_DESCRIPTOR = {
    "deviceRegistrationPath": "/api/notifications/devices",
    "deviceRemovalPathTemplate": "/api/notifications/devices/{device_id}",
    "testPath": "/api/notifications/test",
    "richTestPath": "/api/notifications/test/rich",
    "preferencesPath": "/api/notifications/preferences",
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

    payload = _copy_runtime_descriptor_template()
    payload["version"] = version
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


def _copy_runtime_descriptor_template() -> dict[str, object]:
    return {
        key: (
            _copy_public_descriptor_section(value)
            if isinstance(value, Mapping)
            else value
        )
        for key, value in _PUBLIC_RUNTIME_DESCRIPTOR_TEMPLATE.items()
    }


_PUBLIC_RUNTIME_DESCRIPTOR_TEMPLATE: dict[str, object] = {
    "status": "ok",
    "app": "ebook-tools",
    "service": "ebook-tools-api",
    "version": "",
    "healthPath": "/_health",
    "auth": AUTH_DESCRIPTOR,
    "clientConfig": CLIENT_CONFIG_DESCRIPTOR,
    "applePipeline": APPLE_PIPELINE_DESCRIPTOR,
    "creation": CREATION_DESCRIPTOR,
    "offlineExports": OFFLINE_EXPORTS_DESCRIPTOR,
    "pipelineJobs": PIPELINE_JOBS_DESCRIPTOR,
    "pipelineMedia": PIPELINE_MEDIA_DESCRIPTOR,
    "linguist": LINGUIST_DESCRIPTOR,
    "libraryActions": LIBRARY_ACTIONS_DESCRIPTOR,
    "playbackState": PLAYBACK_STATE_DESCRIPTOR,
    "notifications": NOTIFICATIONS_DESCRIPTOR,
}
assert_runtime_descriptor_is_public(_PUBLIC_RUNTIME_DESCRIPTOR_TEMPLATE)
