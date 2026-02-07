import textwrap
from pathlib import Path

import pytest

import modules.subtitles.translation as subtitle_translation
import modules.subtitles.processing as subtitle_processing
from modules.subtitles.language import SubtitleLanguageContext
from modules.subtitles.models import SubtitleColorPalette, SubtitleCue, SubtitleJobOptions
from modules.subtitles.processing import process_subtitle_file
from modules.subtitles.render import CueTextRenderer, _build_output_cues

pytestmark = pytest.mark.pipeline


def _sample_source_cue() -> SubtitleCue:
    return SubtitleCue(
        index=1,
        start=0.0,
        end=2.0,
        lines=["Hello world"],
    )


def test_build_output_cues_srt_highlight() -> None:
    palette = SubtitleColorPalette.default()
    renderer = CueTextRenderer("srt", palette)
    cues = _build_output_cues(
        _sample_source_cue(),
        "hola mundo",
        "",
        highlight=True,
        show_original=True,
        renderer=renderer,
    )
    assert len(cues) == 2

    first_cue = cues[0]
    assert '<font color="#FFD60A">Hello world</font>' in first_cue.lines[0]
    translation_line = first_cue.lines[1]
    assert '<font color="#FB923C" size="5"><b>hola</b></font>' in translation_line
    assert '<font color="#21C55D" size="5">mundo</font>' in translation_line

    second_cue = cues[1]
    translation_line_second = second_cue.lines[1]
    assert '<font color="#FB923C" size="5">hola</font>' in translation_line_second
    assert '<font color="#FB923C" size="5"><b>mundo</b></font>' in translation_line_second


def test_build_output_cues_ass_highlight() -> None:
    palette = SubtitleColorPalette.default()
    renderer = CueTextRenderer("ass", palette)
    cues = _build_output_cues(
        _sample_source_cue(),
        "hola mundo",
        "",
        highlight=True,
        show_original=True,
        renderer=renderer,
    )
    assert len(cues) == 2

    first_translation = cues[0].lines[1]
    # Highlight colour should be the first word with bold enabled.
    assert "{\\c&H3C92FB&}{\\b1}hola{\\b0}" in first_translation
    # Remaining words stay green.
    assert "{\\c&H5DC521&}mundo" in first_translation


def test_build_output_cues_hide_original_line() -> None:
    palette = SubtitleColorPalette.default()
    renderer = CueTextRenderer("srt", palette)
    cues = _build_output_cues(
        _sample_source_cue(),
        "hola mundo",
        "",
        highlight=True,
        show_original=False,
        renderer=renderer,
    )
    assert len(cues) == 2
    first_cue = cues[0]
    assert len(first_cue.lines) == 1
    assert all("#FFD60A" not in line for line in first_cue.lines)
    assert '<font color="#FB923C" size="5"><b>hola</b></font>' in first_cue.lines[0]


@pytest.fixture
def srt_source(tmp_path: Path) -> Path:
    payload = textwrap.dedent(
        """\
        1
        00:00:00,000 --> 00:00:02,000
        Hello world
        """
    ).strip() + "\n"
    source = tmp_path / "source.srt"
    source.write_text(payload, encoding="utf-8")
    return source


def _stub_translation(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setattr(
        subtitle_translation,
        "translate_sentence_simple",
        lambda text, src, tgt, **kwargs: value,
    )
    # Disable the batch translation path so the per-cue fallback is used,
    # which calls our mocked translate_sentence_simple via _translate_text.
    def _fake_translate_batch(sentences, *args, **kwargs):
        raise RuntimeError("batch disabled in test")

    monkeypatch.setattr(
        subtitle_processing,
        "translate_batch",
        _fake_translate_batch,
    )
    # Prevent origin language re-translation from overwriting original_text.
    monkeypatch.setattr(
        subtitle_processing,
        "_resolve_language_context",
        lambda cues, options: SubtitleLanguageContext(
            detected_language=options.input_language,
            detection_source="test_stub",
            detection_sample="",
            translation_source_language=options.input_language,
            origin_language=options.input_language,
            origin_translation_needed=False,
        ),
    )


def test_process_subtitle_file_emits_colourised_srt(tmp_path: Path, srt_source: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    output_path = tmp_path / "source.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="srt",
    )

    result = process_subtitle_file(
        srt_source,
        output_path,
        options,
        mirror_output_path=None,
    )

    payload = output_path.read_text(encoding="utf-8")
    assert result.cue_count == 1
    assert '<font color="#FFD60A">Hello world</font>' in payload
    assert '<font color="#FB923C" size="5"><b>hola</b></font>' in payload
    assert '<font color="#21C55D" size="5">mundo</font>' in payload


def test_transliteration_skips_latin_targets(
    tmp_path: Path,
    srt_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    transliterator_calls = {"get": 0, "render": 0}

    class _TransliteratorStub:
        def transliterate(self, *_args, **_kwargs):
            transliterator_calls["render"] += 1
            return type("Result", (), {"text": "should-not-appear"})()

    def _fake_get_transliterator():
        transliterator_calls["get"] += 1
        return _TransliteratorStub()

    monkeypatch.setattr(
        subtitle_processing,
        "get_transliterator",
        _fake_get_transliterator,
    )

    output_path = tmp_path / "source.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=True,
        highlight=True,
        show_original=True,
        output_format="srt",
    )

    result = process_subtitle_file(
        srt_source,
        output_path,
        options,
        mirror_output_path=None,
    )

    payload = output_path.read_text(encoding="utf-8")
    assert "should-not-appear" not in payload
    assert transliterator_calls == {"get": 0, "render": 0}
    assert result.metadata["transliteration"] is False


def test_transliteration_applies_to_non_latin_targets(
    tmp_path: Path,
    srt_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_translation(monkeypatch, "こんにちは 世界")
    transliterator_calls = {"get": 0}

    class _TransliteratorStub:
        def __init__(self) -> None:
            self.calls = 0

        def transliterate(self, *_args, **_kwargs):
            self.calls += 1
            return type("Result", (), {"text": "konnichiwa sekai"})()

    transliterator = _TransliteratorStub()

    def _fake_get_transliterator():
        transliterator_calls["get"] += 1
        return transliterator

    monkeypatch.setattr(
        subtitle_processing,
        "get_transliterator",
        _fake_get_transliterator,
    )

    output_path = tmp_path / "source.ja.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Japanese",
        enable_transliteration=True,
        highlight=True,
        show_original=True,
        output_format="srt",
    )

    result = process_subtitle_file(
        srt_source,
        output_path,
        options,
        mirror_output_path=None,
    )

    payload = output_path.read_text(encoding="utf-8")
    html_payload = (output_path.parent / "html" / "source.ja.drt.html").read_text(
        encoding="utf-8"
    )
    assert "konnichiwa" in payload and "sekai" in payload
    assert "konnichiwa sekai" in html_payload
    assert transliterator_calls["get"] == 1
    assert transliterator.calls == 1
    assert result.metadata["transliteration"] is True


def test_process_subtitle_file_appends_html_transcript(
    tmp_path: Path, srt_source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    output_path = tmp_path / "source.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="srt",
    )

    process_subtitle_file(
        srt_source,
        output_path,
        options,
        mirror_output_path=None,
    )

    html_path = output_path.parent / "html" / "source.es.drt.html"
    assert html_path.exists()
    html_payload = html_path.read_text(encoding="utf-8")
    assert html_payload.startswith("<!DOCTYPE html>")
    assert '<meta charset="utf-8">' in html_payload
    assert "<h3>00:00:00–00:00:02</h3>" in html_payload
    assert "<p>Hello world</p>" in html_payload
    assert '<p style="font-size:150%; font-weight:600;">hola mundo</p>' in html_payload
    assert html_payload.rstrip().endswith("</body>\n</html>")


def test_process_subtitle_file_hides_original_when_disabled(
    tmp_path: Path, srt_source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    output_path = tmp_path / "source.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=False,
        output_format="srt",
    )

    result = process_subtitle_file(
        srt_source,
        output_path,
        options,
        mirror_output_path=None,
    )

    payload = output_path.read_text(encoding="utf-8")
    assert "Hello world" not in payload
    assert '<font color="#FB923C" size="5"><b>hola</b></font>' in payload
    assert '<font color="#21C55D" size="5">hola mundo</font>' not in payload
    assert result.metadata["show_original"] is False
    assert result.metadata["original_language"] == "English"


def test_process_subtitle_file_emits_ass_with_header(tmp_path: Path, srt_source: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    output_path = tmp_path / "source.es.drt.ass"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="ass",
    )

    process_subtitle_file(
        srt_source,
        output_path,
        options,
        mirror_output_path=None,
    )

    payload = output_path.read_text(encoding="utf-8")
    assert payload.startswith("[Script Info]")
    assert "Style: DRT,Arial,56,&H5DC521&,&H3C92FB&,&H64000000,&HA0000000" in payload
    assert payload.count("Dialogue: 0,") == 2
    assert "Dialogue: 0,0:00:00.00" in payload
    assert "0:00:02.00,DRT" in payload
    assert "{\\c&H3C92FB&}{\\b1}hola{\\b0}" in payload


def test_process_subtitle_file_uses_custom_llm_model(
    tmp_path: Path,
    srt_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ClientStub:
        def __init__(self) -> None:
            self.closed = False

        def __enter__(self) -> "_ClientStub":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            self.closed = True

        def close(self) -> None:
            self.closed = True

    captured_clients: list[_ClientStub] = []
    captured_kwargs: list[dict] = []

    def _fake_create_client(**kwargs):
        client = _ClientStub()
        captured_clients.append(client)
        captured_kwargs.append(kwargs)
        return client

    used_clients: list[_ClientStub | None] = []

    def _fake_translate(
        text,
        src,
        tgt,
        **kwargs,
    ):
        used_clients.append(kwargs.get("client"))
        return "hola mundo"

    monkeypatch.setattr(subtitle_translation, "create_client", _fake_create_client)
    monkeypatch.setattr(
        subtitle_translation,
        "translate_sentence_simple",
        _fake_translate,
    )
    # Disable the batch translation path so the per-cue fallback is used,
    # which exercises create_client and translate_sentence_simple via _translate_text.
    monkeypatch.setattr(
        subtitle_processing,
        "translate_batch",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("batch disabled")),
    )

    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="srt",
        llm_model="llama3:8b",
    )

    output_path = tmp_path / "source.es.drt.srt"
    process_subtitle_file(
        srt_source,
        output_path,
        options,
        mirror_output_path=None,
    )

    assert captured_kwargs and captured_kwargs[0]["model"] == "llama3:8b"
    assert used_clients and used_clients[0] is captured_clients[0]
    assert captured_clients[0].closed is True


def test_process_subtitle_file_respects_end_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    source_path = tmp_path / "window.srt"
    source_payload = textwrap.dedent(
        """\
        1
        00:00:00,000 --> 00:00:10,000
        Hello world

        2
        00:00:12,000 --> 00:00:15,000
        Another line
        """
    ).strip() + "\n"
    source_path.write_text(source_payload, encoding="utf-8")
    output_path = tmp_path / "window.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        start_time_offset=0.0,
        end_time_offset=5.0,
        output_format="srt",
    )

    result = process_subtitle_file(
        source_path,
        output_path,
        options,
        mirror_output_path=None,
    )

    payload = output_path.read_text(encoding="utf-8")
    assert "00:00:05,000" in payload
    assert "00:00:10,000" not in payload
    assert "00:00:12" not in payload
    assert result.metadata["end_time_offset_seconds"] == pytest.approx(5.0)
    assert result.metadata["end_time_offset_label"] == "00:05"


def test_process_subtitle_file_merges_windows_when_generate_audio_book_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    source_path = tmp_path / "multi.srt"
    source_payload = textwrap.dedent(
        """\
        1
        00:00:00,000 --> 00:00:01,000
        First line

        2
        00:00:01,100 --> 00:00:02,000
        Second line

        3
        00:00:02,100 --> 00:00:03,000
        Third line
        """
    ).strip() + "\n"
    source_path.write_text(source_payload, encoding="utf-8")

    output_path = tmp_path / "multi.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="srt",
        generate_audio_book=True,
    )
    result = process_subtitle_file(
        source_path,
        output_path,
        options,
        mirror_output_path=None,
    )
    assert result.cue_count == 1


def test_process_subtitle_file_streams_transcript_batches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    source_path = tmp_path / "multi.srt"
    source_payload = textwrap.dedent(
        """\
        1
        00:00:00,000 --> 00:00:01,000
        First line

        2
        00:00:01,100 --> 00:00:02,000
        Second line

        3
        00:00:02,100 --> 00:00:03,000
        Third line
        """
    ).strip() + "\n"
    source_path.write_text(source_payload, encoding="utf-8")

    output_path = tmp_path / "multi.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="srt",
        generate_audio_book=True,
    )
    received: list[tuple[int, object]] = []

    def _capture(batch):
        received.extend(list(batch))

    result = process_subtitle_file(
        source_path,
        output_path,
        options,
        mirror_output_path=None,
        on_transcript_batch=_capture,
    )
    assert result.cue_count == 1
    assert len(received) == 1
    sentence_number, entry = received[0]
    assert sentence_number == 1
    assert "First line" in entry.original_text
    assert entry.translation_text == "hola mundo"


def test_process_subtitle_file_transcript_callback_preserves_indices_without_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    source_path = tmp_path / "multi.srt"
    source_payload = textwrap.dedent(
        """\
        1
        00:00:00,000 --> 00:00:01,000
        First line

        2
        00:00:01,100 --> 00:00:02,000
        Second line

        3
        00:00:02,100 --> 00:00:03,000
        Third line
        """
    ).strip() + "\n"
    source_path.write_text(source_payload, encoding="utf-8")

    output_path = tmp_path / "multi.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="srt",
        generate_audio_book=False,
    )
    received: list[tuple[int, object]] = []

    def _capture(batch):
        received.extend(list(batch))

    result = process_subtitle_file(
        source_path,
        output_path,
        options,
        mirror_output_path=None,
        on_transcript_batch=_capture,
    )
    assert result.cue_count == 3
    assert [sentence_number for sentence_number, _ in received] == [1, 2, 3]


def test_process_subtitle_file_preserves_cues_when_generate_audio_book_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_translation(monkeypatch, "hola mundo")
    source_path = tmp_path / "multi.srt"
    source_payload = textwrap.dedent(
        """\
        1
        00:00:00,000 --> 00:00:01,000
        First line

        2
        00:00:01,100 --> 00:00:02,000
        Second line

        3
        00:00:02,100 --> 00:00:03,000
        Third line
        """
    ).strip() + "\n"
    source_path.write_text(source_payload, encoding="utf-8")

    output_path = tmp_path / "multi.es.drt.srt"
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=True,
        show_original=True,
        output_format="srt",
        generate_audio_book=False,
    )
    result = process_subtitle_file(
        source_path,
        output_path,
        options,
        mirror_output_path=None,
    )
    assert result.cue_count == 3


def test_original_line_sanitises_html_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subtitle_translation,
        "translate_sentence_simple",
        lambda text, *_args, **_kwargs: "hola mundo",
    )
    cue = SubtitleCue(
        index=1,
        start=0.0,
        end=2.0,
        lines=["<i>Hello</i> <span>world</span> &amp; beyond"],
    )
    options = SubtitleJobOptions(
        input_language="English",
        target_language="Spanish",
        enable_transliteration=False,
        highlight=False,
        show_original=True,
        output_format="srt",
    )
    renderer = CueTextRenderer("srt", SubtitleColorPalette.default())
    result = _build_output_cues(
        cue,
        "hola mundo",
        "",
        highlight=False,
        show_original=True,
        renderer=renderer,
    )
    assert len(result) == 1
    original_line = result[0].lines[0]
    assert "<font" in original_line
    assert "<i>" not in original_line
    assert original_line.count("&amp;") == 1
    assert "Hello world & beyond" in original_line.replace("&amp;", "&")


def test_subtitle_job_options_require_end_after_start() -> None:
    with pytest.raises(ValueError):
        SubtitleJobOptions(
            input_language="English",
            target_language="Spanish",
            start_time_offset=10.0,
            end_time_offset=5.0,
        )
