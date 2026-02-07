"""Tests for WhisperX forced alignment adapter.

These tests verify that WhisperX alignment models load and function correctly
for all supported languages.
"""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
import wave
import struct

pytestmark = [pytest.mark.audio, pytest.mark.slow]

# Skip all tests if WhisperX is not installed
whisperx = pytest.importorskip("whisperx")


@pytest.fixture(scope="module")
def sample_audio_path(tmp_path_factory) -> Path:
    """Create a simple silent audio file for testing."""
    audio_dir = tmp_path_factory.mktemp("audio")
    audio_path = audio_dir / "test_audio.wav"

    # Create a 1-second silent WAV file at 16kHz
    sample_rate = 16000
    duration = 1.0
    num_samples = int(sample_rate * duration)

    with wave.open(str(audio_path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        # Write silence (zeros)
        for _ in range(num_samples):
            wav_file.writeframes(struct.pack("<h", 0))

    return audio_path


# Languages with downloaded WhisperX alignment models
# Only test these to avoid downloading new models during tests
DOWNLOADED_LANGUAGES = [
    ("en", "English"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("hu", "Hungarian"),
    ("el", "Greek"),
    ("fi", "Finnish"),
    ("tr", "Turkish"),
]


class TestWhisperXModelLoading:
    """Tests for WhisperX alignment model loading."""

    @pytest.mark.parametrize("language_code,language_name", DOWNLOADED_LANGUAGES)
    def test_model_loads_on_cpu(self, language_code, language_name):
        """Test that alignment model loads successfully on CPU."""
        from modules.align.backends.whisperx_adapter import (
            _get_alignment_model,
            clear_model_cache,
        )

        # Clear cache to force fresh load
        clear_model_cache()

        try:
            model, metadata = _get_alignment_model(language_code, "cpu")
            assert model is not None, f"{language_name} model should not be None"
            assert metadata is not None, f"{language_name} metadata should not be None"
        except ValueError as e:
            # No model available for this language - skip
            pytest.skip(f"No alignment model available for {language_name}: {e}")
        except Exception as e:
            pytest.fail(f"Failed to load {language_name} model: {e}")


# Sample texts for downloaded languages
DOWNLOADED_LANGUAGE_SAMPLES = [
    ("en", "Hello world"),
    ("ar", "مرحبا بالعالم"),
    ("hi", "नमस्ते दुनिया"),
    ("hu", "Helló világ"),
    ("el", "Γειά σου κόσμε"),
    ("fi", "Hei maailma"),
    ("tr", "Merhaba dünya"),
]


class TestWhisperXAlignment:
    """Tests for WhisperX alignment functionality."""

    @pytest.mark.parametrize("language_code,sample_text", DOWNLOADED_LANGUAGE_SAMPLES)
    def test_alignment_returns_tokens_or_empty(
        self, language_code, sample_text, sample_audio_path
    ):
        """Test that alignment either returns tokens or empty list (not exception)."""
        from modules.align.backends.whisperx_adapter import align_sentence

        try:
            tokens = align_sentence(
                sample_audio_path,
                sample_text,
                language=language_code,
                device="cpu",
            )
            # Should return a list (possibly empty for silent audio)
            assert isinstance(tokens, list), f"Expected list, got {type(tokens)}"
        except ValueError:
            # No model for this language - acceptable
            pytest.skip(f"No alignment model for {language_code}")


class TestWhisperXDeviceFallback:
    """Tests for device fallback behavior."""

    def test_meta_tensor_fallback_to_cpu(self):
        """Test that meta tensor errors fall back to CPU."""
        from modules.align.backends.whisperx_adapter import (
            _get_alignment_model,
            clear_model_cache,
        )

        # Clear cache
        clear_model_cache()

        # Try loading on MPS/CUDA - should fall back to CPU if meta tensor error
        try:
            import torch

            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                pytest.skip("No GPU device available to test fallback")

            # Try to load - should either succeed or fall back to CPU
            model, metadata = _get_alignment_model("en", device)
            assert model is not None
        except ValueError:
            pytest.skip("No alignment model for English")
        except Exception as e:
            if "meta tensor" in str(e):
                pytest.fail("Meta tensor error should have triggered CPU fallback")
            # Other exceptions are acceptable (GPU not properly configured, etc.)
            pytest.skip(f"GPU test skipped: {e}")


class TestWhisperXCaching:
    """Tests for model caching behavior."""

    def test_model_cache_reuse(self):
        """Test that cached models are reused."""
        from modules.align.backends.whisperx_adapter import (
            _get_alignment_model,
            _model_cache,
            clear_model_cache,
        )

        clear_model_cache()
        assert len(_model_cache) == 0

        try:
            # First load
            model1, _ = _get_alignment_model("en", "cpu")
            cache_size_after_first = len(_model_cache)
            assert cache_size_after_first == 1

            # Second load should use cache
            model2, _ = _get_alignment_model("en", "cpu")
            cache_size_after_second = len(_model_cache)
            assert cache_size_after_second == 1  # Still just one entry

            # Models should be the same object (from cache)
            assert model1 is model2
        except ValueError:
            pytest.skip("No alignment model for English")

    def test_clear_model_cache(self):
        """Test that cache clearing works."""
        from modules.align.backends.whisperx_adapter import (
            _get_alignment_model,
            _model_cache,
            clear_model_cache,
        )

        try:
            # Load a model
            _get_alignment_model("en", "cpu")
            assert len(_model_cache) > 0

            # Clear cache
            clear_model_cache()
            assert len(_model_cache) == 0
        except ValueError:
            pytest.skip("No alignment model for English")


class TestWhisperXRetry:
    """Tests for retry alignment functionality."""

    def test_retry_returns_tuple(self, sample_audio_path):
        """Test that retry_alignment returns correct tuple format."""
        from modules.align.backends.whisperx_adapter import retry_alignment

        try:
            tokens, exhausted = retry_alignment(
                sample_audio_path,
                "Hello world",
                language="en",
                device="cpu",
                max_attempts=1,
            )
            assert isinstance(tokens, list)
            assert isinstance(exhausted, bool)
        except ValueError:
            pytest.skip("No alignment model for English")

    def test_retry_exhausted_flag(self, sample_audio_path):
        """Test that exhausted flag is set correctly on failure."""
        from modules.align.backends.whisperx_adapter import retry_alignment

        # Use nonexistent file to force failure
        fake_path = Path("/nonexistent/audio.wav")
        tokens, exhausted = retry_alignment(
            fake_path,
            "Hello world",
            language="en",
            device="cpu",
            max_attempts=2,
        )
        assert tokens == []
        assert exhausted is True


class TestWhisperXLanguageDetection:
    """Tests for language detection heuristics."""

    def test_detect_arabic(self):
        """Test Arabic script detection."""
        from modules.align.backends.whisperx_adapter import _detect_language

        assert _detect_language("مرحبا بالعالم") == "ar"

    def test_detect_chinese(self):
        """Test Chinese script detection."""
        from modules.align.backends.whisperx_adapter import _detect_language

        assert _detect_language("你好世界") == "zh"

    def test_detect_japanese(self):
        """Test Japanese script detection."""
        from modules.align.backends.whisperx_adapter import _detect_language

        assert _detect_language("こんにちは世界") == "ja"

    def test_detect_hebrew(self):
        """Test Hebrew script detection."""
        from modules.align.backends.whisperx_adapter import _detect_language

        assert _detect_language("שלום עולם") == "he"

    def test_detect_russian(self):
        """Test Cyrillic script detection."""
        from modules.align.backends.whisperx_adapter import _detect_language

        assert _detect_language("Привет мир") == "ru"

    def test_detect_english_default(self):
        """Test that Latin scripts default to English."""
        from modules.align.backends.whisperx_adapter import _detect_language

        assert _detect_language("Hello world") == "en"
        assert _detect_language("Bonjour monde") == "en"  # French uses Latin


class TestWhisperXConcurrency:
    """Tests for thread-safe concurrent model loading."""

    def test_concurrent_model_loading(self, sample_audio_path):
        """Test that concurrent model loading doesn't cause meta tensor errors."""
        import threading
        import time
        from modules.align.backends.whisperx_adapter import (
            align_sentence,
            clear_model_cache,
        )

        clear_model_cache()

        errors = []
        results = []
        lock = threading.Lock()

        def align_task(thread_id, language, text):
            try:
                tokens = align_sentence(
                    sample_audio_path,
                    text,
                    language=language,
                    device="cpu",
                )
                with lock:
                    results.append((thread_id, language, len(tokens)))
            except Exception as e:
                with lock:
                    errors.append((thread_id, language, str(e)))

        # Create threads that will all try to load models concurrently
        threads = []
        test_cases = [
            ("en", "Hello world"),
            ("en", "Testing alignment"),
            ("ar", "مرحبا"),
            ("ar", "اختبار"),
            ("he", "שלום"),
            ("he", "בדיקה"),
        ]

        for i, (lang, text) in enumerate(test_cases):
            t = threading.Thread(target=align_task, args=(i, lang, text))
            threads.append(t)

        # Start all threads at approximately the same time
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=60)

        # Check results
        assert len(errors) == 0, f"Concurrent loading errors: {errors}"
        assert len(results) == len(test_cases), f"Expected {len(test_cases)} results, got {len(results)}"

    def test_concurrent_same_language(self, sample_audio_path):
        """Test that multiple threads loading the same language don't conflict."""
        import threading
        from modules.align.backends.whisperx_adapter import (
            align_sentence,
            clear_model_cache,
            _model_cache,
        )

        clear_model_cache()

        errors = []
        results = []
        lock = threading.Lock()

        def align_task(thread_id):
            try:
                tokens = align_sentence(
                    sample_audio_path,
                    f"Test sentence number {thread_id}",
                    language="en",
                    device="cpu",
                )
                with lock:
                    results.append((thread_id, len(tokens)))
            except Exception as e:
                with lock:
                    errors.append((thread_id, str(e)))

        # Create 4 threads all loading English
        threads = [threading.Thread(target=align_task, args=(i,)) for i in range(4)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=60)

        # All should succeed
        assert len(errors) == 0, f"Concurrent same-language errors: {errors}"
        assert len(results) == 4

        # Model should only be loaded once (cached)
        en_cache_entries = [k for k in _model_cache.keys() if k.startswith("en:")]
        assert len(en_cache_entries) == 1, f"Expected 1 cached English model, got {len(en_cache_entries)}"


class TestWhisperXModelValidation:
    """Tests for model name validation."""

    def test_rejects_whisper_model_names(self):
        """Test that Whisper model names are rejected as alignment models."""
        from modules.align.backends.whisperx_adapter import _is_valid_alignment_model

        # Whisper model names should be rejected
        assert not _is_valid_alignment_model("tiny")
        assert not _is_valid_alignment_model("base")
        assert not _is_valid_alignment_model("small")
        assert not _is_valid_alignment_model("medium")
        assert not _is_valid_alignment_model("large")
        assert not _is_valid_alignment_model("large-v2")
        assert not _is_valid_alignment_model("large-v3")
        assert not _is_valid_alignment_model("tiny.en")

    def test_accepts_wav2vec_model_names(self):
        """Test that Wav2Vec2 model names are accepted."""
        from modules.align.backends.whisperx_adapter import _is_valid_alignment_model

        # Wav2Vec2 model names should be accepted
        assert _is_valid_alignment_model("WAV2VEC2_ASR_BASE_960H")
        assert _is_valid_alignment_model("jonatasgrosman/wav2vec2-large-xlsr-53-english")
        assert _is_valid_alignment_model("facebook/hubert-large-ls960-ft")

    def test_accepts_huggingface_paths(self):
        """Test that HuggingFace model paths are accepted."""
        from modules.align.backends.whisperx_adapter import _is_valid_alignment_model
        assert _is_valid_alignment_model("facebook/wav2vec2-base")
        assert _is_valid_alignment_model("jonatasgrosman/wav2vec2-large-xlsr-53-arabic")
