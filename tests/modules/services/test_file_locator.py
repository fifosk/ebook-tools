from __future__ import annotations

import types

import pytest

from modules.services.file_locator import FileLocator


def _settings_stub(job_storage_dir: str, storage_base_url: str = "") -> object:
    return types.SimpleNamespace(
        job_storage_dir=job_storage_dir, storage_base_url=storage_base_url
    )


def test_resolve_path_uses_storage_root(tmp_path):
    settings = _settings_stub(str(tmp_path / "jobs"))
    locator = FileLocator(settings_provider=lambda: settings)

    path = locator.resolve_path("job with space")

    assert path == (tmp_path / "jobs" / "job_with_space")


def test_resolve_path_rejects_traversal(tmp_path):
    settings = _settings_stub(str(tmp_path / "jobs"))
    locator = FileLocator(settings_provider=lambda: settings)

    with pytest.raises(ValueError):
        locator.resolve_path("job", "../escape.txt")


def test_resolve_url_builds_from_base(tmp_path):
    settings = _settings_stub(str(tmp_path / "jobs"), "https://example.com/storage")
    locator = FileLocator(settings_provider=lambda: settings)

    url = locator.resolve_url("job 1", "folder/output.epub")

    assert url == "https://example.com/storage/job_1/folder/output.epub"


def test_resolve_url_rejects_parent_path(tmp_path):
    settings = _settings_stub(str(tmp_path / "jobs"), "https://example.com/storage")
    locator = FileLocator(settings_provider=lambda: settings)

    with pytest.raises(ValueError):
        locator.resolve_url("job", "../escape")


def test_resolve_url_without_base_returns_none(tmp_path):
    settings = _settings_stub(str(tmp_path / "jobs"), "")
    locator = FileLocator(settings_provider=lambda: settings)

    assert locator.resolve_url("job") is None
