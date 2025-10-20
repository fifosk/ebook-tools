from modules.cli import context


def test_update_sentence_config_with_lookup_updates_start():
    config = {"start_sentence_lookup": "hello", "start_sentence": 1}
    refined = ["hello world", "second sentence"]
    updated = context.update_sentence_config(config, refined)
    assert updated["start_sentence"] == 1
    assert updated["start_sentence_lookup"] == ""


def test_default_target_languages_returns_copy():
    defaults = context.default_target_languages()
    defaults.append("TestLang")
    again = context.default_target_languages()
    assert "TestLang" not in again
