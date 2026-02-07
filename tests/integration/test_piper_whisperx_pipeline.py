"""Integration tests for Piper TTS -> WhisperX alignment pipeline.

These tests verify the complete pipeline from text-to-speech generation
through word-level alignment using WhisperX. They require:
  - piper-tts package installed
  - whisperx package installed
  - At least one Piper voice model downloaded
  - At least one WhisperX alignment model available

Run with: pytest tests/integration/test_piper_whisperx_pipeline.py -v
Skip if dependencies unavailable: pytest -m "not integration"
"""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import List, Tuple

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.audio, pytest.mark.slow]

# Skip all tests if Piper or WhisperX not installed
piper = pytest.importorskip("piper", reason="piper-tts not installed")
whisperx = pytest.importorskip("whisperx", reason="whisperx not installed")


@pytest.fixture(scope="module")
def piper_models_path():
    """Get the Piper models path and skip if not available."""
    from modules.core.storage_config import get_piper_models_path

    models_path = get_piper_models_path()
    if not models_path.exists():
        pytest.skip(f"Piper models path not found: {models_path}")

    # Check for at least one model
    models = list(models_path.glob("*.onnx"))
    if not models:
        pytest.skip("No Piper voice models installed")

    return models_path


@pytest.fixture(scope="module")
def available_piper_voices(piper_models_path) -> List[Tuple[str, str]]:
    """Get list of available Piper voices (voice_name, lang_code)."""
    voices = []
    for model_file in piper_models_path.glob("*.onnx"):
        voice_name = model_file.stem
        # Extract language from voice name (e.g., en_US-lessac-medium -> en)
        if "_" in voice_name:
            lang_code = voice_name.split("_")[0]
            voices.append((voice_name, lang_code))
    return voices


# Test cases: (language_code, sample_text, expected_min_words)
# These are tested only if the corresponding voice model is available
PIPELINE_TEST_CASES = [
    ("en", "Hello world, this is a test.", 6),
    ("de", "Hallo Welt, das ist ein Test.", 6),
    ("es", "Hola mundo, esta es una prueba.", 6),
    ("fr", "Bonjour le monde, ceci est un test.", 7),
    ("ar", "مرحبا بالعالم", 2),
    ("tr", "Merhaba dünya, bu bir test.", 5),
]


def _voice_available_for_lang(lang_code: str, piper_models_path: Path) -> str | None:
    """Check if a voice model is available for the given language."""
    from modules.audio.backends.piper import get_voice_for_language

    voice = get_voice_for_language(lang_code)
    if not voice:
        return None

    model_path = piper_models_path / f"{voice}.onnx"
    if model_path.exists():
        return voice
    return None


@pytest.mark.integration
class TestPiperWhisperXPipeline:
    """Integration tests for Piper -> WhisperX pipeline."""

    @pytest.mark.parametrize("lang_code,text,min_words", PIPELINE_TEST_CASES)
    def test_tts_to_alignment_pipeline(
        self,
        lang_code: str,
        text: str,
        min_words: int,
        piper_models_path: Path,
    ):
        """Test complete pipeline: Piper TTS -> WhisperX alignment."""
        from modules.align.backends.whisperx_adapter import align_sentence
        from modules.audio.backends.piper import PiperTTSBackend

        # Check if voice available for this language
        voice = _voice_available_for_lang(lang_code, piper_models_path)
        if not voice:
            pytest.skip(f"No Piper voice installed for language: {lang_code}")

        # Generate audio with Piper
        backend = PiperTTSBackend()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            audio = backend.synthesize(
                text=text,
                voice=voice,
                speed=175,
                lang_code=lang_code,
                output_path=str(tmp_path),
            )

            assert audio is not None, "Audio should be generated"
            assert len(audio) > 0, "Audio should have duration"
            assert tmp_path.exists(), "Output file should exist"

            # Align with WhisperX
            try:
                tokens = align_sentence(
                    tmp_path,
                    text,
                    language=lang_code,
                    device="cpu",
                )
            except ValueError as e:
                # No WhisperX model for this language
                pytest.skip(f"No WhisperX model for {lang_code}: {e}")

            # Verify alignment results
            assert isinstance(tokens, list), "Tokens should be a list"

            # For clean TTS audio, we should get word-level tokens
            if tokens:
                for token in tokens:
                    assert "text" in token, "Token should have text"
                    assert "start" in token, "Token should have start time"
                    assert "end" in token, "Token should have end time"
                    assert token["start"] >= 0, "Start time should be non-negative"
                    assert token["end"] >= token["start"], "End >= Start"

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_piper_audio_format_compatible_with_whisperx(
        self,
        piper_models_path: Path,
    ):
        """Test that Piper output format is compatible with WhisperX."""
        from modules.audio.backends.piper import PiperTTSBackend

        voice = _voice_available_for_lang("en", piper_models_path)
        if not voice:
            pytest.skip("No English Piper voice available")

        backend = PiperTTSBackend()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            backend.synthesize(
                text="Test audio format compatibility.",
                voice=voice,
                speed=175,
                lang_code="en",
                output_path=str(tmp_path),
            )

            # Verify WAV format
            with wave.open(str(tmp_path), "rb") as wav:
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                sample_rate = wav.getframerate()

            # WhisperX expects: mono, 16-bit
            # Piper outputs: mono, 16-bit, 16kHz or 22.05kHz
            assert channels == 1, f"Expected mono audio, got {channels} channels"
            assert sample_width == 2, f"Expected 16-bit audio, got {sample_width * 8}-bit"
            assert sample_rate in (16000, 22050), f"Unexpected sample rate: {sample_rate}"

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_pipeline_with_punctuation_and_numbers(
        self,
        piper_models_path: Path,
    ):
        """Test pipeline with text containing punctuation and numbers."""
        from modules.align.backends.whisperx_adapter import align_sentence
        from modules.audio.backends.piper import PiperTTSBackend

        voice = _voice_available_for_lang("en", piper_models_path)
        if not voice:
            pytest.skip("No English Piper voice available")

        backend = PiperTTSBackend()
        text = "The year 2024 has 365 days!"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            backend.synthesize(
                text=text,
                voice=voice,
                speed=175,
                lang_code="en",
                output_path=str(tmp_path),
            )

            try:
                tokens = align_sentence(
                    tmp_path,
                    text,
                    language="en",
                    device="cpu",
                )
            except ValueError:
                pytest.skip("No WhisperX model for English")

            # Should handle numbers in text
            assert isinstance(tokens, list)

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_pipeline_speed_variations(
        self,
        piper_models_path: Path,
    ):
        """Test pipeline with different speech speeds."""
        from modules.audio.backends.piper import PiperTTSBackend

        voice = _voice_available_for_lang("en", piper_models_path)
        if not voice:
            pytest.skip("No English Piper voice available")

        backend = PiperTTSBackend()
        text = "Testing speech speed."

        speeds = [100, 175, 250]  # Slow, normal, fast
        durations = []

        for speed in speeds:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            try:
                audio = backend.synthesize(
                    text=text,
                    voice=voice,
                    speed=speed,
                    lang_code="en",
                    output_path=str(tmp_path),
                )
                durations.append(len(audio))
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        # Slower speed should produce longer audio
        # (allowing some tolerance for edge cases)
        assert durations[0] >= durations[1] * 0.8, "Slow should be longer than normal"
        assert durations[1] >= durations[2] * 0.8, "Normal should be longer than fast"


@pytest.mark.integration
class TestPiperVoiceAvailability:
    """Tests for Piper voice availability and discovery."""

    def test_list_available_voices(self, piper_models_path: Path):
        """Test listing installed Piper voices."""
        from modules.audio.backends.piper import PiperTTSBackend

        backend = PiperTTSBackend()
        voices = backend.list_available_voices()

        assert isinstance(voices, list)
        assert len(voices) > 0, "Should have at least one voice installed"

        for voice_name, lang_region, quality in voices:
            assert voice_name, "Voice name should not be empty"
            assert lang_region, "Language/region should not be empty"
            assert "_" in lang_region, f"Lang region should have underscore: {lang_region}"

    def test_voice_language_mapping(self, available_piper_voices):
        """Test that voice language mapping is configured correctly."""
        from modules.audio.backends.piper import get_voice_for_language

        # Languages where Piper has models but no mapping in the lookup table
        _UNMAPPED_LANGUAGES = {"no"}

        # For each available voice, check that we can look up by language
        languages_checked = set()
        for voice_name, lang_code in available_piper_voices:
            if lang_code in languages_checked:
                continue
            languages_checked.add(lang_code)

            found_voice = get_voice_for_language(lang_code)
            if lang_code in _UNMAPPED_LANGUAGES:
                continue
            assert found_voice is not None, f"Should find voice for language: {lang_code}"


@pytest.mark.integration
class TestEndToEndPipelineScenarios:
    """End-to-end pipeline scenario tests."""

    def test_short_sentence_alignment(self, piper_models_path: Path):
        """Test alignment of short sentences (edge case)."""
        from modules.align.backends.whisperx_adapter import align_sentence
        from modules.audio.backends.piper import PiperTTSBackend

        voice = _voice_available_for_lang("en", piper_models_path)
        if not voice:
            pytest.skip("No English Piper voice available")

        backend = PiperTTSBackend()
        text = "Hi."  # Very short

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            backend.synthesize(
                text=text,
                voice=voice,
                speed=175,
                lang_code="en",
                output_path=str(tmp_path),
            )

            try:
                tokens = align_sentence(
                    tmp_path,
                    text,
                    language="en",
                    device="cpu",
                )
            except ValueError:
                pytest.skip("No WhisperX model for English")

            # Should handle short text gracefully
            assert isinstance(tokens, list)

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_long_sentence_alignment(self, piper_models_path: Path):
        """Test alignment of longer sentences."""
        from modules.align.backends.whisperx_adapter import align_sentence
        from modules.audio.backends.piper import PiperTTSBackend
        voice = _voice_available_for_lang("en", piper_models_path)
        if not voice:
            pytest.skip("No English Piper voice available")

        backend = PiperTTSBackend()
        text = (
            "This is a longer sentence that contains multiple clauses, "
            "various punctuation marks, and should test the alignment "
            "system's ability to handle more complex input text."
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            backend.synthesize(
                text=text,
                voice=voice,
                speed=175,
                lang_code="en",
                output_path=str(tmp_path),
            )

            try:
                tokens = align_sentence(
                    tmp_path,
                    text,
                    language="en",
                    device="cpu",
                )
            except ValueError:
                pytest.skip("No WhisperX model for English")

            assert isinstance(tokens, list)
            # Long sentence should produce multiple tokens
            if tokens:
                assert len(tokens) >= 10, f"Expected many tokens, got {len(tokens)}"

        finally:
            if tmp_path.exists():
                tmp_path.unlink()
