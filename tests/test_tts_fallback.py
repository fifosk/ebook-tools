from modules.audio import tts


def test_romani_voice_falls_back_to_slovak():
    voice = tts.select_voice("Romani", "gTTS")

    assert "sk" in voice.lower()


def test_celtic_languages_fall_back_to_english():
    for language in ["Irish", "Scottish Gaelic", "Scots"]:
        voice = tts.select_voice(language, "gTTS")
        assert "en" in voice.lower()
