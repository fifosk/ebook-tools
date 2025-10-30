from __future__ import annotations

from pathlib import Path

from modules.config_manager import loader as cfg_loader


def _reset_settings(monkeypatch):
    monkeypatch.setattr(cfg_loader, "_ACTIVE_SETTINGS", None)


def test_settings_provide_storage_defaults(monkeypatch):
    _reset_settings(monkeypatch)
    monkeypatch.delenv("JOB_STORAGE_DIR", raising=False)
    monkeypatch.delenv("EBOOK_STORAGE_BASE_URL", raising=False)

    settings = cfg_loader.get_settings()

    assert settings.job_storage_dir == str(Path("storage"))
    assert settings.storage_base_url == ""


def test_settings_respect_storage_env(monkeypatch, tmp_path):
    _reset_settings(monkeypatch)
    custom_dir = tmp_path / "custom"
    monkeypatch.setenv("JOB_STORAGE_DIR", str(custom_dir))
    monkeypatch.setenv("EBOOK_STORAGE_BASE_URL", "https://example.com/jobs")

    settings = cfg_loader.get_settings()

    assert settings.job_storage_dir == str(custom_dir)
    assert settings.storage_base_url == "https://example.com/jobs"
