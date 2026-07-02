"""Newznab/Torznab helper functions for acquisition discovery."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from .discovery_values import safe_identifier
from .models import AcquisitionCandidate, AcquisitionProviderDiscoveryError
from .references import store_acquisition_reference
from .tokens import encode_acquisition_token


def discover_newznab_torznab(
    config: Mapping[str, Any],
    query: str,
    limit: int,
    *,
    session: requests.Session | None,
) -> list[AcquisitionCandidate]:
    endpoint = indexer_endpoint(config)
    if not endpoint or not query:
        return []

    client = session or requests.Session()
    params: dict[str, str | int] = {
        "t": "search",
        "q": query,
        "limit": max(1, min(limit, 100)),
    }
    api_key = indexer_api_key(config)
    if api_key:
        params["apikey"] = api_key
    category = indexer_category(config)
    if category:
        params["cat"] = category

    response = client.get(newznab_api_url(endpoint), params=params, timeout=15)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise indexer_provider_error(exc) from exc

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as exc:
        raise AcquisitionProviderDiscoveryError(
            provider="newznab_torznab",
            reason="invalid_xml",
            message="Indexer search returned an unreadable feed. Check the configured Newznab/Torznab endpoint.",
        ) from exc

    candidates: list[AcquisitionCandidate] = []
    for item in root.findall(".//item"):
        title = xml_child_text(item, "title") or "Indexer result"
        guid = xml_child_text(item, "guid") or xml_child_text(item, "link") or title
        attrs = torznab_attrs(item)
        size_bytes = int_value(attrs.get("size")) or enclosure_length(item)
        published_at = xml_child_text(item, "pubDate")
        published_dt = parse_rfc2822_datetime(published_at)
        indexer = xml_child_text(item, "author") or string_value(config.get("indexer_label"))
        categories = tuple(
            category
            for category in (
                xml_child_text(element, None)
                for element in item.findall("./category")
            )
            if category
        )
        safe_guid = safe_identifier(guid)
        source_uri = xml_child_text(item, "link") or enclosure_url(item)
        source_ref = (
            store_acquisition_reference(
                provider="newznab_torznab",
                media_kind="video",
                source_uri=source_uri,
                config=config,
                metadata={"guid": safe_guid, "title": title},
            )
            if source_uri
            else None
        )
        handoff_provider = "download_station" if source_ref else None
        token = _candidate_token(
            {
                "provider": "newznab_torznab",
                "media_kind": "video",
                "guid": safe_guid,
                "source_ref": source_ref,
                "title": title,
            }
        )
        seeders = int_value(attrs.get("seeders"))
        peers = int_value(attrs.get("peers"))
        candidates.append(
            AcquisitionCandidate(
                candidate_id=f"newznab_torznab:{safe_guid}",
                provider="newznab_torznab",
                media_kind="video",
                title=title,
                rights="unknown",
                capabilities=(
                    ("search", "metadata", "acquire")
                    if handoff_provider
                    else ("search", "metadata")
                ),
                candidate_token=token,
                contributors=tuple(value for value in (indexer,) if value),
                published_at=published_dt.isoformat() if published_dt else published_at,
                size_bytes=size_bytes,
                requires_confirmation=True,
                policy_notes=(
                    "Indexer result is metadata only; confirm lawful access before any downloader handoff.",
                    "Raw NZB, torrent, magnet, and API-key URLs stay server-side and are not returned to clients.",
                ),
                metadata={
                    "source_kind": "newznab_torznab",
                    "indexer": indexer,
                    "guid": safe_guid,
                    "categories": list(categories),
                    "seeders": seeders,
                    "peers": peers,
                    "grabs": int_value(attrs.get("grabs")),
                    "has_download_url": bool(source_ref),
                    "handoff_provider": handoff_provider,
                    "handoff_action": "confirm_acquisition" if handoff_provider else None,
                },
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def indexer_endpoint(config: Mapping[str, Any]) -> str | None:
    for key in ("prowlarr_url", "torznab_url", "newznab_url", "indexer_url"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("PROWLARR_URL", "TORZNAB_URL", "NEWZNAB_URL", "EBOOK_PROWLARR_URL"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def indexer_api_key(config: Mapping[str, Any]) -> str | None:
    for key in (
        "prowlarr_api_key",
        "torznab_api_key",
        "newznab_api_key",
        "indexer_api_key",
    ):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in (
        "PROWLARR_API_KEY",
        "TORZNAB_API_KEY",
        "NEWZNAB_API_KEY",
        "EBOOK_PROWLARR_API_KEY",
    ):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def indexer_category(config: Mapping[str, Any]) -> str | None:
    value = config.get("indexer_video_category") or config.get("torznab_video_category")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, int):
        return str(value)
    env_value = os.environ.get("TORZNAB_VIDEO_CATEGORY", "").strip()
    return env_value or None


def newznab_api_url(endpoint: str) -> str:
    parts = urlsplit(endpoint)
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.casefold() != "apikey"
        ],
        doseq=True,
    )
    path = parts.path.rstrip("/")
    if not path.endswith("/api") and path.rsplit("/", 1)[-1] != "api":
        path = f"{path}/api" if path else "/api"
    return urlunsplit((parts.scheme, parts.netloc, path, query, ""))


def xml_child_text(element: ET.Element, tag: str | None) -> str | None:
    if tag is None:
        return string_value(element.text)
    child = element.find(tag)
    if child is None:
        return None
    return string_value(child.text)


def torznab_attrs(item: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for element in item.iter():
        if not element.tag.endswith("attr"):
            continue
        name = string_value(element.attrib.get("name"))
        value = string_value(element.attrib.get("value"))
        if name and value:
            attrs[name.casefold()] = value
    return attrs


def enclosure_length(item: ET.Element) -> int | None:
    enclosure = item.find("enclosure")
    if enclosure is None:
        return None
    return int_value(enclosure.attrib.get("length"))


def enclosure_url(item: ET.Element) -> str | None:
    enclosure = item.find("enclosure")
    if enclosure is None:
        return None
    return string_value(enclosure.attrib.get("url"))


def parse_rfc2822_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, AttributeError):
        return None


def int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def indexer_provider_error(exc: requests.HTTPError) -> AcquisitionProviderDiscoveryError:
    response = exc.response
    status_code = response.status_code if response is not None else None
    if status_code in {401, 403}:
        message = "Indexer search is not authorized. Check the backend Newznab/Torznab API key."
        reason = "unauthorized"
    elif status_code == 429:
        message = "Indexer search is rate limited. Wait and try again later."
        reason = "rate_limited"
    else:
        suffix = f" HTTP {status_code}" if status_code else ""
        message = f"Indexer search failed{suffix}. Try again later."
        reason = f"http_{status_code or 'unknown'}"
    return AcquisitionProviderDiscoveryError(
        provider="newznab_torznab",
        reason=reason,
        message=message,
    )


def _candidate_token(payload: Mapping[str, Any]) -> str:
    return encode_acquisition_token(payload)
