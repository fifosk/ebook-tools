from modules.epub_parser import (
    compare_sentence_splitter_modes,
    normalize_sentence_splitter_mode,
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


def test_split_preserves_smart_closing_quote_after_sentence_punctuation():
    text = "She whispered “Look there.” Then she closed the book."

    assert split_text_into_sentences_no_refine(text) == [
        "She whispered “Look there.”",
        "Then she closed the book.",
    ]
    assert split_text_into_sentences(text, max_words=20) == [
        "She whispered “Look there.”",
        "Then she closed the book.",
    ]


def test_split_keeps_initials_with_following_names():
    text = "Dr. A. Stone waited. Mr. B. Carter answered."

    sentences = split_text_into_sentences(text, max_words=20)

    assert sentences == [
        "Dr. A. Stone waited.",
        "Mr. B. Carter answered.",
    ]
    assert _normalized_join(sentences) == _normalized_text(text)


def test_split_detects_lowercase_sentence_starts_after_terminal_punctuation():
    text = "the door closed. then silence followed. another page turned."

    expected = [
        "the door closed.",
        "then silence followed.",
        "another page turned.",
    ]

    assert split_text_into_sentences_no_refine(text) == expected
    assert split_text_into_sentences(text, max_words=20) == expected
    assert _normalized_join(expected) == _normalized_text(text)


def test_split_detects_lowercase_sentence_starts_after_closing_quotes():
    text = 'She whispered "run." then the lights failed. he listened.'

    expected = [
        'She whispered "run."',
        "then the lights failed.",
        "he listened.",
    ]

    assert split_text_into_sentences_no_refine(text) == expected
    assert split_text_into_sentences(text, max_words=20) == expected
    assert _normalized_join(expected) == _normalized_text(text)


def test_split_detects_ascii_opening_quote_after_sentence_boundary():
    text = 'He stopped. "run," she said. then the lights failed.'

    expected = [
        "He stopped.",
        '"run," she said.',
        "then the lights failed.",
    ]

    assert split_text_into_sentences_no_refine(text) == expected
    assert split_text_into_sentences(text, max_words=20) == expected
    assert _normalized_join(expected) == _normalized_text(text)


def test_split_keeps_ellipses_with_lowercase_continuations():
    text = "She paused... then kept reading. the room stayed still."

    expected = [
        "She paused... then kept reading.",
        "the room stayed still.",
    ]

    assert split_text_into_sentences_no_refine(text) == expected
    assert split_text_into_sentences(text, max_words=20) == expected
    assert _normalized_join(expected) == _normalized_text(text)


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
        "the door closed. then silence followed. another page turned.",
        'She whispered "run." then the lights failed. he listened.',
        'He stopped. "run," she said. then the lights failed.',
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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "وصل الفريق، ثم بدأ البحث؛ وكانت الخريطة واضحة.",
            [
                "وصل الفريق،",
                "ثم بدأ البحث؛",
                "وكانت الخريطة واضحة.",
            ],
        ),
        (
            "地図は古く，でも読めた；道はまだ見えた。",
            [
                "地図は古く，",
                "でも読めた；",
                "道はまだ見えた。",
            ],
        ),
    ],
)
def test_comma_semicolon_split_mode_preserves_non_ascii_delimiters(text, expected):
    sentences = split_text_into_sentences(
        text,
        max_words=20,
        extend_split_with_comma_semicolon=True,
    )

    assert sentences == expected
    if " " in text:
        assert _normalized_join(sentences) == _normalized_text(text)
    else:
        assert "".join(sentences) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("他来了。她笑了！他们走了吗？是的。", ["他来了。", "她笑了！", "他们走了吗？", "是的。"]),
        ("「準備できた？」彼女は聞いた。彼はうなずいた。", ["「準備できた？」", "彼女は聞いた。", "彼はうなずいた。"]),
        ("هل وصل؟ نعم وصل۔", ["هل وصل؟", "نعم وصل۔"]),
    ],
)
def test_non_latin_sentence_punctuation_creates_boundaries(text, expected):
    assert split_text_into_sentences_no_refine(text) == expected
    assert split_text_into_sentences(text, max_words=20) == expected
    expected_text = " ".join(expected) if " " in text else "".join(expected)
    assert expected_text == text


def test_modern_splitter_mode_falls_back_to_regex_when_unavailable(monkeypatch):
    text = 'Dr. A. Stone waited. then she whispered "go."'

    monkeypatch.setattr(
        "modules.epub_parser._split_text_into_sentences_modern",
        lambda *_args, **_kwargs: None,
    )

    regex_sentences = split_text_into_sentences(text, max_words=20)
    modern_sentences = split_text_into_sentences(
        text,
        max_words=20,
        splitter_mode="modern",
    )
    report = compare_sentence_splitter_modes(text, max_words=20)

    assert modern_sentences == regex_sentences
    assert report["modern"]["fallback_to_regex"] is True
    assert report["sentence_count_delta"] == 0
    assert report["normalized_text_coverage"] == {"regex": True, "modern": True}


def test_sentence_splitter_mode_normalization_defaults_to_regex():
    assert normalize_sentence_splitter_mode("modern") == "modern"
    assert normalize_sentence_splitter_mode("REGEX") == "regex"
    assert normalize_sentence_splitter_mode("unsupported") == "regex"
