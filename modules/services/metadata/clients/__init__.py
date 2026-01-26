"""Metadata lookup client implementations."""

from __future__ import annotations

from .base import BaseMetadataClient
from .openlibrary import OpenLibraryClient
from .tvmaze import TVMazeClient
from .ytdlp import YtDlpClient
from .tmdb import TMDBClient
from .omdb import OMDbClient
from .google_books import GoogleBooksClient
from .wikipedia import WikipediaClient

__all__ = [
    "BaseMetadataClient",
    "GoogleBooksClient",
    "OMDbClient",
    "OpenLibraryClient",
    "TMDBClient",
    "TVMazeClient",
    "WikipediaClient",
    "YtDlpClient",
]
