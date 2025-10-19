"""Utilities for retrieving book cover images from remote services."""

from __future__ import annotations

import io
import urllib.parse
from typing import Optional

import requests
from PIL import Image

from . import logging_manager as log_mgr

logger = log_mgr.logger


def fetch_book_cover(query: str, debug_enabled: bool = False) -> Optional[Image.Image]:
    """Retrieve a book cover image from OpenLibrary when available."""
    encoded = urllib.parse.quote(query)
    url = f"http://openlibrary.org/search.json?title={encoded}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        for doc in data.get("docs", []):
            cover_id = doc.get("cover_i")
            if cover_id is None:
                continue
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
            cover_response = requests.get(cover_url, stream=True, timeout=10)
            if cover_response.status_code != 200:
                continue
            image = Image.open(io.BytesIO(cover_response.content))
            image.load()
            return image
        return None
    except Exception as exc:  # pragma: no cover - network errors
        if debug_enabled:
            logger.error("Error fetching book cover: %s", exc)
        return None
