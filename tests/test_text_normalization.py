from modules.epub_parser import remove_quotes
from modules import text_normalization as text_norm


def test_remove_quotes_preserves_apostrophes():
    text = "Il s’agit d’un test “simple”."

    normalized = remove_quotes(text)

    assert normalized == "Il s'agit d'un test \"simple\"."


def test_collapse_whitespace_removes_newlines():
    text = "Bonjour\nle\tmonde  !"

    assert text_norm.collapse_whitespace(text) == "Bonjour le monde !"
