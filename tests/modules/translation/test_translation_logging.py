"""Unit tests for translation_logging module."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from modules import translation_logging as tl

import pytest

pytestmark = pytest.mark.translation


class TestBatchStatsRecorder:
    def test_initialization(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
            total_batches=5,
            items_total=50,
        )

        assert recorder._batch_size == 10
        assert recorder._progress_tracker is tracker
        assert recorder._metadata_key == "test_stats"
        assert recorder._total_batches == 5
        assert recorder._items_total == 50
        assert recorder._batches_completed == 0
        assert recorder._items_completed == 0

    def test_set_total(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
        )

        recorder.set_total(8, items_total=80)

        assert recorder._total_batches == 8
        assert recorder._items_total == 80
        tracker.update_generated_files_metadata.assert_called_once()

    def test_set_total_with_none(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
        )

        recorder.set_total(None)

        # Should not update
        tracker.update_generated_files_metadata.assert_not_called()

    def test_add_total(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
            total_batches=5,
        )

        recorder.add_total(3)

        assert recorder._total_batches == 8
        tracker.update_generated_files_metadata.assert_called_once()

    def test_add_total_with_zero(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
            total_batches=5,
        )

        recorder.add_total(0)

        # Should not update
        assert recorder._total_batches == 5
        tracker.update_generated_files_metadata.assert_not_called()

    def test_record_batch(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
        )

        recorder.record(elapsed_seconds=1.5, item_count=10)

        assert recorder._batches_completed == 1
        assert recorder._items_completed == 10
        assert recorder._total_batch_seconds == 1.5
        assert recorder._last_batch_seconds == 1.5
        assert recorder._last_batch_items == 10
        tracker.update_generated_files_metadata.assert_called_once()

    def test_record_multiple_batches(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
        )

        recorder.record(elapsed_seconds=1.0, item_count=10)
        recorder.record(elapsed_seconds=2.0, item_count=8)
        recorder.record(elapsed_seconds=1.5, item_count=10)

        assert recorder._batches_completed == 3
        assert recorder._items_completed == 28
        assert recorder._total_batch_seconds == 4.5
        assert recorder._last_batch_seconds == 1.5
        assert recorder._last_batch_items == 10

    def test_record_with_zero_items(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
        )

        recorder.record(elapsed_seconds=1.0, item_count=0)

        # Should not record
        assert recorder._batches_completed == 0
        tracker.update_generated_files_metadata.assert_not_called()

    def test_build_payload(self):
        tracker = Mock()
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=tracker,
            metadata_key="test_stats",
            total_batches=5,
            items_total=50,
        )

        recorder.record(elapsed_seconds=2.0, item_count=10)
        recorder.record(elapsed_seconds=3.0, item_count=10)

        # Get the last published payload
        call_args = tracker.update_generated_files_metadata.call_args_list[-1]
        payload = call_args[0][0]["test_stats"]

        assert payload["batch_size"] == 10
        assert payload["batches_completed"] == 2
        assert payload["items_completed"] == 20
        assert payload["avg_batch_seconds"] == 2.5  # (2.0 + 3.0) / 2
        assert payload["avg_item_seconds"] == 0.25  # 5.0 / 20
        assert payload["last_batch_seconds"] == 3.0
        assert payload["last_batch_items"] == 10
        assert payload["batches_total"] == 5
        assert payload["items_total"] == 50
        assert "last_updated" in payload

    def test_publish_with_no_tracker(self):
        recorder = tl.BatchStatsRecorder(
            batch_size=10,
            progress_tracker=None,
            metadata_key="test_stats",
        )

        # Should not raise error
        recorder.record(elapsed_seconds=1.0, item_count=10)


class TestResolveLogDir:
    def test_resolve_with_media_output_dir(self):
        mock_context = Mock()
        mock_context.output_dir = "/path/to/output/media"

        with patch('modules.translation_logging.cfg.get_runtime_context', return_value=mock_context):
            result = tl.resolve_llm_batch_log_dir("translation")

            assert result == Path("/path/to/output/metadata/llm_batches/translation")

    def test_resolve_with_non_media_output_dir(self):
        mock_context = Mock()
        mock_context.output_dir = "/path/to/output"

        with patch('modules.translation_logging.cfg.get_runtime_context', return_value=mock_context):
            result = tl.resolve_llm_batch_log_dir("transliteration")

            assert result == Path("/path/to/output/metadata/llm_batches/transliteration")

    def test_resolve_with_no_context(self):
        with patch('modules.translation_logging.cfg.get_runtime_context', return_value=None):
            result = tl.resolve_llm_batch_log_dir()

            assert result is None

    def test_resolve_with_invalid_output_dir(self):
        mock_context = Mock()
        mock_context.output_dir = None  # Will raise when accessing Path()

        with patch('modules.translation_logging.cfg.get_runtime_context', return_value=mock_context):
            result = tl.resolve_llm_batch_log_dir()

            assert result is None


class TestSanitizeBatchComponent:
    def test_sanitize_simple_string(self):
        result = tl.sanitize_batch_component("english")
        assert result == "english"

    def test_sanitize_with_spaces(self):
        result = tl.sanitize_batch_component("Modern Greek")
        assert result == "modern_greek"

    def test_sanitize_with_special_chars(self):
        result = tl.sanitize_batch_component("zh-CN (Simplified)")
        assert result == "zh-cn_simplified"

    def test_sanitize_with_leading_trailing(self):
        result = tl.sanitize_batch_component("  spanish  ")
        assert result == "spanish"

    def test_sanitize_empty_string(self):
        result = tl.sanitize_batch_component("")
        assert result == "unknown"

    def test_sanitize_only_special_chars(self):
        result = tl.sanitize_batch_component("@#$%")
        assert result == "unknown"


class TestWriteBatchArtifact:
    def test_write_artifact_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            mock_client = Mock()
            mock_client.model = "test-model"
            mock_client.llm_source = "test-source"

            tl.write_llm_batch_artifact(
                operation="translation",
                log_dir=log_dir,
                request_items=[{"id": 1, "text": "hello"}, {"id": 2, "text": "world"}],
                input_language="en",
                target_language="es",
                include_transliteration=False,
                system_prompt="You are a translator",
                user_payload='{"texts": ["hello", "world"]}',
                request_payload={"model": "test"},
                response_payload={"translations": ["hola", "mundo"]},
                response_raw_text='{"translations": ["hola", "mundo"]}',
                response_error=None,
                elapsed_seconds=1.234,
                attempt=1,
                timeout_seconds=30.0,
                client=mock_client,
            )

            # Find the created file
            files = list(log_dir.glob("batch_*.json"))
            assert len(files) == 1

            # Read and verify content
            content = json.loads(files[0].read_text(encoding="utf-8"))
            assert content["operation"] == "translation"
            assert content["batch_size"] == 2
            assert content["input_language"] == "en"
            assert content["target_language"] == "es"
            assert content["include_transliteration"] is False
            assert content["model"] == "test-model"
            assert content["llm_source"] == "test-source"
            assert content["elapsed_seconds"] == 1.234
            assert content["attempt"] == 1
            assert len(content["request_items"]) == 2

    def test_write_artifact_filename_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            mock_client = Mock()
            mock_client.model = "test-model"
            mock_client.llm_source = "test-source"

            tl.write_llm_batch_artifact(
                operation="translation",
                log_dir=log_dir,
                request_items=[{"id": 10, "text": "a"}, {"id": 15, "text": "b"}],
                input_language="en",
                target_language="Japanese",
                include_transliteration=True,
                system_prompt="",
                user_payload="",
                request_payload={},
                response_payload=None,
                response_raw_text="",
                response_error="timeout",
                elapsed_seconds=30.0,
                attempt=2,
                timeout_seconds=30.0,
                client=mock_client,
            )

            files = list(log_dir.glob("batch_*.json"))
            assert len(files) == 1

            # Verify filename contains expected components
            filename = files[0].name
            assert "_0010-0015_" in filename  # ID range
            assert "_japanese_" in filename  # Sanitized language
            assert "_a2.json" in filename  # Attempt number

    def test_write_artifact_with_no_log_dir(self):
        mock_context = Mock()
        mock_context.output_dir = "/nonexistent/path"

        with patch('modules.translation_logging.cfg.get_runtime_context', return_value=mock_context):
            with patch('modules.translation_logging.logger') as mock_logger:
                mock_client = Mock()
                mock_client.model = "test-model"
                mock_client.llm_source = "test-source"

                # Should not raise, just log debug message
                tl.write_llm_batch_artifact(
                    operation="translation",
                    log_dir=None,  # Will use resolver
                    request_items=[{"id": 1}],
                    input_language="en",
                    target_language="es",
                    include_transliteration=False,
                    system_prompt="",
                    user_payload="",
                    request_payload={},
                    response_payload=None,
                    response_raw_text="",
                    response_error=None,
                    elapsed_seconds=1.0,
                    attempt=1,
                    timeout_seconds=30.0,
                    client=mock_client,
                )

    def test_write_artifact_no_batch_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            mock_client = Mock()
            mock_client.model = "test-model"
            mock_client.llm_source = "test-source"

            tl.write_llm_batch_artifact(
                operation="translation",
                log_dir=log_dir,
                request_items=[{"text": "no id"}],  # No "id" field
                input_language="en",
                target_language="es",
                include_transliteration=False,
                system_prompt="",
                user_payload="",
                request_payload={},
                response_payload=None,
                response_raw_text="",
                response_error=None,
                elapsed_seconds=1.0,
                attempt=1,
                timeout_seconds=30.0,
                client=mock_client,
            )

            files = list(log_dir.glob("batch_*.json"))
            assert len(files) == 1

            # Filename should use 0000-0000 for missing IDs
            assert "_0000-0000_" in files[0].name


class TestConstants:
    def test_constants_exported(self):
        assert tl.TRANSLATION_SUBDIR == "translation"
        assert tl.TRANSLITERATION_SUBDIR == "transliteration"
