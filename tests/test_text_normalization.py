from modules.epub_parser import remove_quotes
from modules import text_normalization as text_norm

import pytest

pytestmark = pytest.mark.pipeline


def test_remove_quotes_preserves_apostrophes():
    text = "Il s’agit d’un test “simple”."

    normalized = remove_quotes(text)

    assert normalized == "Il s'agit d'un test \"simple\"."


def test_collapse_whitespace_removes_newlines():
    text = "Bonjour\nle\tmonde  !"

    assert text_norm.collapse_whitespace(text) == "Bonjour le monde !"


@pytest.mark.parametrize("text,expected", [
    ("Wait here.\nWhere are you going?", ("Wait here. Where are you going?", "")),
    ("مَرْحَبًا بِكَ\nmarhaban bika", ("مَرْحَبًا بِكَ", "marhaban bika")),
    ("مرحبا\nTransliteration: marhaba", ("مرحبا", "marhaba")),
])
def test_split_preserves_multiline_latin_translation(text, expected):
    assert text_norm.split_translation_and_transliteration(text) == expected
