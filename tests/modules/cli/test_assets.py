from modules.shared import assets

import pytest

pytestmark = pytest.mark.cli


def test_audio_mode_descriptions_expose_expected_modes():
    descriptions = assets.get_audio_mode_descriptions()
    assert descriptions["1"].startswith("Only the translated sentence")
    assert "4" in descriptions


def test_top_languages_matches_payload_copy():
    payload = assets.get_assets_payload()
    languages_from_fn = assets.get_top_languages()
    assert languages_from_fn == payload["top_languages"]
    languages_from_fn.append("Test Language")
    assert payload["top_languages"][-1] != "Test Language"
