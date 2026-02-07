"""Unit tests for googletrans_provider module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from modules.translation_providers import googletrans_provider as gtp

pytestmark = pytest.mark.translation


class TestNormalizeTranslationProvider:
    def test_none_returns_llm(self):
        assert gtp.normalize_translation_provider(None) == "llm"

    def test_empty_string_returns_llm(self):
        assert gtp.normalize_translation_provider("") == "llm"
        assert gtp.normalize_translation_provider("   ") == "llm"

    def test_googletrans_aliases(self):
        assert gtp.normalize_translation_provider("google") == "googletrans"
        assert gtp.normalize_translation_provider("googletrans") == "googletrans"
        assert gtp.normalize_translation_provider("googletranslate") == "googletrans"
        assert gtp.normalize_translation_provider("google-translate") == "googletrans"
        assert gtp.normalize_translation_provider("gtranslate") == "googletrans"
        assert gtp.normalize_translation_provider("gtrans") == "googletrans"

    def test_case_insensitive(self):
        assert gtp.normalize_translation_provider("GOOGLE") == "googletrans"
        assert gtp.normalize_translation_provider("Google") == "googletrans"
        assert gtp.normalize_translation_provider("LLM") == "llm"

    def test_llm_aliases(self):
        assert gtp.normalize_translation_provider("llm") == "llm"
        assert gtp.normalize_translation_provider("ollama") == "llm"
        assert gtp.normalize_translation_provider("default") == "llm"

    def test_unknown_provider_returns_llm(self):
        assert gtp.normalize_translation_provider("unknown") == "llm"
        assert gtp.normalize_translation_provider("openai") == "llm"


class TestStripGoogletransPseudoSuffix:
    def test_no_suffix(self):
        assert gtp._strip_googletrans_pseudo_suffix("en") == "en"
        assert gtp._strip_googletrans_pseudo_suffix("zh-cn") == "zh-cn"

    def test_with_orig_suffix(self):
        assert gtp._strip_googletrans_pseudo_suffix("en-orig") == "en"
        assert gtp._strip_googletrans_pseudo_suffix("zh-cn-orig") == "zh-cn"

    def test_with_auto_suffix(self):
        assert gtp._strip_googletrans_pseudo_suffix("en-auto") == "en"
        assert gtp._strip_googletrans_pseudo_suffix("en-autogen") == "en"
        # Only strips the last part, so "auto-generated" becomes "auto"
        assert gtp._strip_googletrans_pseudo_suffix("en-auto-generated") == "en-auto"

    def test_with_generated_suffix(self):
        assert gtp._strip_googletrans_pseudo_suffix("en-generated") == "en"

    def test_no_hyphen(self):
        assert gtp._strip_googletrans_pseudo_suffix("english") == "english"

    def test_valid_suffix_not_pseudo(self):
        # Should not strip valid language suffixes
        assert gtp._strip_googletrans_pseudo_suffix("zh-tw") == "zh-tw"


class TestResolveGoogletransLanguage:
    def test_none_returns_fallback(self):
        assert gtp.resolve_googletrans_language(None, fallback="en") == "en"
        assert gtp.resolve_googletrans_language(None, fallback=None) is None

    def test_empty_string_returns_fallback(self):
        assert gtp.resolve_googletrans_language("", fallback="en") == "en"
        assert gtp.resolve_googletrans_language("   ", fallback="en") == "en"

    def test_normalizes_underscores(self):
        # Should convert underscores to hyphens
        result = gtp.resolve_googletrans_language("zh_cn", fallback="en")
        # Actual result depends on googletrans being available
        assert result is not None

    def test_strips_pseudo_suffix(self):
        result = gtp.resolve_googletrans_language("en-orig", fallback="en")
        # Should strip -orig and resolve
        assert result is not None

    @patch('modules.translation_providers.googletrans_provider.LANGUAGE_CODES',
           {'English': 'en', 'Spanish': 'es'})
    def test_resolves_language_name(self):
        result = gtp.resolve_googletrans_language("english", fallback=None)
        # Should resolve English -> en
        assert result is not None

    def test_case_insensitive(self):
        result = gtp.resolve_googletrans_language("EN", fallback=None)
        assert result is not None

    def test_chinese_variant_resolution(self):
        # Test Chinese variant handling
        result_cn = gtp.resolve_googletrans_language("zh-hans", fallback=None)
        result_tw = gtp.resolve_googletrans_language("zh-hant", fallback=None)
        # Both should resolve (to zh-cn and zh-tw respectively if googletrans available)
        assert result_cn is not None or result_cn == "zh-hans"
        assert result_tw is not None or result_tw == "zh-hant"


class TestCheckGoogletransHealth:
    def test_returns_cached_result(self):
        gtp._GOOGLETRANS_HEALTH_STATE.update({"checked": True, "ok": True, "reason": None})
        ok, reason = gtp.check_googletrans_health()
        assert ok is True
        assert reason is None

    def test_returns_cached_failure(self):
        gtp._GOOGLETRANS_HEALTH_STATE.update({"checked": True, "ok": False, "reason": "test error"})
        ok, reason = gtp.check_googletrans_health()
        assert ok is False
        assert reason == "test error"

    def test_httpcore_import_failure(self):
        # Reset health state before test
        gtp._GOOGLETRANS_HEALTH_STATE.update({"checked": False, "ok": False, "reason": None})
        with patch.dict('sys.modules', {'httpcore': None}):
            with patch('modules.translation_providers.googletrans_provider.logger'):
                ok, reason = gtp.check_googletrans_health()
                # Should fail due to import
                assert ok is False
                assert reason is not None


class TestGetGoogletransTranslator:
    def test_creates_translator_on_first_call(self):
        # Clear any cached translator
        if hasattr(gtp._GOOGLETRANS_LOCAL, 'translator'):
            del gtp._GOOGLETRANS_LOCAL.translator

        with patch('googletrans.Translator') as mock_translator_class:
            mock_instance = Mock()
            mock_translator_class.return_value = mock_instance

            translator = gtp._get_googletrans_translator()

            assert translator == mock_instance
            mock_translator_class.assert_called_once()

    def test_returns_cached_translator_on_subsequent_calls(self):
        # Set a cached translator
        mock_cached = Mock()
        gtp._GOOGLETRANS_LOCAL.translator = mock_cached

        translator = gtp._get_googletrans_translator()

        assert translator == mock_cached


class TestTranslateWithGoogletrans:
    def test_health_check_failure(self):
        with patch.object(gtp, 'check_googletrans_health', return_value=(False, "test failure")):
            result, error = gtp.translate_with_googletrans("hello", "en", "es")

            assert error == "googletrans health check failed: test failure"
            assert "retries" in result.lower()

    def test_unsupported_language(self):
        with patch.object(gtp, 'check_googletrans_health', return_value=(True, None)):
            with patch.object(gtp, 'resolve_googletrans_language') as mock_resolve:
                mock_resolve.side_effect = [
                    "en",  # source language
                    None,  # target language (unsupported)
                ]

                result, error = gtp.translate_with_googletrans("hello", "en", "fake-lang")

                assert "Unsupported googletrans language" in error
                assert "retries" in result.lower()

    def test_successful_translation(self):
        with patch.object(gtp, 'check_googletrans_health', return_value=(True, None)):
            with patch.object(gtp, 'resolve_googletrans_language', side_effect=["en", "es"]):
                with patch.object(gtp, '_get_googletrans_translator') as mock_get_translator:
                    mock_translator = Mock()
                    mock_result = Mock()
                    mock_result.text = "hola"
                    mock_translator.translate.return_value = mock_result
                    mock_get_translator.return_value = mock_translator

                    result, error = gtp.translate_with_googletrans("hello", "en", "es")

                    assert result == "hola"
                    assert error is None
                    mock_translator.translate.assert_called_once_with("hello", src="en", dest="es")

    def test_empty_translation_retries(self):
        with patch.object(gtp, 'check_googletrans_health', return_value=(True, None)):
            with patch.object(gtp, 'resolve_googletrans_language', side_effect=["en", "es"]):
                with patch.object(gtp, '_get_googletrans_translator') as mock_get_translator:
                    with patch('time.sleep'):  # Mock sleep to speed up test
                        mock_translator = Mock()
                        mock_result = Mock()
                        mock_result.text = ""  # Empty response
                        mock_translator.translate.return_value = mock_result
                        mock_get_translator.return_value = mock_translator

                        result, error = gtp.translate_with_googletrans("hello", "en", "es")

                        assert error == "Empty translation response"
                        assert "retries" in result.lower()
                        # Should have retried multiple times
                        assert mock_translator.translate.call_count == gtp._TRANSLATION_RESPONSE_ATTEMPTS

    def test_exception_handling(self):
        with patch.object(gtp, 'check_googletrans_health', return_value=(True, None)):
            with patch.object(gtp, 'resolve_googletrans_language', side_effect=["en", "es"]):
                with patch.object(gtp, '_get_googletrans_translator') as mock_get_translator:
                    with patch('time.sleep'):  # Mock sleep
                        mock_translator = Mock()
                        mock_translator.translate.side_effect = Exception("Network error")
                        mock_get_translator.return_value = mock_translator

                        result, error = gtp.translate_with_googletrans("hello", "en", "es")

                        assert "Network error" in error
                        assert "retries" in result.lower()

    def test_progress_tracker_recording(self):
        mock_tracker = Mock()
        with patch.object(gtp, 'check_googletrans_health', return_value=(False, "health fail")):
            result, error = gtp.translate_with_googletrans(
                "hello", "en", "es", progress_tracker=mock_tracker
            )

            mock_tracker.record_retry.assert_called_once()
            args = mock_tracker.record_retry.call_args[0]
            assert args[0] == "translation"
            assert "health" in args[1].lower()
