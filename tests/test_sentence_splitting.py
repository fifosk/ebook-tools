from modules.epub_parser import split_text_into_sentences


def test_merges_short_trailing_chunk_when_under_overflow_limit():
    text = " ".join([f"word{i}" for i in range(1, 22)]) + "."

    sentences = split_text_into_sentences(text, max_words=10)

    assert len(sentences) == 2
    assert [len(sentence.split()) for sentence in sentences] == [10, 11]


def test_respects_overflow_limit_and_keeps_extra_segment():
    text = " ".join([f"token{i}" for i in range(1, 27)]) + "."

    sentences = split_text_into_sentences(text, max_words=10)

    assert [len(sentence.split()) for sentence in sentences] == [10, 10, 6]
