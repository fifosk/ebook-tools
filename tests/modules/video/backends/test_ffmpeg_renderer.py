from __future__ import annotations

from pathlib import Path
import types

import pytest
from pydub import AudioSegment

from modules.media.exceptions import CommandExecutionError
from modules.video.api import VideoService
from modules.video.backends import VideoRenderOptions
from modules.video.backends.ffmpeg_renderer import FFmpegVideoRenderer
from modules.video.slide_renderer import SentenceFrameBatch, SlideFrameTask


class DummyRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command, **_):
        self.commands.append(list(command))


def _make_frame_batch(tmp_path: Path) -> SentenceFrameBatch:
    frame_path = tmp_path / "frame.png"
    frame_path.write_bytes(b"")
    task = SlideFrameTask(
        index=0,
        block="Header",
        duration=1.0,
        original_highlight_index=0,
        translation_highlight_index=0,
        transliteration_highlight_index=0,
        original_char_range=None,
        translation_char_range=None,
        transliteration_char_range=None,
        slide_size=(1280, 720),
        initial_font_size=60,
        default_font_path="Arial.ttf",
        bg_color=(0, 0, 0),
        cover_image_bytes=None,
        header_info="header",
        highlight_granularity="word",
        output_path=str(frame_path),
        template_name=None,
    )
    return SentenceFrameBatch(frame_tasks=[task], pad_duration=0.0, profiler=None)


@pytest.fixture()
def silence_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    silence_path = tmp_path / "silence.wav"
    silence_path.write_bytes(b"")
    monkeypatch.setattr(
        "modules.video.backends.ffmpeg_renderer.silence_audio_path",
        lambda: str(silence_path),
    )
    return silence_path


def _video_options() -> VideoRenderOptions:
    return VideoRenderOptions(
        batch_start=1,
        batch_end=1,
        cover_image=None,
        book_author="Author",
        book_title="Title",
        cumulative_word_counts=[0],
        total_word_count=10,
        macos_reading_speed=120,
        input_language="en",
        total_sentences=1,
        tempo=1.0,
        sync_ratio=0.9,
        word_highlighting=True,
        highlight_granularity="word",
    )


def test_video_service_selects_backend_and_merges_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class StubRenderer:
        def __init__(self) -> None:
            self.render_calls = 0

        def render_slides(self, slides, audio, output_path, options):  # noqa: ANN001
            self.render_calls += 1
            captured["options"] = options
            return output_path

        def concatenate(self, video_paths, output_path):  # noqa: ANN001
            return output_path

    renderer = StubRenderer()

    def fake_factory(name: str, settings: dict[str, object] | None):
        captured["name"] = name
        captured["settings"] = settings or {}
        return renderer

    config = types.SimpleNamespace(
        video_backend="ffmpeg",
        video_backend_settings={"ffmpeg": {"loglevel": "info"}},
    )
    monkeypatch.setattr("modules.video.api.get_rendering_config", lambda: config)

    service = VideoService(
        backend="ffmpeg",
        backend_settings={"ffmpeg": {"executable": "custom"}},
        renderer_factory=fake_factory,
    )

    audio = AudioSegment.silent(duration=1000)
    output_path = tmp_path / "service_output.mp4"
    result = service.render(["Slide"], [audio], str(output_path), _video_options())

    assert result == str(output_path)
    assert renderer.render_calls == 1
    assert captured["name"] == "ffmpeg"
    assert captured["settings"]["loglevel"] == "info"
    assert captured["settings"]["executable"] == "custom"


def test_ffmpeg_renderer_builds_expected_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silence_file: Path
) -> None:
    batch = _make_frame_batch(tmp_path)
    monkeypatch.setattr(
        "modules.video.backends.ffmpeg_renderer.prepare_sentence_frames",
        lambda *args, **kwargs: batch,
    )

    monkeypatch.setattr(
        AudioSegment,
        "export",
        lambda self, out_f, format="wav", **_: Path(out_f).write_bytes(b""),
        raising=False,
    )

    fake_runner = DummyRunner()
    renderer = FFmpegVideoRenderer(
        executable="custom_ffmpeg", command_runner=fake_runner
    )

    audio = AudioSegment.silent(duration=1000)
    output_path = tmp_path / "output" / "video.mp4"
    result_path = renderer.render_slides(["Header"], [audio], str(output_path), _video_options())

    assert result_path == str(output_path)
    assert fake_runner.commands[0][0] == "custom_ffmpeg"
    assert fake_runner.commands[-1][-1] == str(output_path)
    assert len(fake_runner.commands) == 4  # frame, concat, merge, final concat


def test_ffmpeg_renderer_propagates_subprocess_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silence_file: Path
) -> None:
    batch = _make_frame_batch(tmp_path)
    monkeypatch.setattr(
        "modules.video.backends.ffmpeg_renderer.prepare_sentence_frames",
        lambda *args, **kwargs: batch,
    )
    monkeypatch.setattr(
        AudioSegment,
        "export",
        lambda self, out_f, format="wav", **_: Path(out_f).write_bytes(b""),
        raising=False,
    )

    def failing_run(command, **_):
        raise CommandExecutionError(command, returncode=1)

    renderer = FFmpegVideoRenderer(command_runner=failing_run)
    audio = AudioSegment.silent(duration=1000)

    with pytest.raises(CommandExecutionError):
        renderer.render_slides(["Header"], [audio], str(tmp_path / "output.mp4"), _video_options())
