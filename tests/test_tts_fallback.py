from modules.audio import tts

import pytest

pytestmark = pytest.mark.audio


def test_romani_voice_falls_back_to_slovak():
    voice = tts.select_voice("Romani", "gTTS")

    assert "sk" in voice.lower()


def test_celtic_languages_fall_back_to_english():
    for language in ["Irish", "Scottish Gaelic", "Scots"]:
        voice = tts.select_voice(language, "gTTS")
        assert "en" in voice.lower()


def test_gtts_language_normalization_prefers_supported_base_locale():
    assert tts.normalize_gtts_language_code("ar-SA") == "ar"
    assert tts.normalize_gtts_language_code("pt-BR") == "pt"


def test_gtts_language_normalization_preserves_supported_variants():
    assert tts.normalize_gtts_language_code("zh-CN") == "zh-cn"
    assert tts.normalize_gtts_language_code("pt-PT") == "pt-pt"
