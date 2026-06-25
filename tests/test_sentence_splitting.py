from modules.epub_parser import (
    split_text_into_sentences,
    split_text_into_sentences_no_refine,
)

import pytest

pytestmark = pytest.mark.pipeline


def test_merges_short_trailing_chunk_when_under_overflow_limit():
    text = " ".join([f"word{i}" for i in range(1, 22)]) + "."

    sentences = split_text_into_sentences(text, max_words=10)

    assert len(sentences) == 2
    assert [len(sentence.split()) for sentence in sentences] == [10, 11]


def test_respects_overflow_limit_and_keeps_extra_segment():
    text = " ".join([f"token{i}" for i in range(1, 27)]) + "."

    sentences = split_text_into_sentences(text, max_words=10)

    assert [len(sentence.split()) for sentence in sentences] == [10, 10, 6]


def test_split_preserves_closing_quote_after_sentence_punctuation():
    text = 'She whispered "Look there." Then she closed the book.'

    sentences = split_text_into_sentences_no_refine(text)

    assert sentences == [
        'She whispered "Look there."',
        "Then she closed the book.",
    ]


def test_refined_split_preserves_closing_quote_after_sentence_punctuation():
    text = 'She whispered "Look there." Then she closed the book.'

    sentences = split_text_into_sentences(text, max_words=20)
    normalized = " ".join(sentences)

    assert '"Look there."' in normalized
    assert sentences[-1] == "Then she closed the book."


def test_refined_split_preserves_parenthetical_words():
    text = "The signal arrived (quietly and late). The crew listened."

    sentences = split_text_into_sentences(text, max_words=20)
    normalized = " ".join(sentences)

    for word in ["signal", "quietly", "late", "crew", "listened"]:
        assert word in normalized
