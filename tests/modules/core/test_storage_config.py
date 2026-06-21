"""Tests for ML model storage configuration."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.config


class TestStorageConfigPaths:
    """Tests for storage path configuration functions."""

    def test_get_piper_models_path_default(self, monkeypatch):
        """Test default Piper models path when no env var set."""
        from modules.core.storage_config import (
            DEFAULT_PIPER_MODELS_PATH,
            get_piper_models_path,
        )

        monkeypatch.delenv("EBOOK_PIPER_MODELS_PATH", raising=False)

        path = get_piper_models_path()
        assert path == DEFAULT_PIPER_MODELS_PATH

    def test_get_piper_models_path_custom(self, monkeypatch, tmp_path):
        """Test custom Piper models path from environment variable."""
        from modules.core.storage_config import get_piper_models_path

        custom_path = tmp_path / "custom-piper"
        monkeypatch.setenv("EBOOK_PIPER_MODELS_PATH", str(custom_path))

        path = get_piper_models_path()
        assert path == custom_path
        assert path.exists()  # Should be created automatically

    def test_get_whisperx_models_path_default(self, monkeypatch):
        """Test default WhisperX models path when no env var set."""
        from modules.core.storage_config import (
            DEFAULT_WHISPERX_MODELS_PATH,
            get_whisperx_models_path,
        )

        monkeypatch.delenv("EBOOK_WHISPERX_MODELS_PATH", raising=False)

        path = get_whisperx_models_path()
        assert path == DEFAULT_WHISPERX_MODELS_PATH

    def test_get_whisperx_models_path_custom(self, monkeypatch, tmp_path):
        """Test custom WhisperX models path from environment variable."""
        from modules.core.storage_config import get_whisperx_models_path

        custom_path = tmp_path / "custom-whisperx"
        monkeypatch.setenv("EBOOK_WHISPERX_MODELS_PATH", str(custom_path))

        path = get_whisperx_models_path()
        assert path == custom_path
        assert path.exists()

    def test_get_hf_cache_path_default(self, monkeypatch):
        """Test default HuggingFace cache path when no env var set."""
        from modules.core.storage_config import (
            DEFAULT_HF_CACHE_PATH,
            get_hf_cache_path,
        )

        monkeypatch.delenv("EBOOK_HF_CACHE_PATH", raising=False)

        path = get_hf_cache_path()
        assert path == DEFAULT_HF_CACHE_PATH

    def test_get_hf_cache_path_custom(self, monkeypatch, tmp_path):
        """Test custom HuggingFace cache path from environment variable."""
        from modules.core.storage_config import get_hf_cache_path

        custom_path = tmp_path / "custom-hf"
        monkeypatch.setenv("EBOOK_HF_CACHE_PATH", str(custom_path))

        path = get_hf_cache_path()
        assert path == custom_path
        assert path.exists()


class TestHuggingFaceEnvironment:
    """Tests for HuggingFace environment variable configuration."""

    def test_configure_hf_environment_sets_vars(self, monkeypatch, tmp_path):
        """Test that configure_hf_environment sets HF environment variables."""
        from modules.core.storage_config import configure_hf_environment

        custom_path = tmp_path / "hf-cache"
        monkeypatch.setenv("EBOOK_HF_CACHE_PATH", str(custom_path))

        # Clear existing HF env vars
        for key in ["HF_HOME", "HUGGINGFACE_HUB_CACHE", "HF_DATASETS_CACHE"]:
            monkeypatch.delenv(key, raising=False)

        configure_hf_environment()

        assert os.environ["HF_HOME"] == str(custom_path)
        assert os.environ["HUGGINGFACE_HUB_CACHE"] == str(custom_path / "hub")
        assert os.environ["HF_DATASETS_CACHE"] == str(custom_path / "datasets")

    def test_configure_hf_environment_respects_existing(self, monkeypatch, tmp_path):
        """Test that configure_hf_environment doesn't overwrite existing vars."""
        from modules.core.storage_config import configure_hf_environment

        custom_path = tmp_path / "hf-cache"
        existing_path = tmp_path / "existing-hf"
        monkeypatch.setenv("EBOOK_HF_CACHE_PATH", str(custom_path))
        monkeypatch.setenv("HF_HOME", str(existing_path))

        configure_hf_environment()

        # Should keep existing value
        assert os.environ["HF_HOME"] == str(existing_path)

    def test_pytest_hf_cache_falls_back_when_configured_path_unusable(
        self, monkeypatch, tmp_path
    ):
        """Pytest should use a local cache when workstation media is offline."""
        import tests.conftest as root_conftest

        blocked_path = tmp_path / "offline-volume"
        blocked_path.write_text("not a directory", encoding="utf-8")
        fallback_path = tmp_path / "fallback-hf-cache"

        monkeypatch.setenv("EBOOK_HF_CACHE_PATH", str(blocked_path / "huggingface"))
        monkeypatch.setenv("HF_HOME", str(blocked_path / "hf-home"))
        monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(blocked_path / "hub"))
        monkeypatch.setenv("HF_DATASETS_CACHE", str(blocked_path / "datasets"))
        monkeypatch.setenv("EBOOK_TEST_HF_CACHE_PATH", str(fallback_path))

        root_conftest._prepare_hf_cache_for_tests()

        assert os.environ["EBOOK_HF_CACHE_PATH"] == str(fallback_path)
        assert fallback_path.exists()
        assert "HF_HOME" not in os.environ
        assert "HUGGINGFACE_HUB_CACHE" not in os.environ
        assert "HF_DATASETS_CACHE" not in os.environ

    def test_pytest_hf_cache_keeps_configured_path_when_writable(
        self, monkeypatch, tmp_path
    ):
        """Writable explicit cache paths should remain the test cache."""
        import tests.conftest as root_conftest

        configured_path = tmp_path / "configured-hf-cache"
        monkeypatch.setenv("EBOOK_HF_CACHE_PATH", str(configured_path))

        root_conftest._prepare_hf_cache_for_tests()

        assert os.environ["EBOOK_HF_CACHE_PATH"] == str(configured_path)


class TestExternalSSDConfiguration:
    """Tests for external SSD storage configuration."""

    def test_external_ssd_paths_configured(self, monkeypatch, tmp_path):
        """Test configuration with external SSD paths like /Volumes/WD-1TB."""
        from modules.core.storage_config import (
            get_hf_cache_path,
            get_piper_models_path,
            get_whisperx_models_path,
        )

        # Simulate external SSD configuration
        base_path = tmp_path / "Volumes" / "WD-1TB" / "ml-models"
        monkeypatch.setenv("EBOOK_PIPER_MODELS_PATH", f"{base_path}/piper-voices")
        monkeypatch.setenv("EBOOK_WHISPERX_MODELS_PATH", f"{base_path}/whisperx")
        monkeypatch.setenv("EBOOK_HF_CACHE_PATH", f"{base_path}/huggingface")

        piper_path = get_piper_models_path()
        whisperx_path = get_whisperx_models_path()
        hf_path = get_hf_cache_path()

        assert "WD-1TB" in str(piper_path)
        assert "piper-voices" in str(piper_path)
        assert "WD-1TB" in str(whisperx_path)
        assert "whisperx" in str(whisperx_path)
        assert "WD-1TB" in str(hf_path)
        assert "huggingface" in str(hf_path)


class TestModelPathsSummary:
    """Tests for the model paths summary function."""

    def test_get_model_paths_summary(self, monkeypatch, tmp_path):
        """Test getting summary of all model paths."""
        from modules.core.storage_config import get_model_paths_summary
        piper_path = tmp_path / "piper"
        whisperx_path = tmp_path / "whisperx"
        hf_path = tmp_path / "hf"

        monkeypatch.setenv("EBOOK_PIPER_MODELS_PATH", str(piper_path))
        monkeypatch.setenv("EBOOK_WHISPERX_MODELS_PATH", str(whisperx_path))
        monkeypatch.setenv("EBOOK_HF_CACHE_PATH", str(hf_path))

        summary = get_model_paths_summary()

        assert "piper_models" in summary
        assert "whisperx_models" in summary
        assert "hf_cache" in summary
        assert str(piper_path) in summary["piper_models"]
        assert str(whisperx_path) in summary["whisperx_models"]
        assert str(hf_path) in summary["hf_cache"]
