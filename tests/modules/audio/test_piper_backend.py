"""Tests for Piper TTS backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydub import AudioSegment

import modules.audio.backends as backend_registry
import modules.audio.backends.piper as piper_backend
from modules.audio.backends import (
    PiperTTSBackend,
    TTSBackendError,
    create_backend,
    get_tts_backend,
)

pytestmark = [pytest.mark.audio, pytest.mark.slow]


class TestPiperBackendRegistration:
    """Tests for Piper backend registration and creation."""

    def test_piper_backend_registered(self):
        """Test that Piper backend is registered in the registry."""
        assert "piper" in backend_registry._BACKENDS

    def test_create_piper_backend(self):
        """Test creating Piper backend instance via create_backend."""
        backend = create_backend("piper")
        assert isinstance(backend, PiperTTSBackend)
        assert backend.name == "piper"

    def test_piper_name_resolution(self):
        """Test Piper backend name resolves correctly."""
        backend = create_backend("piper")
        assert isinstance(backend, PiperTTSBackend)
        assert backend.name == "piper"

    def test_get_tts_backend_with_piper_config(self):
        """Test get_tts_backend selects Piper when configured."""
        backend = get_tts_backend({"tts_backend": "piper"})
        assert isinstance(backend, PiperTTSBackend)


class TestPiperVoiceConfig:
    """Tests for Piper voice configuration loading."""

    def test_load_voice_config(self, tmp_path):
        """Test loading Piper voice configuration from YAML."""
        from modules.audio.backends.piper import load_piper_voice_config

        config_content = """
voices:
  en:
    - en_US-lessac-medium
    - en_US-amy-medium
  de:
    - de_DE-thorsten-medium
fallbacks:
  kk: tr
"""
        config_file = tmp_path / "piper_voices.yaml"
        config_file.write_text(config_content)

        # Clear cache before test
        load_piper_voice_config.cache_clear()

        config = load_piper_voice_config(str(config_file))
        assert "voices" in config
        assert "en" in config["voices"]
        assert config["voices"]["en"][0] == "en_US-lessac-medium"
        assert config["fallbacks"]["kk"] == "tr"

    def test_load_voice_config_missing_file(self, tmp_path):
        """Test loading config returns empty dict when file missing."""
        from modules.audio.backends.piper import load_piper_voice_config

        load_piper_voice_config.cache_clear()
        config = load_piper_voice_config(str(tmp_path / "nonexistent.yaml"))
        assert config == {}

    def test_get_voice_for_language(self, tmp_path, monkeypatch):
        """Test getting voice for a language code."""
        from modules.audio.backends import piper as piper_module
        from modules.audio.backends.piper import get_voice_for_language

        mock_config = {
            "voices": {
                "en": ["en_US-lessac-medium", "en_US-amy-medium"],
                "de": ["de_DE-thorsten-medium"],
            },
            "fallbacks": {"kk": "tr"},
        }
        monkeypatch.setattr(
            piper_module, "load_piper_voice_config", lambda path=None: mock_config
        )
        monkeypatch.setattr(piper_module, "get_piper_models_path", lambda: tmp_path)

        voice = get_voice_for_language("en")
        assert voice == "en_US-lessac-medium"

    def test_get_voice_for_language_with_fallback(self, tmp_path, monkeypatch):
        """Test fallback to related language when no direct match."""
        from modules.audio.backends import piper as piper_module
        from modules.audio.backends.piper import get_voice_for_language

        mock_config = {
            "voices": {
                "tr": ["tr_TR-dfki-medium"],
            },
            "fallbacks": {"kk": "tr"},  # Kazakh falls back to Turkish
        }
        monkeypatch.setattr(
            piper_module, "load_piper_voice_config", lambda path=None: mock_config
        )
        monkeypatch.setattr(piper_module, "get_piper_models_path", lambda: tmp_path)

        voice = get_voice_for_language("kk")
        assert voice == "tr_TR-dfki-medium"

    def test_get_voice_for_unsupported_language(self, tmp_path, monkeypatch):
        """Test returns None for unsupported language without fallback."""
        from modules.audio.backends import piper as piper_module
        from modules.audio.backends.piper import get_voice_for_language

        mock_config = {
            "voices": {"en": ["en_US-lessac-medium"]},
            "fallbacks": {},
        }
        monkeypatch.setattr(
            piper_module, "load_piper_voice_config", lambda path=None: mock_config
        )
        monkeypatch.setattr(piper_module, "get_piper_models_path", lambda: tmp_path)

        voice = get_voice_for_language("xyz")
        assert voice is None


class TestPiperSpeedConversion:
    """Tests for speed to length_scale conversion."""

    def test_speed_to_length_scale_default(self):
        """Test default speed (175 WPM) produces length_scale of 1.0."""
        from modules.audio.backends.piper import _speed_to_length_scale

        assert _speed_to_length_scale(175) == 1.0

    def test_speed_to_length_scale_faster(self):
        """Test faster speed produces lower length_scale."""
        from modules.audio.backends.piper import _speed_to_length_scale

        # Double speed = half length_scale
        length_scale = _speed_to_length_scale(350)
        assert length_scale == 0.5

    def test_speed_to_length_scale_slower(self):
        """Test slower speed produces higher length_scale."""
        from modules.audio.backends.piper import _speed_to_length_scale

        # Half speed = double length_scale
        length_scale = _speed_to_length_scale(87)
        assert length_scale == pytest.approx(2.0, rel=0.1)

    def test_speed_to_length_scale_clamped_fast(self):
        """Test very fast speed is clamped to 0.5."""
        from modules.audio.backends.piper import _speed_to_length_scale

        assert _speed_to_length_scale(1000) == 0.5

    def test_speed_to_length_scale_clamped_slow(self):
        """Test very slow speed is clamped to 2.0."""
        from modules.audio.backends.piper import _speed_to_length_scale

        assert _speed_to_length_scale(50) == 2.0

    def test_speed_to_length_scale_zero(self):
        """Test zero speed returns 1.0 (default)."""
        from modules.audio.backends.piper import _speed_to_length_scale

        assert _speed_to_length_scale(0) == 1.0

    def test_speed_to_length_scale_negative(self):
        """Test negative speed returns 1.0 (default)."""
        from modules.audio.backends.piper import _speed_to_length_scale

        assert _speed_to_length_scale(-100) == 1.0


class TestPiperSynthesis:
    """Tests for Piper TTS synthesis."""

    def test_synthesize_with_mocked_piper_voice(self, tmp_path, monkeypatch):
        """Test synthesis with mocked Piper voice."""
        from modules.audio.backends.piper import PiperTTSBackend

        # Create mock voice that produces silence using the new API
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050

        # Create mock AudioChunk
        mock_chunk = MagicMock()
        mock_chunk.audio_int16_bytes = b"\x00" * 44100  # 1 second of silence

        def mock_synthesize(text, syn_config=None):
            yield mock_chunk

        mock_voice.synthesize = mock_synthesize

        monkeypatch.setattr(
            piper_backend, "_get_voice_model",
            lambda name: mock_voice,
        )
        monkeypatch.setattr(
            piper_backend, "get_voice_for_language",
            lambda lang: "en_US-lessac-medium",
        )

        backend = PiperTTSBackend()
        result = backend.synthesize(
            text="Hello world",
            voice="piper-auto",
            speed=175,
            lang_code="en",
        )

        assert isinstance(result, AudioSegment)
        assert len(result) > 0

    def test_synthesize_raises_on_missing_voice(self, monkeypatch):
        """Test that synthesis raises error when no voice available."""
        from modules.audio.backends.piper import PiperTTSBackend

        monkeypatch.setattr(
            piper_backend, "get_voice_for_language",
            lambda lang: None,
        )

        backend = PiperTTSBackend()

        with pytest.raises(TTSBackendError, match="No Piper voice available"):
            backend.synthesize(
                text="Hello",
                voice="auto",
                speed=175,
                lang_code="xyz",
            )

    def test_synthesize_with_explicit_voice_name(self, tmp_path, monkeypatch):
        """Test synthesis with explicit Piper voice model name."""
        from modules.audio.backends.piper import PiperTTSBackend

        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050

        mock_chunk = MagicMock()
        mock_chunk.audio_int16_bytes = b"\x00" * 44100

        def mock_synthesize(text, syn_config=None):
            yield mock_chunk

        mock_voice.synthesize = mock_synthesize

        monkeypatch.setattr(
            piper_backend, "_get_voice_model",
            lambda name: mock_voice,
        )

        backend = PiperTTSBackend()
        result = backend.synthesize(
            text="Hello",
            voice="en_US-lessac-medium",  # Explicit voice name
            speed=175,
            lang_code="en",
        )

        assert isinstance(result, AudioSegment)

    def test_synthesize_with_output_path(self, tmp_path, monkeypatch):
        """Test synthesis exports to output path when specified."""
        from modules.audio.backends.piper import PiperTTSBackend

        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050

        mock_chunk = MagicMock()
        mock_chunk.audio_int16_bytes = b"\x00" * 44100

        def mock_synthesize(text, syn_config=None):
            yield mock_chunk

        mock_voice.synthesize = mock_synthesize

        monkeypatch.setattr(
            piper_backend, "_get_voice_model",
            lambda name: mock_voice,
        )
        monkeypatch.setattr(
            piper_backend, "get_voice_for_language",
            lambda lang: "en_US-lessac-medium",
        )

        backend = PiperTTSBackend()
        output_file = tmp_path / "output.wav"

        result = backend.synthesize(
            text="Hello",
            voice="auto",
            speed=175,
            lang_code="en",
            output_path=str(output_file),
        )

        assert output_file.exists()
        assert isinstance(result, AudioSegment)


class TestPiperVoiceCache:
    """Tests for voice model caching."""

    def test_clear_voice_cache(self, monkeypatch):
        """Test clearing voice cache."""
        from modules.audio.backends.piper import _voice_cache, clear_voice_cache

        # Simulate cached voice
        _voice_cache["test_voice"] = MagicMock()
        assert len(_voice_cache) > 0

        clear_voice_cache()
        assert len(_voice_cache) == 0


class TestPiperVoiceResolution:
    """Tests for voice identifier resolution."""

    def test_resolve_explicit_piper_voice_name(self, monkeypatch):
        """Test that explicit Piper model names are used directly."""
        from modules.audio.backends.piper import PiperTTSBackend

        backend = PiperTTSBackend()

        # Voice name with proper format should be used directly
        resolved = backend._resolve_voice("en_US-lessac-medium", "en")
        assert resolved == "en_US-lessac-medium"

    def test_resolve_auto_voice(self, monkeypatch):
        """Test auto voice selection falls back to language lookup."""
        from modules.audio.backends import piper as piper_module
        from modules.audio.backends.piper import PiperTTSBackend

        monkeypatch.setattr(
            piper_module, "get_voice_for_language", lambda lang: "de_DE-thorsten-medium"
        )

        backend = PiperTTSBackend()
        resolved = backend._resolve_voice("auto", "de")
        assert resolved == "de_DE-thorsten-medium"

    def test_resolve_piper_auto_voice(self, monkeypatch):
        """Test 'piper-auto' triggers language-based selection."""
        from modules.audio.backends import piper as piper_module
        from modules.audio.backends.piper import PiperTTSBackend

        monkeypatch.setattr(
            piper_module, "get_voice_for_language", lambda lang: "fr_FR-siwis-medium"
        )

        backend = PiperTTSBackend()
        resolved = backend._resolve_voice("piper-auto", "fr")
        assert resolved == "fr_FR-siwis-medium"


class TestPiperListVoices:
    """Tests for listing available voices."""

    def test_list_available_voices_empty(self, tmp_path, monkeypatch):
        """Test listing voices when no models installed."""
        from modules.audio.backends.piper import PiperTTSBackend

        monkeypatch.setattr(
            piper_backend, "get_piper_models_path", lambda: tmp_path
        )

        backend = PiperTTSBackend()
        voices = backend.list_available_voices()
        assert voices == []

    def test_list_available_voices_with_models(self, tmp_path, monkeypatch):
        """Test listing voices when models are installed."""
        from modules.audio.backends.piper import PiperTTSBackend

        # Create fake model files
        (tmp_path / "en_US-lessac-medium.onnx").touch()
        (tmp_path / "en_US-lessac-medium.onnx.json").touch()
        (tmp_path / "de_DE-thorsten-high.onnx").touch()
        (tmp_path / "de_DE-thorsten-high.onnx.json").touch()

        monkeypatch.setattr(
            piper_backend, "get_piper_models_path", lambda: tmp_path
        )

        backend = PiperTTSBackend()
        voices = backend.list_available_voices()

        assert len(voices) == 2
        voice_names = [v[0] for v in voices]
        assert "en_US-lessac-medium" in voice_names
        assert "de_DE-thorsten-high" in voice_names


class TestPiperModelLoading:
    """Tests for voice model loading."""

    def test_get_voice_model_missing_file(self, tmp_path, monkeypatch):
        """Test loading model raises error when file missing."""
        from modules.audio.backends.piper import _get_voice_model, _voice_cache
        # Clear cache
        _voice_cache.clear()

        monkeypatch.setattr(
            piper_backend, "get_piper_models_path", lambda: tmp_path
        )

        # Mock the piper module to avoid import error
        mock_piper = MagicMock()
        monkeypatch.setattr(
            piper_backend, "_get_piper_voice_module",
            lambda: mock_piper,
        )

        with pytest.raises(TTSBackendError, match="voice model not found"):
            _get_voice_model("nonexistent-voice")
