#!/usr/bin/env python3
"""Preflight native Apple Create readiness before running XCUITest journeys."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import ssl
import sys
from typing import Any
from urllib import error, parse, request
from datetime import datetime


DEFAULT_API_BASE_URL = "https://api.langtools.fifosk.synology.me"
EXPECTED_BOOK_OPTIONS_PATH = "/api/books/options"
EXPECTED_BOOK_JOBS_PATH = "/api/books/jobs"
EXPECTED_CREATE_PATHS = {
    "bookOptionsPath": EXPECTED_BOOK_OPTIONS_PATH,
    "bookJobsPath": EXPECTED_BOOK_JOBS_PATH,
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
    "templateListPath": "/api/creation/templates",
    "templatePathTemplate": "/api/creation/templates/{template_id}",
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
    parsed = parse.urlparse(getattr(exc, "url", "") or "")
    target = parsed.path or getattr(exc, "url", "") or "request"
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
    return sum(
        1
        for entry in ebooks
        if isinstance(entry, dict)
        and str(entry.get("type") or "").strip().lower() == "file"
        and str(entry.get("path") or "").strip()
    )


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


def preferred_epub(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    ebooks = payload.get("ebooks")
    if not isinstance(ebooks, list):
        return None
    candidates = [
        entry
        for entry in ebooks
        if isinstance(entry, dict)
        and str(entry.get("type") or "").strip().lower() == "file"
        and str(entry.get("path") or "").strip()
    ]
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
        }
    path = str(entry.get("path") or "").strip()
    if not path:
        return {
            "default_epub_chapter_index_ready": False,
            "default_epub_chapters": 0,
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
        }
    chapter_count = content_index_chapter_count(payload)
    return {
        "default_epub_chapter_index_ready": chapter_count > 0,
        "default_epub_chapters": chapter_count,
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


def media_job_defaults_inventory(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        generated_errors = ["book options missing"]
        subtitle_errors = ["subtitle_defaults missing"]
        youtube_errors = ["youtube_dub_defaults missing"]
    else:
        generated_errors = validate_generated_book_defaults(payload)
        subtitle_errors = validate_subtitle_defaults(payload.get("subtitle_defaults"))
        youtube_errors = validate_youtube_dub_defaults(payload.get("youtube_dub_defaults"))
    return {
        "generated_book_defaults_ready": not generated_errors,
        "subtitle_job_defaults_ready": not subtitle_errors,
        "youtube_dub_defaults_ready": not youtube_errors,
        "generated_book_defaults_errors": generated_errors,
        "subtitle_job_defaults_errors": subtitle_errors,
        "youtube_dub_defaults_errors": youtube_errors,
    }


def validate_runtime_create_contract(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["runtime descriptor was not a JSON object"]

    creation = payload.get("creation")
    if not isinstance(creation, dict):
        return ["runtime descriptor is missing creation metadata"]

    return [
        f"{key}={(str(creation.get(key) or '').strip() or '<missing>')} expected {expected}"
        for key, expected in EXPECTED_CREATE_PATHS.items()
        if str(creation.get(key) or "").strip() != expected
    ]


def require_runtime_create_contract(api_base_url: str, timeout: float) -> None:
    runtime = json_request(api_base_url, "/api/system/runtime", timeout=timeout)
    errors = validate_runtime_create_contract(runtime)
    if errors:
        raise RuntimeError(
            "Backend runtime Create contract is not ready: " + "; ".join(errors)
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
    creation_templates = json_request(
        api_base_url,
        EXPECTED_CREATE_PATHS["templateListPath"],
        token=token,
        timeout=timeout,
    )
    intake_status = json_request(
        api_base_url,
        EXPECTED_CREATE_PATHS["pipelineIntakeStatusPath"],
        token=token,
        timeout=timeout,
    )
    youtube_videos, youtube_subtitles = count_youtube_pairs(youtube)
    default_youtube_video, default_youtube_subtitle = preferred_youtube_selection(youtube)
    chapter_inventory = preferred_epub_chapter_inventory(api_base_url, token, files, timeout)
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
        **creation_template_inventory(creation_templates),
        **pipeline_intake_inventory(intake_status),
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
    if not summary.get("subtitle_job_defaults_ready"):
        errors = summary.get("subtitle_job_defaults_errors")
        suffix = ": " + ", ".join(errors) if isinstance(errors, list) and errors else ""
        missing.append("subtitle job processing defaults" + suffix)
    if not summary.get("youtube_dub_defaults_ready"):
        errors = summary.get("youtube_dub_defaults_errors")
        suffix = ": " + ", ".join(errors) if isinstance(errors, list) and errors else ""
        missing.append("YouTube dubbing processing defaults" + suffix)
    if not summary.get("creation_templates_route_ready"):
        missing.append("creation template list endpoint")
    if not summary.get("pipeline_intake_ready"):
        missing.append("pipeline intake status endpoint")
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
        f"default_subtitle_source_ready={summary['default_subtitle_source_ready']} "
        f"default_youtube_pair_ready={summary['default_youtube_video_ready'] and summary['default_youtube_subtitle_ready']} "
        f"book_input_languages={summary['book_input_languages']} "
        f"book_output_languages={summary['book_output_languages']} "
        f"generated_book_defaults_ready={summary['generated_book_defaults_ready']} "
        f"subtitle_job_defaults_ready={summary['subtitle_job_defaults_ready']} "
        f"youtube_dub_defaults_ready={summary['youtube_dub_defaults_ready']} "
        f"creation_templates={summary['creation_templates']} "
        f"creation_templates_route_ready={summary['creation_templates_route_ready']} "
        f"pipeline_intake_ready={summary['pipeline_intake_ready']} "
        f"pipeline_intake_accepting_jobs={summary['pipeline_intake_accepting_jobs']} "
        f"pipeline_intake_queue_depth={summary['pipeline_intake_queue_depth']} "
        f"pipeline_intake_active_count={summary['pipeline_intake_active_count']}"
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
