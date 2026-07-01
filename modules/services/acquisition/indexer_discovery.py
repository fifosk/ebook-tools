"""Newznab/Torznab helper functions for acquisition discovery."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


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
