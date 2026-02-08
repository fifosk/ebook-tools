"""Tests for the media analytics service."""

from __future__ import annotations

import pytest

from modules.services.analytics_service import MediaAnalyticsService, _GenerationEntry

pytestmark = pytest.mark.analytics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeJob:
    """Minimal duck-typed PipelineJob for testing."""

    def __init__(
        self,
        *,
        job_id: str = "test-job-1",
        job_type: str = "book",
        generated_files: dict | None = None,
        request_payload: dict | None = None,
        result_payload: dict | None = None,
    ) -> None:
        self.job_id = job_id
        self.job_type = job_type
        self.generated_files = generated_files or {}
        self.request_payload = request_payload or {}
        self.result_payload = result_payload or {}


def _make_chunk(
    *,
    orig_duration: float = 10.0,
    trans_duration: float = 12.0,
    sentence_count: int = 5,
) -> dict:
    chunk: dict = {"sentenceCount": sentence_count, "audioTracks": {}}
    if orig_duration > 0:
        chunk["audioTracks"]["orig"] = {"duration": orig_duration, "sampleRate": 24000}
    if trans_duration > 0:
        chunk["audioTracks"]["translation"] = {"duration": trans_duration, "sampleRate": 24000}
    return chunk


# ---------------------------------------------------------------------------
# _extract_audio_durations
# ---------------------------------------------------------------------------

class TestExtractAudioDurations:
    """Unit tests for duration extraction from generated_files."""

    def test_empty_chunks(self) -> None:
        result = MediaAnalyticsService._extract_audio_durations({}, "book", "en", ["ar"])
        assert result == []

    def test_single_chunk_both_tracks(self) -> None:
        chunks = [_make_chunk(orig_duration=30.5, trans_duration=40.2, sentence_count=10)]
        result = MediaAnalyticsService._extract_audio_durations(
            {"chunks": chunks}, "book", "en", ["ar"]
        )
        assert len(result) == 2

        orig = next(e for e in result if e.track_kind == "original")
        trans = next(e for e in result if e.track_kind == "translation")

        assert orig.language == "en"
        assert orig.duration_seconds == pytest.approx(30.5, abs=0.01)
        assert orig.sentence_count == 10
        assert orig.chunk_count == 1

        assert trans.language == "ar"
        assert trans.duration_seconds == pytest.approx(40.2, abs=0.01)

    def test_multiple_chunks_sum_durations(self) -> None:
        chunks = [
            _make_chunk(orig_duration=10.0, trans_duration=12.0, sentence_count=5),
            _make_chunk(orig_duration=20.0, trans_duration=25.0, sentence_count=8),
        ]
        result = MediaAnalyticsService._extract_audio_durations(
            {"chunks": chunks}, "book", "en", ["ar"]
        )
        orig = next(e for e in result if e.track_kind == "original")
        trans = next(e for e in result if e.track_kind == "translation")

        assert orig.duration_seconds == pytest.approx(30.0, abs=0.01)
        assert orig.sentence_count == 13
        assert orig.chunk_count == 2

        assert trans.duration_seconds == pytest.approx(37.0, abs=0.01)

    def test_original_key_alias(self) -> None:
        """Track key 'original' (not just 'orig') should map to track_kind='original'."""
        chunks = [{"sentenceCount": 3, "audioTracks": {
            "original": {"duration": 15.0},
            "translation": {"duration": 18.0},
        }}]
        result = MediaAnalyticsService._extract_audio_durations(
            {"chunks": chunks}, "book", "en", ["ar"]
        )
        assert any(e.track_kind == "original" for e in result)

    def test_unknown_language_fallback(self) -> None:
        """If input_language is None, 'unknown' should be used."""
        chunks = [_make_chunk()]
        result = MediaAnalyticsService._extract_audio_durations(
            {"chunks": chunks}, "book", None, []
        )
        for entry in result:
            assert entry.language == "unknown"

    def test_snake_case_keys(self) -> None:
        """audio_tracks (snake_case) should be handled alongside audioTracks."""
        chunks = [{"sentence_count": 4, "audio_tracks": {
            "orig": {"duration": 5.0},
        }}]
        result = MediaAnalyticsService._extract_audio_durations(
            {"chunks": chunks}, "book", "en", []
        )
        assert len(result) == 1
        assert result[0].duration_seconds == pytest.approx(5.0)

    def test_zero_duration_skipped(self) -> None:
        chunks = [{"sentenceCount": 2, "audioTracks": {
            "orig": {"duration": 0},
            "translation": {"duration": 0},
        }}]
        result = MediaAnalyticsService._extract_audio_durations(
            {"chunks": chunks}, "book", "en", ["ar"]
        )
        assert result == []


# ---------------------------------------------------------------------------
# _resolve_languages
# ---------------------------------------------------------------------------

class TestResolveLanguages:
    """Unit tests for language resolution across job types."""

    def test_pipeline_job(self) -> None:
        job = _FakeJob(
            job_type="book",
            request_payload={"inputs": {"input_language": "en", "target_languages": ["ar", "hu"]}},
        )
        input_lang, targets = MediaAnalyticsService._resolve_languages(job)
        assert input_lang == "en"
        assert targets == ["ar", "hu"]

    def test_youtube_dub_job(self) -> None:
        job = _FakeJob(
            job_type="youtube_dub",
            result_payload={"youtube_dub": {"source_language": "en", "language": "ar"}},
        )
        input_lang, targets = MediaAnalyticsService._resolve_languages(job)
        assert input_lang == "en"
        assert targets == ["ar"]

    def test_subtitle_job(self) -> None:
        job = _FakeJob(
            job_type="subtitle",
            request_payload={"options": {"source_language": "en", "target_language": "de"}},
        )
        input_lang, targets = MediaAnalyticsService._resolve_languages(job)
        assert input_lang == "en"
        assert targets == ["de"]

    def test_missing_languages(self) -> None:
        job = _FakeJob(job_type="book", request_payload={})
        input_lang, targets = MediaAnalyticsService._resolve_languages(job)
        assert input_lang is None
        assert targets == []


# ---------------------------------------------------------------------------
# record_generation_stats (integration-light, no real DB)
# ---------------------------------------------------------------------------

class TestRecordGenerationStats:
    """Tests that record_generation_stats handles edge cases gracefully."""

    def test_no_generated_files_is_noop(self) -> None:
        """Should not raise when generated_files is empty."""
        service = MediaAnalyticsService()
        job = _FakeJob(generated_files={})
        # Calling without a DB will hit the try/except path
        service.record_generation_stats(job)

    def test_no_chunks_is_noop(self) -> None:
        service = MediaAnalyticsService()
        job = _FakeJob(generated_files={"chunks": []})
        service.record_generation_stats(job)

    def test_none_generated_files_is_noop(self) -> None:
        service = MediaAnalyticsService()
        job = _FakeJob(generated_files=None)
        service.record_generation_stats(job)
