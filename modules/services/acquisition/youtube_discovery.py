"""YouTube metadata helpers for acquisition discovery."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import requests

from .models import AcquisitionCandidate, AcquisitionProviderDiscoveryError
from .tokens import encode_acquisition_token


YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
ISO8601_DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def discover_youtube_url(query: str, limit: int) -> list[AcquisitionCandidate]:
    if limit <= 0:
        return []
    video_id = parse_youtube_url_or_id(query)
    if not video_id:
        return []
    url = f"https://www.youtube.com/watch?v={video_id}"
    token = _candidate_token(
        {
            "provider": "youtube_url",
            "media_kind": "video",
            "video_id": video_id,
            "youtube_url": url,
        }
    )
    return [
        AcquisitionCandidate(
            candidate_id=f"youtube_url:{video_id}",
            provider="youtube_url",
            media_kind="video",
            title=f"YouTube video {video_id}",
            rights="unknown",
            capabilities=("metadata", "extract_subtitles"),
            candidate_token=token,
            source_url=url,
            requires_confirmation=True,
            policy_notes=(
                "Direct YouTube URL discovery returns metadata handoff only; video/subtitle acquisition is a separate reviewed step.",
            ),
            metadata={
                "source_kind": "youtube",
                "youtube_video_id": video_id,
                "youtube_url": url,
            },
        )
    ]


def discover_youtube_search(
    config: Mapping[str, Any],
    query: str,
    limit: int,
    *,
    language: str | None,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    api_key = youtube_api_key(config)
    if not api_key or not query:
        return []

    client = session or requests.Session()
    params: dict[str, str | int] = {
        "part": "snippet",
        "type": "video",
        "maxResults": max(1, min(limit, 25)),
        "q": query,
        "key": api_key,
        "safeSearch": "moderate",
    }
    if language:
        params["relevanceLanguage"] = language
    response = client.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
    raise_for_youtube_status(response, operation="search")
    payload = response.json()
    items = payload.get("items", [])
    if not isinstance(items, Sequence):
        return []

    search_items = [item for item in items if isinstance(item, Mapping)]
    video_ids = [youtube_video_id(item) for item in search_items]
    details_by_id = fetch_youtube_video_details(client, api_key, video_ids)
    candidates: list[AcquisitionCandidate] = []
    for item in search_items:
        video_id = youtube_video_id(item)
        if not video_id:
            continue
        snippet = item.get("snippet")
        if not isinstance(snippet, Mapping):
            continue
        details = details_by_id.get(video_id, {})
        url = f"https://www.youtube.com/watch?v={video_id}"
        token = _candidate_token(
            {
                "provider": "youtube_search",
                "media_kind": "video",
                "video_id": video_id,
            }
        )
        candidates.append(
            AcquisitionCandidate(
                candidate_id=f"youtube_search:{video_id}",
                provider="youtube_search",
                media_kind="video",
                title=string_value(snippet.get("title")) or video_id,
                rights="unknown",
                capabilities=("metadata", "extract_subtitles"),
                candidate_token=token,
                contributors=tuple(
                    value
                    for value in [string_value(snippet.get("channelTitle"))]
                    if value
                ),
                published_at=string_value(snippet.get("publishedAt")),
                source_url=url,
                thumbnail_url=youtube_thumbnail(snippet),
                duration_seconds=parse_iso8601_duration(
                    string_value(details.get("duration"))
                ),
                requires_confirmation=True,
                policy_notes=(
                    "YouTube search uses metadata only; video/subtitle acquisition is a separate reviewed step.",
                ),
                metadata={
                    "source_kind": "youtube",
                    "youtube_video_id": video_id,
                    "youtube_url": url,
                    "channel": string_value(snippet.get("channelTitle")),
                },
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def parse_youtube_url_or_id(value: str) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    if YOUTUBE_ID_PATTERN.fullmatch(candidate):
        return candidate
    if candidate.casefold().startswith(
        (
            "youtube.com/",
            "www.youtube.com/",
            "m.youtube.com/",
            "youtu.be/",
            "www.youtu.be/",
        )
    ):
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").casefold()
    if hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/", 1)[0]
        return video_id if YOUTUBE_ID_PATTERN.fullmatch(video_id) else None
    if hostname.endswith("youtube.com"):
        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts and path_parts[0] in {"shorts", "embed", "live"} and len(path_parts) > 1:
            video_id = path_parts[1]
            return video_id if YOUTUBE_ID_PATTERN.fullmatch(video_id) else None
        query_params = dict(parse_qsl(parsed.query, keep_blank_values=False))
        video_id = query_params.get("v")
        return video_id if video_id and YOUTUBE_ID_PATTERN.fullmatch(video_id) else None
    return None


def youtube_video_id(item: Mapping[str, Any]) -> str | None:
    item_id = item.get("id")
    if isinstance(item_id, Mapping):
        return string_value(item_id.get("videoId"))
    return None


def youtube_thumbnail(snippet: Mapping[str, Any]) -> str | None:
    thumbnails = snippet.get("thumbnails")
    if not isinstance(thumbnails, Mapping):
        return None
    for key in ("high", "medium", "default"):
        entry = thumbnails.get(key)
        if isinstance(entry, Mapping):
            value = string_value(entry.get("url"))
            if value:
                return value
    return None


def parse_iso8601_duration(value: str | None) -> int | None:
    if not value:
        return None
    match = ISO8601_DURATION_PATTERN.match(value)
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def youtube_api_key(config: Mapping[str, Any]) -> str | None:
    for key in ("youtube_api_key", "youtube_data_api_key"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("YOUTUBE_API_KEY", "EBOOK_YOUTUBE_API_KEY"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def youtube_error_reason(response: requests.Response | None) -> str:
    if response is None:
        return ""
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, Mapping):
        return ""
    error = payload.get("error")
    if not isinstance(error, Mapping):
        return ""
    errors = error.get("errors")
    if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)):
        for item in errors:
            if not isinstance(item, Mapping):
                continue
            reason = string_value(item.get("reason"))
            if reason:
                return reason
    status_reason = string_value(error.get("status"))
    return status_reason or string_value(error.get("reason")) or ""


def fetch_youtube_video_details(
    client: requests.Session,
    api_key: str,
    video_ids: Sequence[str | None],
) -> dict[str, Mapping[str, Any]]:
    ids = [video_id for video_id in video_ids if video_id]
    if not ids:
        return {}
    response = client.get(
        YOUTUBE_VIDEOS_URL,
        params={
            "part": "contentDetails,snippet",
            "id": ",".join(ids[:50]),
            "key": api_key,
        },
        timeout=10,
    )
    raise_for_youtube_status(response, operation="details")
    payload = response.json()
    items = payload.get("items", [])
    details: dict[str, Mapping[str, Any]] = {}
    if not isinstance(items, Sequence):
        return details
    for item in items:
        if not isinstance(item, Mapping):
            continue
        video_id = string_value(item.get("id"))
        content_details = item.get("contentDetails")
        if video_id and isinstance(content_details, Mapping):
            details[video_id] = {
                "duration": content_details.get("duration"),
            }
    return details


def raise_for_youtube_status(response: requests.Response, *, operation: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise youtube_provider_error(exc, operation=operation) from exc


def youtube_provider_error(
    exc: requests.HTTPError,
    *,
    operation: str,
) -> AcquisitionProviderDiscoveryError:
    response = exc.response
    status_code = response.status_code if response is not None else None
    reason = youtube_error_reason(response)
    normalized_reason = reason.casefold()
    if normalized_reason in {
        "quotaexceeded",
        "dailylimitexceeded",
        "ratelimitexceeded",
        "userratelimitexceeded",
    }:
        message = (
            "YouTube search quota or rate limit was exceeded. "
            "Check the backend YouTube Data API quota, then try again."
        )
    elif normalized_reason in {
        "keyinvalid",
        "accessnotconfigured",
        "forbidden",
        "insufficientpermissions",
        "iprefererblocked",
    } or status_code in {401, 403}:
        message = (
            "YouTube search is not authorized. "
            "Check the backend YouTube Data API key and API enablement."
        )
    elif status_code == 429:
        message = (
            "YouTube search is rate limited. Wait for quota to recover, then try again."
        )
    else:
        suffix = f" HTTP {status_code}" if status_code else ""
        message = f"YouTube search {operation} failed{suffix}. Try again later."
    return AcquisitionProviderDiscoveryError(
        provider="youtube_search",
        reason=reason or f"http_{status_code or 'unknown'}",
        message=message,
    )


def string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _candidate_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)
