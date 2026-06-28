#!/usr/bin/env python3
"""Preflight native Apple Create readiness before running XCUITest journeys."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import importlib.util
import json
import os
from pathlib import Path
import ssl
import sys
from typing import Any
from urllib import error, parse, request
from datetime import datetime


DEFAULT_API_BASE_URL = "https://api.langtools.fifosk.synology.me"
_ROOT_DIR = Path(__file__).resolve().parents[1]
_RUNTIME_DESCRIPTOR_PATH = _ROOT_DIR / "modules" / "webapi" / "runtime_descriptor.py"
_RUNTIME_DESCRIPTOR_SPEC = importlib.util.spec_from_file_location(
    "ebook_tools_runtime_descriptor",
    _RUNTIME_DESCRIPTOR_PATH,
)
if _RUNTIME_DESCRIPTOR_SPEC is None or _RUNTIME_DESCRIPTOR_SPEC.loader is None:
    raise RuntimeError(f"Unable to load runtime descriptor from {_RUNTIME_DESCRIPTOR_PATH}")
_runtime_descriptor = importlib.util.module_from_spec(_RUNTIME_DESCRIPTOR_SPEC)
_RUNTIME_DESCRIPTOR_SPEC.loader.exec_module(_runtime_descriptor)

EXPECTED_BOOK_OPTIONS_PATH = "/api/books/options"
EXPECTED_BOOK_JOBS_PATH = "/api/books/jobs"
EXPECTED_AUDIO_VOICES_PATH = "/api/audio/voices"
EXPECTED_PIPELINE_DEFAULTS_PATH = "/api/pipelines/defaults"
EXPECTED_PIPELINE_LLM_MODELS_PATH = "/api/pipelines/llm-models"
EXPECTED_PIPELINE_SEARCH_PATH = "/api/pipelines/search"
EXPECTED_IMAGE_NODE_AVAILABILITY_PATH = "/api/pipelines/image-nodes/availability"
EXPECTED_ACQUISITION_PROVIDERS_PATH = "/api/acquisition/providers"
EXPECTED_ACQUISITION_DISCOVER_PATH = "/api/acquisition/discover"
EXPECTED_CREATE_PATHS = {
    "bookOptionsPath": EXPECTED_BOOK_OPTIONS_PATH,
    "bookJobsPath": EXPECTED_BOOK_JOBS_PATH,
    "pipelineFilesPath": "/api/pipelines/files",
    "pipelineContentIndexPath": "/api/pipelines/files/content-index",
    "pipelineUploadPath": "/api/pipelines/files/upload",
    "pipelineJobsPath": "/api/pipelines",
    "pipelineIntakeStatusPath": "/api/pipelines/intake/status",
    "pipelineDefaultsPath": EXPECTED_PIPELINE_DEFAULTS_PATH,
    "pipelineLlmModelsPath": EXPECTED_PIPELINE_LLM_MODELS_PATH,
    "pipelineSearchPath": EXPECTED_PIPELINE_SEARCH_PATH,
    "imageNodeAvailabilityPath": EXPECTED_IMAGE_NODE_AVAILABILITY_PATH,
    "audioVoicesPath": EXPECTED_AUDIO_VOICES_PATH,
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
    "acquisitionProvidersPath": EXPECTED_ACQUISITION_PROVIDERS_PATH,
    "acquisitionDiscoverPath": EXPECTED_ACQUISITION_DISCOVER_PATH,
    "acquisitionAcquirePath": "/api/acquisition/acquire",
    "acquisitionArtifactPreparePathTemplate": "/api/acquisition/artifacts/{artifact_id}/prepare",
    "acquisitionJobsPath": "/api/acquisition/jobs",
    "acquisitionJobPathTemplate": "/api/acquisition/jobs/{task_id}",
    "templateListPath": "/api/creation/templates",
    "templatePathTemplate": "/api/creation/templates/{template_id}",
}
EXPECTED_RUNTIME_SECTIONS = {
    "auth": _runtime_descriptor.AUTH_DESCRIPTOR,
    "creation": EXPECTED_CREATE_PATHS,
    "libraryActions": _runtime_descriptor.LIBRARY_ACTIONS_DESCRIPTOR,
    "pipelineJobs": _runtime_descriptor.PIPELINE_JOBS_DESCRIPTOR,
    "pipelineMedia": _runtime_descriptor.PIPELINE_MEDIA_DESCRIPTOR,
    "linguist": _runtime_descriptor.LINGUIST_DESCRIPTOR,
    "offlineExports": _runtime_descriptor.OFFLINE_EXPORTS_DESCRIPTOR,
    "playbackState": _runtime_descriptor.PLAYBACK_STATE_DESCRIPTOR,
    "notifications": _runtime_descriptor.NOTIFICATIONS_DESCRIPTOR,
}
MIN_SUPPORTED_BOOK_LANGUAGES = 50
REQUIRED_BOOK_LANGUAGE_SENTINELS = (
    "English",
    "Arabic",
    "Hindi",
    "Chinese (Traditional)",
    "Persian",
)
SUBTITLE_SOURCE_FORMATS = {"ass", "srt", "vtt"}
PREFERRED_SUBTITLE_DEFAULT_FORMATS = {"srt", "vtt"}
YOUTUBE_PLAYABLE_SUBTITLE_FORMATS = {"ass", "srt", "vtt", "sub"}
YOUTUBE_TARGET_HEIGHTS = {320, 480, 720}
EXPECTED_SENTENCE_SPLITTER_MODES = {
    "regex": {
        "cache_version": "regex-v9",
        "stable": True,
    },
    "modern": {
        "cache_version": "modern-syntok-v2+regex-v9-fallback",
        "stable": False,
    },
}
REQUIRED_SENTENCE_SPLITTER_METRICS = {
    "normalized_text_preserved",
    "contiguous_text_preserved",
    "matched_sentence_count",
    "unmatched_sentence_count",
    "unmatched_sentence_indices",
    "skipped_text_character_count",
    "trailing_text_character_count",
    "tiny_fragment_count",
    "max_words_per_segment",
}
REQUIRED_ACQUISITION_PROVIDERS = {
    "local_epub": {
        "media_kinds": {"book"},
        "capabilities": {"import_local", "metadata"},
    },
    "manual_downloads": {
        "media_kinds": {"book", "video"},
        "capabilities": {"import_local", "extract_subtitles", "metadata"},
    },
    "nas_video": {
        "media_kinds": {"video"},
        "capabilities": {"import_local", "extract_subtitles", "metadata"},
    },
    "youtube_url": {
        "media_kinds": {"video"},
        "capabilities": {"metadata", "acquire", "extract_subtitles"},
    },
    "youtube_search": {
        "media_kinds": {"video"},
        "capabilities": {"search", "metadata"},
    },
    "download_station": {
        "media_kinds": {"video"},
        "capabilities": {"acquire", "poll"},
    },
    "newznab_torznab": {
        "media_kinds": {"video"},
        "capabilities": {"search", "metadata"},
    },
    "openlibrary": {
        "media_kinds": {"book"},
        "capabilities": {"search", "metadata"},
    },
    "zlibrary_attended": {
        "media_kinds": {"book"},
        "capabilities": {"import_local"},
    },
    "gutenberg": {
        "media_kinds": {"book"},
        "capabilities": {"search", "metadata", "acquire"},
    },
    "internet_archive": {
        "media_kinds": {"book"},
        "capabilities": {"search", "metadata", "acquire"},
    },
}
EXPLICIT_ONLY_ACQUISITION_DISCOVERY_PROVIDERS = {
    "youtube_url",
}
REQUIRED_ACQUISITION_DISCOVERY_MEDIA_KINDS = {
    "youtube_url": {"video"},
}


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_settings(env_file: Path) -> tuple[str, str, str]:
    file_values = load_env_file(env_file)
    username = os.environ.get("E2E_USERNAME") or file_values.get("E2E_USERNAME", "")
    password = os.environ.get("E2E_PASSWORD") or file_values.get("E2E_PASSWORD", "")
    api_base_url = (
        os.environ.get("E2E_API_BASE_URL")
        or file_values.get("E2E_API_BASE_URL")
        or DEFAULT_API_BASE_URL
    )
    return username.strip(), password, api_base_url.strip().rstrip("/")


def json_request(
    api_base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 15.0,
) -> Any:
    url = f"{api_base_url}{path}"
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, data=body, headers=headers, method=method)
    context = ssl._create_unverified_context()
    with request.urlopen(req, timeout=timeout, context=context) as response:
        data = response.read()
    if not data:
        return None
    return json.loads(data.decode("utf-8"))


def describe_http_error(exc: error.HTTPError) -> str:
    try:
        raw_url = exc.geturl()
    except Exception:
        raw_url = getattr(exc, "filename", "") or ""
    parsed = parse.urlparse(raw_url or "")
    target = parsed.path or raw_url or "request"
    return f"API request to {target} returned HTTP {exc.code}"


def login(api_base_url: str, username: str, password: str, timeout: float) -> str:
    payload = json_request(
        api_base_url,
        "/api/auth/login",
        method="POST",
        payload={"username": username, "password": password},
        timeout=timeout,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Login response was not a JSON object")
    token = payload.get("token") or payload.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Login response did not include a token")
    return token


def count_epubs(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    ebooks = payload.get("ebooks")
    if not isinstance(ebooks, list):
        return 0
    return sum(1 for entry in ebooks if is_pipeline_epub_entry(entry))


def count_subtitle_sources(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return 0
    return sum(
        1
        for entry in sources
        if isinstance(entry, dict)
        and str(entry.get("path") or "").strip()
        and str(entry.get("format") or "").strip().lower() in {"srt", "vtt", "ass"}
    )


def count_youtube_pairs(payload: Any) -> tuple[int, int]:
    if not isinstance(payload, dict):
        return 0, 0
    videos = payload.get("videos")
    if not isinstance(videos, list):
        return 0, 0
    video_count = 0
    subtitle_count = 0
    for video in videos:
        if not isinstance(video, dict) or not str(video.get("path") or "").strip():
            continue
        subtitles = video.get("subtitles")
        if not isinstance(subtitles, list):
            continue
        playable = [
            sub for sub in subtitles
            if isinstance(sub, dict)
            and str(sub.get("path") or "").strip()
            and normalized_format(sub.get("format")) in YOUTUBE_PLAYABLE_SUBTITLE_FORMATS
        ]
        if playable:
            video_count += 1
            subtitle_count += len(playable)
    return video_count, subtitle_count


def parse_modified_timestamp(value: Any, fallback: float) -> float:
    if not isinstance(value, str) or not value.strip():
        return fallback
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return fallback


def normalized_format(value: Any) -> str:
    return str(value or "").strip().lower()


def is_pipeline_epub_entry(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    if str(entry.get("type") or "").strip().lower() == "directory":
        return False
    return bool(str(entry.get("path") or "").strip())


def preferred_epub(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    ebooks = payload.get("ebooks")
    if not isinstance(ebooks, list):
        return None
    candidates = [entry for entry in ebooks if is_pipeline_epub_entry(entry)]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda entry: (
            -parse_modified_timestamp(entry.get("modified_at"), float("-inf")),
            str(entry.get("path") or "").casefold(),
        ),
    )[0]


def content_index_chapter_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    content_index = payload.get("content_index")
    if not isinstance(content_index, dict):
        return 0
    chapters = content_index.get("chapters")
    if not isinstance(chapters, list):
        return 0
    return sum(1 for chapter in chapters if isinstance(chapter, dict))


def content_index_range_coverage_ready(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    content_index = payload.get("content_index")
    if not isinstance(content_index, dict):
        return False
    alignment = content_index.get("alignment")
    if not isinstance(alignment, dict):
        return False
    coverage = alignment.get("chapter_range_coverage")
    if not isinstance(coverage, dict):
        return False
    if coverage.get("contiguous_unique_ranges") is not True:
        return False
    return coverage.get("ordered_adjacent_ranges", True) is True


def preferred_epub_chapter_inventory(
    api_base_url: str,
    token: str,
    files: Any,
    timeout: float,
) -> dict[str, Any]:
    entry = preferred_epub(files)
    if not isinstance(entry, dict):
        return {
            "default_epub_chapter_index_ready": False,
            "default_epub_chapters": 0,
            "default_epub_chapter_ranges_ready": False,
        }
    path = str(entry.get("path") or "").strip()
    if not path:
        return {
            "default_epub_chapter_index_ready": False,
            "default_epub_chapters": 0,
            "default_epub_chapter_ranges_ready": False,
        }
    query = parse.urlencode({"input_file": path})
    try:
        payload = json_request(
            api_base_url,
            f"{EXPECTED_CREATE_PATHS['pipelineContentIndexPath']}?{query}",
            token=token,
            timeout=timeout,
        )
    except Exception:
        return {
            "default_epub_chapter_index_ready": False,
            "default_epub_chapters": 0,
            "default_epub_chapter_ranges_ready": False,
        }
    chapter_count = content_index_chapter_count(payload)
    ranges_ready = content_index_range_coverage_ready(payload)
    return {
        "default_epub_chapter_index_ready": chapter_count > 0 and ranges_ready,
        "default_epub_chapters": chapter_count,
        "default_epub_chapter_ranges_ready": ranges_ready,
    }


def subtitle_source_candidates(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return []
    return [
        entry
        for entry in sources
        if isinstance(entry, dict)
        and str(entry.get("path") or "").strip()
        and normalized_format(entry.get("format")) in SUBTITLE_SOURCE_FORMATS
    ]


def preferred_subtitle_source(payload: Any) -> dict[str, Any] | None:
    candidates = subtitle_source_candidates(payload)
    preferred = [
        entry
        for entry in candidates
        if normalized_format(entry.get("format")) in PREFERRED_SUBTITLE_DEFAULT_FORMATS
    ]
    pool = preferred or candidates
    if not pool:
        return None
    return sorted(
        pool,
        key=lambda entry: (
            -parse_modified_timestamp(entry.get("modified_at"), 0.0),
            str(entry.get("path") or "").casefold(),
        ),
    )[0]


def playable_youtube_subtitles(video: Any) -> list[dict[str, Any]]:
    if not isinstance(video, dict):
        return []
    subtitles = video.get("subtitles")
    if not isinstance(subtitles, list):
        return []
    return [
        sub
        for sub in subtitles
        if isinstance(sub, dict)
        and str(sub.get("path") or "").strip()
        and normalized_format(sub.get("format")) in YOUTUBE_PLAYABLE_SUBTITLE_FORMATS
    ]


def preferred_youtube_subtitle(video: Any) -> dict[str, Any] | None:
    candidates = playable_youtube_subtitles(video)
    if not candidates:
        return None
    return next(
        (
            sub for sub in candidates
            if str(sub.get("language") or "").strip().lower().startswith("en")
        ),
        candidates[0],
    )


def preferred_youtube_selection(payload: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(payload, dict):
        return None, None
    videos = payload.get("videos")
    if not isinstance(videos, list) or not videos:
        return None, None
    candidates = [
        candidate
        for candidate in videos
        if isinstance(candidate, dict) and str(candidate.get("path") or "").strip()
    ]
    candidates = sorted(
        candidates,
        key=lambda entry: (
            -parse_modified_timestamp(entry.get("modified_at"), float("-inf")),
            str(entry.get("path") or "").casefold(),
        ),
    )
    video = next(
        (
            candidate for candidate in candidates
            if playable_youtube_subtitles(candidate)
        ),
        candidates[0] if candidates else None,
    )
    return video, preferred_youtube_subtitle(video)


def creation_template_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "creation_templates_route_ready": False,
            "creation_templates": 0,
        }
    templates = payload.get("templates")
    if not isinstance(templates, list):
        return {
            "creation_templates_route_ready": False,
            "creation_templates": 0,
        }
    return {
        "creation_templates_route_ready": True,
        "creation_templates": sum(1 for template in templates if isinstance(template, dict)),
    }


def _string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {
        str(value).strip()
        for value in values
        if isinstance(value, str) and str(value).strip()
    }


def acquisition_provider_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "acquisition_providers_ready": False,
            "acquisition_providers": 0,
            "missing_acquisition_providers": sorted(REQUIRED_ACQUISITION_PROVIDERS),
            "invalid_acquisition_providers": ["providers"],
            "acquisition_default_providers_ready": False,
            "acquisition_default_book_providers": 0,
            "acquisition_default_video_providers": 0,
            "acquisition_default_provider_issues": ["default_provider_ids"],
            "zlibrary_policy_ready": False,
            "download_station_handoff_ready": False,
            "download_station_handoff_issues": ["providers"],
        }
    providers = payload.get("providers")
    if not isinstance(providers, list):
        return {
            "acquisition_providers_ready": False,
            "acquisition_providers": 0,
            "missing_acquisition_providers": sorted(REQUIRED_ACQUISITION_PROVIDERS),
            "invalid_acquisition_providers": ["providers"],
            "acquisition_default_providers_ready": False,
            "acquisition_default_book_providers": 0,
            "acquisition_default_video_providers": 0,
            "acquisition_default_provider_issues": ["default_provider_ids"],
            "zlibrary_policy_ready": False,
            "download_station_handoff_ready": False,
            "download_station_handoff_issues": ["providers"],
        }

    indexed = acquisition_provider_map(payload)
    missing = sorted(set(REQUIRED_ACQUISITION_PROVIDERS) - set(indexed))
    invalid: list[str] = []
    for provider_id, requirements in REQUIRED_ACQUISITION_PROVIDERS.items():
        provider = indexed.get(provider_id)
        if provider is None:
            continue
        media_kinds = _string_set(provider.get("media_kinds"))
        capabilities = _string_set(provider.get("capabilities"))
        declared_discovery_media_kinds = _string_set(provider.get("discovery_media_kinds"))
        missing_media = sorted(requirements["media_kinds"] - media_kinds)
        missing_capabilities = sorted(requirements["capabilities"] - capabilities)
        missing_discovery_media = sorted(
            REQUIRED_ACQUISITION_DISCOVERY_MEDIA_KINDS.get(provider_id, set())
            - declared_discovery_media_kinds
        )
        if missing_media:
            invalid.append(f"{provider_id}.media_kinds:{','.join(missing_media)}")
        if missing_capabilities:
            invalid.append(f"{provider_id}.capabilities:{','.join(missing_capabilities)}")
        if missing_discovery_media:
            invalid.append(f"{provider_id}.discovery_media_kinds:{','.join(missing_discovery_media)}")

    zlibrary = indexed.get("zlibrary_attended")
    zlibrary_policy_ready = False
    if isinstance(zlibrary, dict):
        policy_text = " ".join(_string_set(zlibrary.get("policy_notes"))).lower()
        zlibrary_policy_ready = (
            zlibrary.get("available") is False
            and "disabled" in policy_text
            and "attended" in policy_text
        )
    if not zlibrary_policy_ready:
        invalid.append("zlibrary_attended.policy")

    handoff_issues = download_station_handoff_issues(indexed)
    default_provider_issues = acquisition_default_provider_issues(payload, indexed)
    default_provider_ids = payload.get("default_provider_ids")
    default_book_providers = normalized_default_provider_ids(default_provider_ids, "book")
    default_video_providers = normalized_default_provider_ids(default_provider_ids, "video")
    return {
        "acquisition_providers_ready": not missing and not invalid and not default_provider_issues,
        "acquisition_providers": len(indexed),
        "missing_acquisition_providers": missing,
        "invalid_acquisition_providers": sorted(invalid),
        "acquisition_default_providers_ready": not default_provider_issues,
        "acquisition_default_book_providers": len(default_book_providers),
        "acquisition_default_video_providers": len(default_video_providers),
        "acquisition_default_provider_issues": default_provider_issues,
        "zlibrary_policy_ready": zlibrary_policy_ready,
        "download_station_handoff_ready": not handoff_issues,
        "download_station_handoff_issues": handoff_issues,
    }


def normalized_default_provider_ids(default_provider_ids: Any, media_kind: str) -> list[str]:
    if not isinstance(default_provider_ids, dict):
        return []
    values = default_provider_ids.get(media_kind)
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        provider_id = value.strip()
        if not provider_id or provider_id in seen:
            continue
        seen.add(provider_id)
        normalized.append(provider_id)
    return normalized


def acquisition_default_provider_issues(
    payload: dict[str, Any],
    providers: dict[str, dict[str, Any]],
) -> list[str]:
    default_provider_ids = payload.get("default_provider_ids")
    if not isinstance(default_provider_ids, dict):
        return ["default_provider_ids"]

    issues: list[str] = []
    for media_kind in ("book", "video"):
        provider_ids = normalized_default_provider_ids(default_provider_ids, media_kind)
        if not provider_ids:
            issues.append(f"{media_kind}.missing")
            continue
        media_kind_issue_count = len(issues)
        compatible_providers: list[dict[str, Any]] = []
        for provider_id in provider_ids:
            provider = providers.get(provider_id)
            if provider is None:
                issues.append(f"{media_kind}.{provider_id}.missing")
                continue
            if provider_id in EXPLICIT_ONLY_ACQUISITION_DISCOVERY_PROVIDERS:
                issues.append(f"{media_kind}.{provider_id}.explicit_only")
                continue
            if media_kind not in acquisition_provider_discovery_media_kinds(provider):
                issues.append(f"{media_kind}.{provider_id}.media_kind")
                continue
            default_eligible_media_kinds = acquisition_provider_default_eligible_media_kinds(provider)
            if (
                default_eligible_media_kinds is not None
                and media_kind not in default_eligible_media_kinds
            ):
                issues.append(f"{media_kind}.{provider_id}.default_eligible")
                continue
            compatible_providers.append(provider)
        if (
            len(issues) == media_kind_issue_count
            and compatible_providers
            and not any(provider.get("available") is True for provider in compatible_providers)
        ):
            issues.append(f"{media_kind}.unavailable")
    return sorted(issues)


def acquisition_provider_discovery_media_kinds(provider: dict[str, Any]) -> set[str]:
    discovery_media_kinds = provider.get("discovery_media_kinds")
    if isinstance(discovery_media_kinds, list):
        return _string_set(discovery_media_kinds)
    return _string_set(provider.get("media_kinds"))


def acquisition_provider_default_eligible_media_kinds(provider: dict[str, Any]) -> set[str] | None:
    default_eligible_media_kinds = provider.get("default_eligible_media_kinds")
    if isinstance(default_eligible_media_kinds, list):
        return _string_set(default_eligible_media_kinds)
    return None


def acquisition_discovery_payload_issues(
    payload: Any,
    *,
    expected_provider: str,
) -> list[str]:
    if not isinstance(payload, dict):
        return ["payload"]

    issues: list[str] = []
    candidates = payload.get("candidates")
    policy_notes = payload.get("policy_notes")
    providers_queried = payload.get("providers_queried")
    if not isinstance(candidates, list):
        issues.append("candidates")
    else:
        required_candidate_fields = {
            "candidate_id": str,
            "provider": str,
            "media_kind": str,
            "title": str,
            "rights": str,
            "capabilities": list,
            "candidate_token": str,
            "contributors": list,
            "subtitles": list,
            "requires_confirmation": bool,
            "policy_notes": list,
        }
        for index, candidate in enumerate(candidates[:3]):
            if not isinstance(candidate, dict):
                issues.append(f"candidate_{index}")
                continue
            for field, expected_type in required_candidate_fields.items():
                if not isinstance(candidate.get(field), expected_type):
                    issues.append(f"candidate_{index}.{field}")
    if not isinstance(policy_notes, list) or not all(isinstance(note, str) for note in policy_notes):
        issues.append("policy_notes")
    if not isinstance(providers_queried, list) or not all(isinstance(provider, str) for provider in providers_queried):
        issues.append("providers_queried")
    elif expected_provider not in providers_queried:
        issues.append(f"providers_queried:{expected_provider}")
    return sorted(issues)


def acquisition_discovery_inventory(
    api_base_url: str,
    token: str,
    providers_payload: Any,
    timeout: float,
    captured_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    default_provider_ids = (
        providers_payload.get("default_provider_ids")
        if isinstance(providers_payload, dict)
        else None
    )
    issues: list[str] = []
    candidate_counts: dict[str, int] = {"book": 0, "video": 0}
    provider_counts: dict[str, int] = {"book": 0, "video": 0}

    for media_kind in ("book", "video"):
        provider_ids = normalized_default_provider_ids(default_provider_ids, media_kind)
        provider = preferred_acquisition_discovery_provider_id(
            providers_payload,
            media_kind,
            provider_ids,
        )
        if not provider:
            issues.append(f"{media_kind}.default_provider")
            continue
        query = parse.urlencode(
            [
                ("media_kind", media_kind),
                ("provider", provider),
                ("limit", "1"),
            ]
        )
        try:
            payload = json_request(
                api_base_url,
                f"{EXPECTED_ACQUISITION_DISCOVER_PATH}?{query}",
                token=token,
                timeout=timeout,
            )
        except Exception:
            issues.append(f"{media_kind}.request")
            continue
        payload_issues = acquisition_discovery_payload_issues(
            payload,
            expected_provider=provider,
        )
        issues.extend(f"{media_kind}.{issue}" for issue in payload_issues)
        if isinstance(payload, dict):
            candidates = payload.get("candidates")
            providers_queried = payload.get("providers_queried")
            candidate_counts[media_kind] = len(candidates) if isinstance(candidates, list) else 0
            provider_counts[media_kind] = len(providers_queried) if isinstance(providers_queried, list) else 0
            if captured_payloads is not None:
                captured_payloads[media_kind] = {
                    "provider": provider,
                    "payload": payload,
                }

    return {
        "acquisition_discovery_route_ready": not issues,
        "acquisition_book_discovery_candidates": candidate_counts["book"],
        "acquisition_video_discovery_candidates": candidate_counts["video"],
        "acquisition_book_discovery_providers": provider_counts["book"],
        "acquisition_video_discovery_providers": provider_counts["video"],
        "acquisition_discovery_issues": sorted(issues),
    }


def acquisition_default_discovery_payload_issues(
    payload: Any,
    *,
    media_kind: str,
    expected_provider_ids: list[str],
) -> list[str]:
    issues = acquisition_discovery_payload_issues(payload, expected_provider="")
    issues = [issue for issue in issues if not issue.startswith("providers_queried:")]
    if not isinstance(payload, dict):
        return issues

    providers_queried = payload.get("providers_queried")
    if not isinstance(providers_queried, list):
        return sorted(issues)
    queried = [
        provider.strip()
        for provider in providers_queried
        if isinstance(provider, str) and provider.strip()
    ]
    expected = set(expected_provider_ids)
    if not queried:
        issues.append("providers_queried.empty")
    if expected:
        unexpected = sorted(provider for provider in queried if provider not in expected)
        if unexpected:
            issues.append("providers_queried.unexpected:" + ",".join(unexpected))
        if not any(provider in expected for provider in queried):
            issues.append("providers_queried.default")

    candidates = payload.get("candidates")
    if isinstance(candidates, list):
        for index, candidate in enumerate(candidates[:3]):
            if not isinstance(candidate, dict):
                continue
            if candidate.get("media_kind") != media_kind:
                issues.append(f"candidate_{index}.media_kind:{media_kind}")
            provider = candidate.get("provider")
            if expected and isinstance(provider, str) and provider not in expected:
                issues.append(f"candidate_{index}.provider:{provider}")
    return sorted(set(issues))


def acquisition_default_discovery_inventory(
    api_base_url: str,
    token: str,
    providers_payload: Any,
    timeout: float,
) -> dict[str, Any]:
    default_provider_ids = (
        providers_payload.get("default_provider_ids")
        if isinstance(providers_payload, dict)
        else None
    )
    issues: list[str] = []
    candidate_counts: dict[str, int] = {"book": 0, "video": 0}
    provider_counts: dict[str, int] = {"book": 0, "video": 0}

    for media_kind in ("book", "video"):
        provider_ids = [
            provider_id
            for provider_id in normalized_default_provider_ids(default_provider_ids, media_kind)
            if provider_id not in EXPLICIT_ONLY_ACQUISITION_DISCOVERY_PROVIDERS
        ]
        if not provider_ids:
            issues.append(f"{media_kind}.default_provider")
            continue
        query = parse.urlencode(
            [
                ("media_kind", media_kind),
                ("limit", "1"),
            ]
        )
        try:
            payload = json_request(
                api_base_url,
                f"{EXPECTED_ACQUISITION_DISCOVER_PATH}?{query}",
                token=token,
                timeout=timeout,
            )
        except Exception:
            issues.append(f"{media_kind}.request")
            continue

        payload_issues = acquisition_default_discovery_payload_issues(
            payload,
            media_kind=media_kind,
            expected_provider_ids=provider_ids,
        )
        issues.extend(f"{media_kind}.{issue}" for issue in payload_issues)
        if isinstance(payload, dict):
            candidates = payload.get("candidates")
            providers_queried = payload.get("providers_queried")
            candidate_counts[media_kind] = len(candidates) if isinstance(candidates, list) else 0
            provider_counts[media_kind] = len(providers_queried) if isinstance(providers_queried, list) else 0

    return {
        "acquisition_default_discovery_route_ready": not issues,
        "acquisition_default_book_discovery_candidates": candidate_counts["book"],
        "acquisition_default_video_discovery_candidates": candidate_counts["video"],
        "acquisition_default_book_discovery_providers": provider_counts["book"],
        "acquisition_default_video_discovery_providers": provider_counts["video"],
        "acquisition_default_discovery_issues": sorted(issues),
    }


def acquisition_prepared_artifact_payload_issues(
    payload: Any,
    *,
    expected_provider: str,
) -> list[str]:
    if not isinstance(payload, dict):
        return ["payload"]

    issues: list[str] = []
    required_fields = {
        "provider": str,
        "media_kind": str,
        "source_kind": str,
        "local_path": str,
        "input_file": str,
        "next_actions": list,
        "metadata": dict,
    }
    for field, expected_type in required_fields.items():
        if not isinstance(payload.get(field), expected_type):
            issues.append(field)
    for field in ("local_path", "input_file", "source_kind"):
        if str(payload.get(field) or "").strip() == "":
            issues.append(f"{field}.empty")
    if payload.get("provider") != expected_provider:
        issues.append(f"provider:{expected_provider}")
    if payload.get("media_kind") != "book":
        issues.append("media_kind:book")
    if (
        isinstance(payload.get("local_path"), str)
        and isinstance(payload.get("input_file"), str)
        and payload.get("local_path") != payload.get("input_file")
    ):
        issues.append("input_file.local_path")
    next_actions = payload.get("next_actions")
    if isinstance(next_actions, list):
        if not all(isinstance(action, str) for action in next_actions):
            issues.append("next_actions.items")
        elif "create_book_job" not in next_actions:
            issues.append("next_actions:create_book_job")
    issues.extend(
        f"metadata.{issue}"
        for issue in acquisition_prepared_artifact_metadata_issues(
            payload.get("metadata"),
            expected_provider=expected_provider,
        )
    )
    return sorted(issues)


def acquisition_prepared_artifact_metadata_issues(
    metadata: Any,
    *,
    expected_provider: str,
) -> list[str]:
    if not isinstance(metadata, dict):
        return ["payload"]

    issues: list[str] = []
    for field in ("source_kind", "source_provider", "acquisition_provider", "acquisition_candidate_id"):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{field}.empty")
    for field in ("source_provider", "acquisition_provider"):
        value = metadata.get(field)
        if isinstance(value, str) and value.strip() and value != expected_provider:
            issues.append(f"{field}:{expected_provider}")
    for field in ("candidate_token", "artifact_token", "token"):
        if field in metadata:
            issues.append(f"{field}.forbidden")
    return sorted(issues)


def acquisition_prepared_video_artifact_payload_issues(
    payload: Any,
    *,
    expected_provider: str,
) -> list[str]:
    if not isinstance(payload, dict):
        return ["payload"]

    issues: list[str] = []
    required_fields = {
        "provider": str,
        "media_kind": str,
        "source_kind": str,
        "local_path": str,
        "video_path": str,
        "subtitles": list,
        "next_actions": list,
        "metadata": dict,
    }
    for field, expected_type in required_fields.items():
        if not isinstance(payload.get(field), expected_type):
            issues.append(field)
    for field in ("local_path", "video_path", "source_kind"):
        if str(payload.get(field) or "").strip() == "":
            issues.append(f"{field}.empty")
    if payload.get("provider") != expected_provider:
        issues.append(f"provider:{expected_provider}")
    if payload.get("media_kind") != "video":
        issues.append("media_kind:video")
    if (
        isinstance(payload.get("local_path"), str)
        and isinstance(payload.get("video_path"), str)
        and payload.get("local_path") != payload.get("video_path")
    ):
        issues.append("video_path.local_path")
    subtitle_path = payload.get("subtitle_path")
    if subtitle_path is not None and not isinstance(subtitle_path, str):
        issues.append("subtitle_path")
    subtitles = payload.get("subtitles")
    if isinstance(subtitles, list) and not all(isinstance(subtitle, dict) for subtitle in subtitles):
        issues.append("subtitles.items")
    next_actions = payload.get("next_actions")
    if isinstance(next_actions, list):
        if not all(isinstance(action, str) for action in next_actions):
            issues.append("next_actions.items")
        elif "create_dub_job" not in next_actions:
            issues.append("next_actions:create_dub_job")
    issues.extend(
        f"metadata.{issue}"
        for issue in acquisition_prepared_artifact_metadata_issues(
            payload.get("metadata"),
            expected_provider=expected_provider,
        )
    )
    return sorted(issues)


def first_candidate_token(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ""
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        token_value = candidate.get("candidate_token")
        if isinstance(token_value, str) and token_value.strip():
            return token_value.strip()
    return ""


def discovery_payload_for_media_kind(
    api_base_url: str,
    token: str,
    timeout: float,
    *,
    media_kind: str,
    provider: str,
    discovery_payloads: dict[str, dict[str, Any]] | None = None,
) -> Any:
    captured = (discovery_payloads or {}).get(media_kind)
    discovery_payload = (
        captured.get("payload")
        if isinstance(captured, dict) and captured.get("provider") == provider
        else None
    )
    if isinstance(discovery_payload, dict):
        return discovery_payload
    query = parse.urlencode(
        [
            ("media_kind", media_kind),
            ("provider", provider),
            ("limit", "1"),
        ]
    )
    return json_request(
        api_base_url,
        f"{EXPECTED_ACQUISITION_DISCOVER_PATH}?{query}",
        token=token,
        timeout=timeout,
    )


def prepared_artifact_payload(
    api_base_url: str,
    token: str,
    timeout: float,
    *,
    candidate_token: str,
) -> Any:
    artifact_path = EXPECTED_CREATE_PATHS["acquisitionArtifactPreparePathTemplate"].replace(
        "{artifact_id}",
        parse.quote(candidate_token, safe=""),
    )
    return json_request(
        api_base_url,
        artifact_path,
        method="POST",
        token=token,
        timeout=timeout,
    )


def acquisition_prepared_artifact_inventory(
    api_base_url: str,
    token: str,
    providers_payload: Any,
    timeout: float,
    discovery_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    default_provider_ids = (
        providers_payload.get("default_provider_ids")
        if isinstance(providers_payload, dict)
        else None
    )
    provider = preferred_acquisition_discovery_provider_id(
        providers_payload,
        "book",
        normalized_default_provider_ids(default_provider_ids, "book"),
    )
    if not provider:
        return {
            "acquisition_artifact_prepare_route_ready": False,
            "acquisition_artifact_prepare_issues": ["book.default_provider"],
        }

    try:
        discovery_payload = discovery_payload_for_media_kind(
            api_base_url,
            token,
            timeout,
            media_kind="book",
            provider=provider,
            discovery_payloads=discovery_payloads,
        )
    except Exception:
        return {
            "acquisition_artifact_prepare_route_ready": False,
            "acquisition_artifact_prepare_issues": ["discovery.request"],
        }

    candidate_token = first_candidate_token(discovery_payload)
    if not candidate_token:
        return {
            "acquisition_artifact_prepare_route_ready": False,
            "acquisition_artifact_prepare_issues": ["book.candidate_token"],
        }

    try:
        prepared_payload = prepared_artifact_payload(
            api_base_url,
            token=token,
            timeout=timeout,
            candidate_token=candidate_token,
        )
    except Exception:
        return {
            "acquisition_artifact_prepare_route_ready": False,
            "acquisition_artifact_prepare_issues": ["prepare.request"],
        }

    issues = acquisition_prepared_artifact_payload_issues(
        prepared_payload,
        expected_provider=provider,
    )
    video_provider = preferred_acquisition_discovery_provider_id(
        providers_payload,
        "video",
        normalized_default_provider_ids(default_provider_ids, "video"),
    )
    if video_provider:
        try:
            video_discovery_payload = discovery_payload_for_media_kind(
                api_base_url,
                token,
                timeout,
                media_kind="video",
                provider=video_provider,
                discovery_payloads=discovery_payloads,
            )
        except Exception:
            issues.append("video.discovery.request")
        else:
            video_candidate_token = first_candidate_token(video_discovery_payload)
            if video_candidate_token:
                try:
                    prepared_video_payload = prepared_artifact_payload(
                        api_base_url,
                        token=token,
                        timeout=timeout,
                        candidate_token=video_candidate_token,
                    )
                except Exception:
                    issues.append("video.prepare.request")
                else:
                    issues.extend(
                        f"video.{issue}"
                        for issue in acquisition_prepared_video_artifact_payload_issues(
                            prepared_video_payload,
                            expected_provider=video_provider,
                        )
                    )
    return {
        "acquisition_artifact_prepare_route_ready": not issues,
        "acquisition_artifact_prepare_issues": sorted(issues),
    }


def acquisition_job_status_payload_issues(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["payload"]

    issues: list[str] = []
    required_fields = {
        "provider": str,
        "task_id": str,
        "status": str,
        "updated_at": str,
        "completed_files": list,
        "next_actions": list,
        "metadata": dict,
    }
    for field, expected_type in required_fields.items():
        if not isinstance(payload.get(field), expected_type):
            issues.append(field)
    for field in ("completed_files", "next_actions"):
        values = payload.get(field)
        if isinstance(values, list) and not all(isinstance(value, str) for value in values):
            issues.append(f"{field}.items")
    progress = payload.get("progress")
    if progress is not None and (isinstance(progress, bool) or not isinstance(progress, (int, float))):
        issues.append("progress")
    for field in ("message", "external_task_id", "raw_status", "started_at"):
        value = payload.get(field)
        if value is not None and not isinstance(value, str):
            issues.append(field)
    if payload.get("provider") != "download_station":
        issues.append("provider:download_station")
    if str(payload.get("task_id") or "").strip() == "":
        issues.append("task_id.empty")
    if str(payload.get("status") or "").strip() == "":
        issues.append("status.empty")
    return sorted(issues)


def acquisition_job_status_inventory(
    api_base_url: str,
    token: str,
    timeout: float,
) -> dict[str, Any]:
    task_id = parse.quote("download_station:submitted", safe="")
    path = EXPECTED_CREATE_PATHS["acquisitionJobPathTemplate"].replace("{task_id}", task_id)
    query = parse.urlencode({"provider": "download_station"})
    try:
        payload = json_request(
            api_base_url,
            f"{path}?{query}",
            token=token,
            timeout=timeout,
        )
    except Exception:
        return {
            "acquisition_job_status_route_ready": False,
            "acquisition_job_status_issues": ["request"],
        }
    issues = acquisition_job_status_payload_issues(payload)
    return {
        "acquisition_job_status_route_ready": not issues,
        "acquisition_job_status_issues": issues,
    }


def preferred_acquisition_discovery_provider_id(
    providers_payload: Any,
    media_kind: str,
    provider_ids: list[str],
) -> str:
    """Return the default provider readiness should probe for a media kind."""

    if not provider_ids:
        return ""
    providers = acquisition_provider_map(providers_payload)
    if not providers:
        return provider_ids[0]
    for provider_id in provider_ids:
        provider = providers.get(provider_id)
        if (
            provider is not None
            and provider.get("available") is True
            and media_kind in acquisition_provider_discovery_media_kinds(provider)
        ):
            return provider_id
    return provider_ids[0]


def acquisition_provider_map(providers_payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(providers_payload, dict):
        return {}
    providers = providers_payload.get("providers")
    if not isinstance(providers, list):
        return {}
    return {
        str(provider.get("id") or "").strip(): provider
        for provider in providers
        if isinstance(provider, dict) and str(provider.get("id") or "").strip()
    }


def download_station_handoff_issues(providers: dict[str, dict[str, Any]]) -> list[str]:
    checks = {
        "newznab_torznab": {"search", "metadata"},
        "download_station": {"acquire", "poll"},
    }
    issues: list[str] = []
    for provider_id, required_capabilities in checks.items():
        provider = providers.get(provider_id)
        if provider is None:
            issues.append(f"{provider_id}.missing")
            continue
        if provider.get("available") is False:
            issues.append(f"{provider_id}.available")
        capabilities = _string_set(provider.get("capabilities"))
        for capability in sorted(required_capabilities - capabilities):
            issues.append(f"{provider_id}.capabilities:{capability}")
    return issues


def pipeline_defaults_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "pipeline_defaults_route_ready": False,
            "pipeline_defaults_config_keys": 0,
        }
    config = payload.get("config")
    return {
        "pipeline_defaults_route_ready": isinstance(config, dict),
        "pipeline_defaults_config_keys": len(config) if isinstance(config, dict) else 0,
    }


def model_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "subtitle_models_ready": False,
            "subtitle_models": 0,
        }
    models = payload.get("models")
    if not isinstance(models, list):
        return {
            "subtitle_models_ready": False,
            "subtitle_models": 0,
        }
    return {
        "subtitle_models_ready": all(isinstance(model, str) for model in models),
        "subtitle_models": sum(1 for model in models if isinstance(model, str) and model.strip()),
    }


def pipeline_llm_model_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "pipeline_llm_models_ready": False,
            "pipeline_llm_models": 0,
        }
    models = payload.get("models")
    if not isinstance(models, list):
        return {
            "pipeline_llm_models_ready": False,
            "pipeline_llm_models": 0,
        }
    return {
        "pipeline_llm_models_ready": all(isinstance(model, str) for model in models),
        "pipeline_llm_models": sum(1 for model in models if isinstance(model, str) and model.strip()),
    }


def image_node_availability_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "image_node_availability_ready": False,
            "image_nodes_checked": 0,
            "image_nodes_available": 0,
            "image_nodes_unavailable": 0,
        }
    nodes = payload.get("nodes")
    available = payload.get("available")
    unavailable = payload.get("unavailable")
    nodes_ready = isinstance(nodes, list) and all(
        isinstance(node, dict)
        and isinstance(node.get("base_url"), str)
        and isinstance(node.get("available"), bool)
        for node in nodes
    )
    available_ready = isinstance(available, list) and all(isinstance(url, str) for url in available)
    unavailable_ready = isinstance(unavailable, list) and all(isinstance(url, str) for url in unavailable)
    return {
        "image_node_availability_ready": nodes_ready and available_ready and unavailable_ready,
        "image_nodes_checked": len(nodes) if isinstance(nodes, list) else 0,
        "image_nodes_available": len(available) if isinstance(available, list) else 0,
        "image_nodes_unavailable": len(unavailable) if isinstance(unavailable, list) else 0,
    }


def voice_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "voice_inventory_ready": False,
            "macos_voices": 0,
            "gtts_voices": 0,
            "piper_voices": 0,
        }
    macos = payload.get("macos")
    gtts = payload.get("gtts")
    piper = payload.get("piper")
    macos_ready = isinstance(macos, list) and all(
        isinstance(voice, dict)
        and isinstance(voice.get("name"), str)
        and isinstance(voice.get("lang"), str)
        for voice in macos
    )
    gtts_ready = isinstance(gtts, list) and all(
        isinstance(voice, dict)
        and isinstance(voice.get("code"), str)
        and isinstance(voice.get("name"), str)
        for voice in gtts
    )
    piper_ready = isinstance(piper, list) and all(
        isinstance(voice, dict)
        and isinstance(voice.get("name"), str)
        and isinstance(voice.get("lang"), str)
        and isinstance(voice.get("quality"), str)
        for voice in piper
    )
    return {
        "voice_inventory_ready": macos_ready and gtts_ready and piper_ready,
        "macos_voices": len(macos) if isinstance(macos, list) else 0,
        "gtts_voices": len(gtts) if isinstance(gtts, list) else 0,
        "piper_voices": len(piper) if isinstance(piper, list) else 0,
    }


def _non_negative_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _optional_non_negative_int(value: Any) -> bool:
    return value is None or _non_negative_int(value)


def pipeline_intake_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "pipeline_intake_ready": False,
            "pipeline_intake_accepting_jobs": False,
            "pipeline_intake_queue_depth": 0,
            "pipeline_intake_active_count": 0,
        }
    accepting_jobs = payload.get("acceptingJobs")
    is_under_pressure = payload.get("isUnderPressure")
    queue_depth = payload.get("queueDepth")
    active_count = payload.get("activeCount")
    delay_count = payload.get("delayCount")
    ready = (
        isinstance(accepting_jobs, bool)
        and isinstance(is_under_pressure, bool)
        and _non_negative_int(queue_depth)
        and _non_negative_int(active_count)
        and _non_negative_int(delay_count)
        and _optional_non_negative_int(payload.get("softLimit"))
        and _optional_non_negative_int(payload.get("hardLimit"))
    )
    return {
        "pipeline_intake_ready": ready,
        "pipeline_intake_accepting_jobs": accepting_jobs if isinstance(accepting_jobs, bool) else False,
        "pipeline_intake_queue_depth": queue_depth if _non_negative_int(queue_depth) else 0,
        "pipeline_intake_active_count": active_count if _non_negative_int(active_count) else 0,
    }


def normalized_language_names(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    names: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = " ".join(value.strip().split())
        if cleaned:
            names.add(cleaned.lower())
    return names


def language_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        input_languages: Any = []
        output_languages: Any = []
    else:
        input_languages = payload.get("supported_input_languages")
        output_languages = payload.get("supported_output_languages")

    input_names = normalized_language_names(input_languages)
    output_names = normalized_language_names(output_languages)
    required = {language.lower() for language in REQUIRED_BOOK_LANGUAGE_SENTINELS}
    return {
        "book_input_languages": len(input_names),
        "book_output_languages": len(output_names),
        "missing_book_input_languages": sorted(required - input_names),
        "missing_book_output_languages": sorted(required - output_names),
    }


def _number_in_range(
    payload: dict[str, Any],
    key: str,
    *,
    minimum: float,
    maximum: float | None = None,
) -> bool:
    value = payload.get(key)
    if isinstance(value, bool):
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    if numeric < minimum:
        return False
    if maximum is not None and numeric > maximum:
        return False
    return True


def validate_subtitle_defaults(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["subtitle_defaults missing"]
    errors: list[str] = []
    checks = {
        "worker_count": (1, 32),
        "batch_size": (1, 500),
        "translation_batch_size": (1, 50),
        "ass_font_size": (12, 120),
        "ass_emphasis_scale": (1.0, 2.5),
    }
    for key, (minimum, maximum) in checks.items():
        if not _number_in_range(payload, key, minimum=minimum, maximum=maximum):
            errors.append(key)
    return errors


def validate_youtube_dub_defaults(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["youtube_dub_defaults missing"]
    errors: list[str] = []
    numeric_checks = {
        "original_mix_percent": (0, 100),
        "flush_sentences": (1, 200),
        "translation_batch_size": (1, 50),
    }
    for key, (minimum, maximum) in numeric_checks.items():
        if not _number_in_range(payload, key, minimum=minimum, maximum=maximum):
            errors.append(key)
    for key in ("split_batches", "stitch_batches", "preserve_aspect_ratio"):
        if not isinstance(payload.get(key), bool):
            errors.append(key)
    target_height = payload.get("target_height")
    if isinstance(target_height, bool) or target_height not in YOUTUBE_TARGET_HEIGHTS:
        errors.append("target_height")
    return errors


def validate_generated_book_defaults(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["book options missing"]
    errors: list[str] = []

    sentence_bounds = payload.get("sentence_bounds")
    if not isinstance(sentence_bounds, dict):
        errors.append("sentence_bounds")
    else:
        for key in ("min", "max", "default"):
            if not _number_in_range(sentence_bounds, key, minimum=1):
                errors.append(f"sentence_bounds.{key}")
        try:
            minimum = int(sentence_bounds.get("min"))
            maximum = int(sentence_bounds.get("max"))
            default = int(sentence_bounds.get("default"))
        except (TypeError, ValueError):
            pass
        else:
            if not minimum <= default <= maximum:
                errors.append("sentence_bounds.default_range")

    defaults = payload.get("defaults")
    if not isinstance(defaults, dict):
        errors.append("defaults")
    else:
        for key in ("author", "input_language", "output_language", "voice"):
            if not str(defaults.get(key) or "").strip():
                errors.append(f"defaults.{key}")

    pipeline_defaults = payload.get("pipeline_defaults")
    if not isinstance(pipeline_defaults, dict):
        errors.append("pipeline_defaults")
    else:
        for key in ("audio_mode", "written_mode", "selected_voice"):
            if not str(pipeline_defaults.get(key) or "").strip():
                errors.append(f"pipeline_defaults.{key}")
        if not isinstance(pipeline_defaults.get("stitch_full"), bool):
            errors.append("pipeline_defaults.stitch_full")

    return errors


def validate_sentence_splitter_capabilities(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["sentence_splitter_capabilities missing"]
    capabilities = payload.get("sentence_splitter_capabilities")
    if not isinstance(capabilities, dict):
        return ["sentence_splitter_capabilities"]

    errors: list[str] = []
    if capabilities.get("default_mode") != "regex":
        errors.append("sentence_splitter_capabilities.default_mode")

    raw_modes = capabilities.get("supported_modes")
    if not isinstance(raw_modes, list):
        errors.append("sentence_splitter_capabilities.supported_modes")
        modes_by_id: dict[str, dict[str, Any]] = {}
    else:
        modes_by_id = {
            str(mode.get("id")): mode
            for mode in raw_modes
            if isinstance(mode, dict) and str(mode.get("id") or "").strip()
        }
        for mode_id, expected in EXPECTED_SENTENCE_SPLITTER_MODES.items():
            mode = modes_by_id.get(mode_id)
            if not isinstance(mode, dict):
                errors.append(f"sentence_splitter_capabilities.supported_modes.{mode_id}")
                continue
            if str(mode.get("label") or "").strip() == "":
                errors.append(f"sentence_splitter_capabilities.supported_modes.{mode_id}.label")
            if mode.get("cache_version") != expected["cache_version"]:
                errors.append(f"sentence_splitter_capabilities.supported_modes.{mode_id}.cache_version")
            if mode.get("stable") != expected["stable"]:
                errors.append(f"sentence_splitter_capabilities.supported_modes.{mode_id}.stable")

    raw_metrics = capabilities.get("comparison_metric_fields")
    metrics = (
        {value for value in raw_metrics if isinstance(value, str)}
        if isinstance(raw_metrics, list)
        else set()
    )
    missing_metrics = sorted(REQUIRED_SENTENCE_SPLITTER_METRICS - metrics)
    if missing_metrics:
        errors.extend(
            f"sentence_splitter_capabilities.comparison_metric_fields.{metric}"
            for metric in missing_metrics
        )
    return errors


def media_job_defaults_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        generated_errors = ["book options missing"]
        splitter_errors = ["sentence_splitter_capabilities missing"]
        subtitle_errors = ["subtitle_defaults missing"]
        youtube_errors = ["youtube_dub_defaults missing"]
    else:
        generated_errors = validate_generated_book_defaults(payload)
        splitter_errors = validate_sentence_splitter_capabilities(payload)
        subtitle_errors = validate_subtitle_defaults(payload.get("subtitle_defaults"))
        youtube_errors = validate_youtube_dub_defaults(payload.get("youtube_dub_defaults"))
    return {
        "generated_book_defaults_ready": not generated_errors,
        "sentence_splitter_capabilities_ready": not splitter_errors,
        "subtitle_job_defaults_ready": not subtitle_errors,
        "youtube_dub_defaults_ready": not youtube_errors,
        "generated_book_defaults_errors": generated_errors,
        "sentence_splitter_capabilities_errors": splitter_errors,
        "subtitle_job_defaults_errors": subtitle_errors,
        "youtube_dub_defaults_errors": youtube_errors,
    }


def validate_runtime_create_contract(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["runtime descriptor was not a JSON object"]

    errors: list[str] = []
    for section_name, expected_paths in EXPECTED_RUNTIME_SECTIONS.items():
        section = payload.get(section_name)
        if not isinstance(section, dict):
            errors.append(f"runtime descriptor is missing {section_name} metadata")
            continue
        errors.extend(
            _runtime_section_errors(
                section,
                expected_paths,
                prefix="" if section_name == "creation" else f"{section_name}.",
            )
        )
    return errors


def _runtime_section_errors(
    section: Mapping[str, Any],
    expected_paths: Mapping[str, Any],
    *,
    prefix: str,
) -> list[str]:
    return [
        f"{prefix}{key}={_runtime_contract_label(actual)} expected {_runtime_contract_label(expected)}"
        for key, expected in expected_paths.items()
        for actual in [_normalized_runtime_contract_value(section.get(key))]
        if actual != _normalized_runtime_contract_value(expected)
    ]


def _normalized_runtime_contract_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return value.strip()
    return value


def _runtime_contract_label(value: Any) -> str:
    normalized = _normalized_runtime_contract_value(value)
    if normalized is None or normalized == "":
        return "<missing>"
    if isinstance(normalized, list):
        return str(normalized)
    return str(normalized)


def require_runtime_create_contract(api_base_url: str, timeout: float) -> None:
    runtime = json_request(api_base_url, "/api/system/runtime", timeout=timeout)
    errors = validate_runtime_create_contract(runtime)
    if errors:
        raise RuntimeError(
            "Backend runtime Apple contract is not ready: " + "; ".join(errors)
        )


def fetch_readiness(api_base_url: str, token: str, timeout: float) -> dict[str, Any]:
    require_runtime_create_contract(api_base_url, timeout)
    files = json_request(api_base_url, "/api/pipelines/files", token=token, timeout=timeout)
    subtitles = json_request(api_base_url, "/api/subtitles/sources", token=token, timeout=timeout)
    youtube = json_request(
        api_base_url,
        "/api/subtitles/youtube/library",
        token=token,
        timeout=timeout,
    )
    book_options = json_request(api_base_url, EXPECTED_BOOK_OPTIONS_PATH, token=token, timeout=timeout)
    pipeline_defaults = json_request(
        api_base_url,
        EXPECTED_PIPELINE_DEFAULTS_PATH,
        token=token,
        timeout=timeout,
    )
    creation_templates = json_request(
        api_base_url,
        EXPECTED_CREATE_PATHS["templateListPath"],
        token=token,
        timeout=timeout,
    )
    acquisition_providers = json_request(
        api_base_url,
        EXPECTED_ACQUISITION_PROVIDERS_PATH,
        token=token,
        timeout=timeout,
    )
    intake_status = json_request(
        api_base_url,
        EXPECTED_CREATE_PATHS["pipelineIntakeStatusPath"],
        token=token,
        timeout=timeout,
    )
    subtitle_models = json_request(
        api_base_url,
        EXPECTED_CREATE_PATHS["subtitleModelsPath"],
        token=token,
        timeout=timeout,
    )
    pipeline_llm_models = json_request(
        api_base_url,
        EXPECTED_PIPELINE_LLM_MODELS_PATH,
        token=token,
        timeout=timeout,
    )
    image_node_availability = json_request(
        api_base_url,
        EXPECTED_IMAGE_NODE_AVAILABILITY_PATH,
        method="POST",
        payload={"base_urls": []},
        token=token,
        timeout=timeout,
    )
    voices = json_request(
        api_base_url,
        EXPECTED_AUDIO_VOICES_PATH,
        token=token,
        timeout=timeout,
    )
    youtube_videos, youtube_subtitles = count_youtube_pairs(youtube)
    default_youtube_video, default_youtube_subtitle = preferred_youtube_selection(youtube)
    chapter_inventory = preferred_epub_chapter_inventory(api_base_url, token, files, timeout)
    acquisition_discovery_payloads: dict[str, dict[str, Any]] = {}
    return {
        "epubs": count_epubs(files),
        "subtitle_sources": count_subtitle_sources(subtitles),
        "youtube_videos": youtube_videos,
        "youtube_subtitles": youtube_subtitles,
        "default_epub_ready": preferred_epub(files) is not None,
        "default_subtitle_source_ready": preferred_subtitle_source(subtitles) is not None,
        "default_youtube_video_ready": default_youtube_video is not None,
        "default_youtube_subtitle_ready": default_youtube_subtitle is not None,
        **chapter_inventory,
        **language_inventory(book_options),
        **media_job_defaults_inventory(book_options),
        **pipeline_defaults_inventory(pipeline_defaults),
        **creation_template_inventory(creation_templates),
        **acquisition_provider_inventory(acquisition_providers),
        **acquisition_discovery_inventory(
            api_base_url,
            token,
            acquisition_providers,
            timeout,
            captured_payloads=acquisition_discovery_payloads,
        ),
        **acquisition_default_discovery_inventory(
            api_base_url,
            token,
            acquisition_providers,
            timeout,
        ),
        **acquisition_prepared_artifact_inventory(
            api_base_url,
            token,
            acquisition_providers,
            timeout,
            discovery_payloads=acquisition_discovery_payloads,
        ),
        **acquisition_job_status_inventory(api_base_url, token, timeout),
        **pipeline_intake_inventory(intake_status),
        **model_inventory(subtitle_models),
        **pipeline_llm_model_inventory(pipeline_llm_models),
        **image_node_availability_inventory(image_node_availability),
        **voice_inventory(voices),
    }


def validate_summary(summary: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if summary.get("epubs", 0) <= 0:
        missing.append("backend-visible EPUBs")
    if summary.get("subtitle_sources", 0) <= 0:
        missing.append("backend-visible subtitle sources")
    if summary.get("youtube_videos", 0) <= 0 or summary.get("youtube_subtitles", 0) <= 0:
        missing.append("YouTube/NAS videos with playable subtitles")
    if not summary.get("default_epub_ready"):
        missing.append("default Narrate EPUB source")
    if not summary.get("default_epub_chapter_index_ready"):
        missing.append("default Narrate EPUB chapter index")
    if not summary.get("default_subtitle_source_ready"):
        missing.append("default subtitle source")
    if not summary.get("default_youtube_video_ready") or not summary.get("default_youtube_subtitle_ready"):
        missing.append("default YouTube/NAS video+subtitle selection")
    if summary.get("book_input_languages", 0) < MIN_SUPPORTED_BOOK_LANGUAGES:
        missing.append("broad book input language options")
    if summary.get("book_output_languages", 0) < MIN_SUPPORTED_BOOK_LANGUAGES:
        missing.append("broad book output language options")
    missing_input = summary.get("missing_book_input_languages")
    if isinstance(missing_input, list) and missing_input:
        missing.append("book input language sentinels: " + ", ".join(missing_input))
    missing_output = summary.get("missing_book_output_languages")
    if isinstance(missing_output, list) and missing_output:
        missing.append("book output language sentinels: " + ", ".join(missing_output))
    if not summary.get("generated_book_defaults_ready"):
        errors = summary.get("generated_book_defaults_errors")
        suffix = ": " + ", ".join(errors) if isinstance(errors, list) and errors else ""
        missing.append("generated book defaults" + suffix)
    if not summary.get("sentence_splitter_capabilities_ready"):
        errors = summary.get("sentence_splitter_capabilities_errors")
        suffix = ": " + ", ".join(errors) if isinstance(errors, list) and errors else ""
        missing.append("sentence splitter capabilities" + suffix)
    if not summary.get("subtitle_job_defaults_ready"):
        errors = summary.get("subtitle_job_defaults_errors")
        suffix = ": " + ", ".join(errors) if isinstance(errors, list) and errors else ""
        missing.append("subtitle job processing defaults" + suffix)
    if not summary.get("youtube_dub_defaults_ready"):
        errors = summary.get("youtube_dub_defaults_errors")
        suffix = ": " + ", ".join(errors) if isinstance(errors, list) and errors else ""
        missing.append("YouTube dubbing processing defaults" + suffix)
    if not summary.get("pipeline_defaults_route_ready"):
        missing.append("pipeline defaults endpoint")
    if not summary.get("creation_templates_route_ready"):
        missing.append("creation template list endpoint")
    if not summary.get("acquisition_providers_ready"):
        missing_providers = summary.get("missing_acquisition_providers")
        invalid_providers = summary.get("invalid_acquisition_providers")
        default_provider_issues = summary.get("acquisition_default_provider_issues")
        details: list[str] = []
        if isinstance(missing_providers, list) and missing_providers:
            details.append("missing " + ", ".join(missing_providers))
        if isinstance(invalid_providers, list) and invalid_providers:
            details.append("invalid " + ", ".join(invalid_providers))
        if isinstance(default_provider_issues, list) and default_provider_issues:
            details.append("default " + ", ".join(default_provider_issues))
        suffix = ": " + "; ".join(details) if details else ""
        missing.append("acquisition provider registry" + suffix)
    if not summary.get("download_station_handoff_ready"):
        issues = summary.get("download_station_handoff_issues")
        suffix = ": " + ", ".join(issues) if isinstance(issues, list) and issues else ""
        missing.append("Download Station indexer handoff" + suffix)
    if not summary.get("acquisition_discovery_route_ready"):
        issues = summary.get("acquisition_discovery_issues")
        suffix = ": " + ", ".join(issues) if isinstance(issues, list) and issues else ""
        missing.append("acquisition discovery endpoint" + suffix)
    if not summary.get("acquisition_default_discovery_route_ready"):
        issues = summary.get("acquisition_default_discovery_issues")
        suffix = ": " + ", ".join(issues) if isinstance(issues, list) and issues else ""
        missing.append("default acquisition discovery fanout" + suffix)
    if not summary.get("acquisition_artifact_prepare_route_ready"):
        issues = summary.get("acquisition_artifact_prepare_issues")
        suffix = ": " + ", ".join(issues) if isinstance(issues, list) and issues else ""
        missing.append("acquisition artifact prepare endpoint" + suffix)
    if not summary.get("acquisition_job_status_route_ready"):
        issues = summary.get("acquisition_job_status_issues")
        suffix = ": " + ", ".join(issues) if isinstance(issues, list) and issues else ""
        missing.append("acquisition job status endpoint" + suffix)
    if not summary.get("pipeline_intake_ready"):
        missing.append("pipeline intake status endpoint")
    if not summary.get("subtitle_models_ready"):
        missing.append("subtitle model inventory endpoint")
    if not summary.get("pipeline_llm_models_ready"):
        missing.append("pipeline LLM model inventory endpoint")
    if not summary.get("image_node_availability_ready"):
        missing.append("image-node availability endpoint")
    if not summary.get("voice_inventory_ready"):
        missing.append("audio voice inventory endpoint")
    return missing


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env", help="Path to optional .env file")
    parser.add_argument("--api-base-url", default=None, help="Override E2E_API_BASE_URL")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    username, password, api_base_url = resolve_settings(Path(args.env_file))
    if args.api_base_url:
        api_base_url = args.api_base_url.strip().rstrip("/")

    if not username or not password:
        print(
            "Apple Create readiness preflight failed: E2E_USERNAME and E2E_PASSWORD are required.",
            file=sys.stderr,
        )
        return 2
    if not api_base_url:
        print("Apple Create readiness preflight failed: API base URL is empty.", file=sys.stderr)
        return 2

    try:
        token = login(api_base_url, username, password, args.timeout)
        summary = fetch_readiness(api_base_url, token, args.timeout)
    except error.HTTPError as exc:
        print(f"Apple Create readiness preflight failed: {describe_http_error(exc)}.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Apple Create readiness preflight failed: {exc}", file=sys.stderr)
        return 1

    missing = validate_summary(summary)
    print(
        "Apple Create readiness inventory: "
        f"epubs={summary['epubs']} "
        f"subtitle_sources={summary['subtitle_sources']} "
        f"youtube_videos={summary['youtube_videos']} "
        f"youtube_subtitles={summary['youtube_subtitles']} "
        f"default_epub_ready={summary['default_epub_ready']} "
        f"default_epub_chapters={summary['default_epub_chapters']} "
        f"default_epub_chapter_index_ready={summary['default_epub_chapter_index_ready']} "
        f"default_epub_chapter_ranges_ready={summary['default_epub_chapter_ranges_ready']} "
        f"default_subtitle_source_ready={summary['default_subtitle_source_ready']} "
        f"default_youtube_pair_ready={summary['default_youtube_video_ready'] and summary['default_youtube_subtitle_ready']} "
        f"book_input_languages={summary['book_input_languages']} "
        f"book_output_languages={summary['book_output_languages']} "
        f"generated_book_defaults_ready={summary['generated_book_defaults_ready']} "
        f"sentence_splitter_capabilities_ready={summary['sentence_splitter_capabilities_ready']} "
        f"subtitle_job_defaults_ready={summary['subtitle_job_defaults_ready']} "
        f"youtube_dub_defaults_ready={summary['youtube_dub_defaults_ready']} "
        f"pipeline_defaults_route_ready={summary['pipeline_defaults_route_ready']} "
        f"pipeline_defaults_config_keys={summary['pipeline_defaults_config_keys']} "
        f"creation_templates={summary['creation_templates']} "
        f"creation_templates_route_ready={summary['creation_templates_route_ready']} "
        f"acquisition_providers={summary['acquisition_providers']} "
        f"acquisition_providers_ready={summary['acquisition_providers_ready']} "
        f"acquisition_default_book_providers={summary['acquisition_default_book_providers']} "
        f"acquisition_default_video_providers={summary['acquisition_default_video_providers']} "
        f"acquisition_default_providers_ready={summary['acquisition_default_providers_ready']} "
        f"zlibrary_policy_ready={summary['zlibrary_policy_ready']} "
        f"download_station_handoff_ready={summary['download_station_handoff_ready']} "
        f"acquisition_discovery_route_ready={summary['acquisition_discovery_route_ready']} "
        f"acquisition_book_discovery_candidates={summary['acquisition_book_discovery_candidates']} "
        f"acquisition_video_discovery_candidates={summary['acquisition_video_discovery_candidates']} "
        f"acquisition_default_discovery_route_ready={summary['acquisition_default_discovery_route_ready']} "
        f"acquisition_default_book_discovery_candidates={summary['acquisition_default_book_discovery_candidates']} "
        f"acquisition_default_video_discovery_candidates={summary['acquisition_default_video_discovery_candidates']} "
        f"acquisition_artifact_prepare_route_ready={summary['acquisition_artifact_prepare_route_ready']} "
        f"acquisition_job_status_route_ready={summary['acquisition_job_status_route_ready']} "
        f"pipeline_intake_ready={summary['pipeline_intake_ready']} "
        f"pipeline_intake_accepting_jobs={summary['pipeline_intake_accepting_jobs']} "
        f"pipeline_intake_queue_depth={summary['pipeline_intake_queue_depth']} "
        f"pipeline_intake_active_count={summary['pipeline_intake_active_count']} "
        f"subtitle_models={summary['subtitle_models']} "
        f"subtitle_models_ready={summary['subtitle_models_ready']} "
        f"pipeline_llm_models={summary['pipeline_llm_models']} "
        f"pipeline_llm_models_ready={summary['pipeline_llm_models_ready']} "
        f"image_node_availability_ready={summary['image_node_availability_ready']} "
        f"image_nodes_checked={summary['image_nodes_checked']} "
        f"image_nodes_available={summary['image_nodes_available']} "
        f"image_nodes_unavailable={summary['image_nodes_unavailable']} "
        f"macos_voices={summary['macos_voices']} "
        f"gtts_voices={summary['gtts_voices']} "
        f"piper_voices={summary['piper_voices']} "
        f"voice_inventory_ready={summary['voice_inventory_ready']}"
    )
    if missing:
        print(
            "Apple Create readiness preflight failed: missing "
            + ", ".join(missing)
            + ".",
            file=sys.stderr,
        )
        return 1
    print("Apple Create readiness preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
