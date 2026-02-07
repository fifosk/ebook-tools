"""Shared fixtures for WebAPI route tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.services.file_locator import FileLocator
from modules.webapi.application import create_app
from modules.webapi.dependencies import get_file_locator


@pytest.fixture
def webapi_app(tmp_path: Path) -> tuple[FastAPI, FileLocator]:
    """Create a fresh FastAPI app with a FileLocator wired to *tmp_path*.

    Yields ``(app, file_locator)`` and clears dependency overrides on teardown.
    """
    app = create_app()
    locator = FileLocator(storage_dir=tmp_path)

    app.dependency_overrides[get_file_locator] = lambda: locator
    yield app, locator
    app.dependency_overrides.clear()
