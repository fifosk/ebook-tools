from modules.epub_parser import (
    split_text_into_sentences,
    split_text_into_sentences_no_refine,
)

import pytest

pytestmark = pytest.mark.pipeline


def _normalized_text(text: str) -> str:
    return " ".join(text.split())


def _normalized_join(sentences: list[str]) -> str:
    return _normalized_text(" ".join(sentences))


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
    normalized = _normalized_join(sentences)

    for word in ["signal", "quietly", "late", "crew", "listened"]:
        assert word in normalized


@pytest.mark.parametrize(
    "text",
    [
        "The signal arrived (quietly and late). The crew listened.",
        'He said "Wait". Then the hallway went silent.',
        "Dr. A. Stone waited. Mr. B. Carter answered.",
        "She paused... then kept reading. The room stayed still.",
    ],
)
def test_refined_split_preserves_normalized_text_without_skips_or_overlap(text):
    sentences = split_text_into_sentences(text, max_words=20)

    assert _normalized_join(sentences) == _normalized_text(text)


def test_comma_semicolon_split_mode_preserves_delimiters():
    text = "The map was old, but readable; the route was still clear."

    sentences = split_text_into_sentences(
        text,
        max_words=20,
        extend_split_with_comma_semicolon=True,
    )

    assert sentences == [
        "The map was old,",
        "but readable;",
        "the route was still clear.",
    ]
    assert _normalized_join(sentences) == _normalized_text(text)
