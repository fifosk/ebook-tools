"""YouTube metadata helpers for acquisition discovery."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import requests


YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
ISO8601_DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


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


def string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
