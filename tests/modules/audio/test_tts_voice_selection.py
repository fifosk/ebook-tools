from modules.audio import tts


def _stub_inventory():
    return [
        ("Samantha", "en_US", "Premium", "female"),
        ("Tom", "en_US", "Enhanced", "male"),
        ("Daniel", "en_GB", "Premium", "male"),
        ("Kyoko", "ja_JP", "Premium", "female"),
        ("Carla", "es_MX", "Enhanced", "female"),
    ]


def test_select_voice_prefers_premium_female(monkeypatch):
    monkeypatch.setattr(tts, "macos_voice_inventory", lambda debug_enabled=False: _stub_inventory())

    result = tts.select_voice("ja", "female")

    assert result.startswith("Kyoko - ja_JP - (Premium)")
    assert result.endswith("Female")


def test_select_voice_prioritises_premium_quality_for_male(monkeypatch):
    monkeypatch.setattr(tts, "macos_voice_inventory", lambda debug_enabled=False: _stub_inventory())

    result = tts.select_voice("en", "male")

    assert result.startswith("Daniel - en_GB - (Premium)")
    assert result.endswith("Male")


def test_select_voice_fallbacks_to_gtts_when_no_macos(monkeypatch):
    monkeypatch.setattr(tts, "macos_voice_inventory", lambda debug_enabled=False: [])

    result = tts.select_voice("es", "female")

    assert result == "gTTS-es"


def test_select_voice_uses_locale_overrides(monkeypatch):
    monkeypatch.setattr(tts, "macos_voice_inventory", lambda debug_enabled=False: _stub_inventory())

    result = tts.select_voice("es", "female")

    assert result.startswith("Carla - es_MX - (Enhanced)")
