from __future__ import annotations

import math
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest
import regex


try:  # pragma: no cover - exercised when dependency is available
    from pydub import AudioSegment  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - provide lightweight fallback
    class AudioSegment:  # type: ignore[override]
        """Minimal stub replicating behaviour used by the tests."""

        def __init__(self, duration: int, frame_rate: int = 44100) -> None:
            self.duration = int(duration)
            self.frame_rate = frame_rate
            self.raw_data: bytes = b""

        @classmethod
        def silent(cls, duration: int) -> "AudioSegment":
            return cls(duration)

        def __len__(self) -> int:  # pragma: no cover - trivial
            return self.duration

        def __add__(self, other: "AudioSegment") -> "AudioSegment":  # pragma: no cover - trivial
            if not isinstance(other, AudioSegment):
                return NotImplemented
            combined = AudioSegment(self.duration + other.duration, frame_rate=self.frame_rate)
            combined.raw_data = self.raw_data + other.raw_data
            return combined

        def set_frame_rate(self, frame_rate: int) -> "AudioSegment":  # pragma: no cover - trivial
            clone = AudioSegment(self.duration, frame_rate=frame_rate)
            clone.raw_data = self.raw_data
            return clone

        def _spawn(self, raw_data: bytes, overrides: dict | None = None) -> "AudioSegment":  # pragma: no cover - trivial
            frame_rate = overrides.get("frame_rate", self.frame_rate) if overrides else self.frame_rate
            clone = AudioSegment(self.duration, frame_rate=frame_rate)
            clone.raw_data = raw_data
            return clone

        @property
        def duration_seconds(self) -> float:  # pragma: no cover - trivial
            return self.duration / 1000.0


    fake_module = types.ModuleType("pydub")
    fake_module.AudioSegment = AudioSegment
    sys.modules.setdefault("pydub", fake_module)


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)


class _StubGTTS:  # pragma: no cover - used only when dependency is missing
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def write_to_fp(self, fp) -> None:  # pragma: no cover - trivial
        fp.write(b"")


gtts_stub = types.ModuleType("gtts")
gtts_stub.gTTS = _StubGTTS
sys.modules.setdefault("gtts", gtts_stub)


env_stub = types.ModuleType("modules.environment")
env_stub.load_environment = lambda *args, **kwargs: None
sys.modules.setdefault("modules.environment", env_stub)


config_stub = types.ModuleType("modules.config_manager")
config_stub.get_thread_count = lambda: 1
config_stub.get_runtime_context = lambda default=None: None
config_stub.set_runtime_context = lambda context: None
config_stub.clear_runtime_context = lambda: None
sys.modules.setdefault("modules.config_manager", config_stub)


class _StubLogger:  # pragma: no cover - trivial logging sink
    def debug(self, *args, **kwargs) -> None:
        pass

    def error(self, *args, **kwargs) -> None:
        pass

    def info(self, *args, **kwargs) -> None:
        pass


logging_stub = types.ModuleType("modules.logging_manager")
logging_stub.logger = _StubLogger()
logging_stub.console_warning = lambda *args, **kwargs: None
logging_stub.console_info = lambda *args, **kwargs: None
logging_stub.get_logger = lambda: logging_stub.logger
sys.modules.setdefault("modules.logging_manager", logging_stub)


output_formatter_stub = types.ModuleType("modules.output_formatter")
sys.modules.setdefault("modules.output_formatter", output_formatter_stub)


translation_stub = types.ModuleType("modules.translation_engine")


@dataclass
class TranslationTask:  # pragma: no cover - used for type compatibility
    index: int
    sentence_number: int
    sentence: str
    translation: str
    target_language: str


translation_stub.TranslationTask = TranslationTask
sys.modules.setdefault("modules.translation_engine", translation_stub)


pil_stub = types.ModuleType("PIL")
pil_image_stub = types.ModuleType("PIL.Image")
pil_draw_stub = types.ModuleType("PIL.ImageDraw")
pil_font_stub = types.ModuleType("PIL.ImageFont")
pil_image_stub.Image = type("_StubImage", (), {})
pil_draw_stub.Draw = lambda *args, **kwargs: None
pil_font_stub.truetype = lambda *args, **kwargs: None
pil_stub.Image = pil_image_stub
pil_stub.ImageDraw = pil_draw_stub
pil_stub.ImageFont = pil_font_stub
sys.modules.setdefault("PIL", pil_stub)
sys.modules.setdefault("PIL.Image", pil_image_stub)
sys.modules.setdefault("PIL.ImageDraw", pil_draw_stub)
sys.modules.setdefault("PIL.ImageFont", pil_font_stub)


project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from modules.audio import highlight
from modules.audio.tts import SILENCE_DURATION_MS
from modules.audio_video_generator import generate_audio_for_sentence


def test_generate_audio_for_sentence_highlight_metadata(monkeypatch):
    numbering_text = "1 - 50.00%"
    input_text = "Hello world"
    translation_text = "Bonjour le monde"

    durations = {
        numbering_text: 300,
        input_text: 200,
        translation_text: 500,
    }

    def fake_synthesize(text: str, lang_code: str, selected_voice: str, macos_reading_speed: int) -> AudioSegment:
        duration = durations[text]
        segment = AudioSegment.silent(duration=duration)
        timings = []
        if text:
            per_char = duration / max(len(text), 1)
            cursor = 0.0
            for ch in text:
                timings.append({"char": ch, "start_ms": cursor, "duration_ms": per_char})
                cursor += per_char
        setattr(segment, "character_timing", timings)
        return segment

    monkeypatch.setattr("modules.audio_video_generator.synthesize_segment", fake_synthesize)

    audio = generate_audio_for_sentence(
        sentence_number=1,
        input_sentence=input_text,
        fluent_translation=translation_text,
        input_language="English",
        target_language="French",
        audio_mode="3",
        total_sentences=2,
        language_codes={"English": "en", "French": "fr"},
        selected_voice="gTTS",
        tempo=1.0,
        macos_reading_speed=180,
    )

    metadata = highlight._get_audio_metadata(audio)
    assert metadata is not None

    total_seconds = len(audio) / 1000.0
    assert metadata.total_duration == pytest.approx(total_seconds, rel=1e-6)

    expected_kinds = [
        "other",
        "silence",
        "original",
        "silence",
        "translation",
        "silence",
    ]
    assert [part.kind for part in metadata.parts] == expected_kinds

    silence_seconds = SILENCE_DURATION_MS / 1000.0
    expected_durations = [
        durations[numbering_text] / 1000.0,
        silence_seconds,
        durations[input_text] / 1000.0,
        silence_seconds,
        durations[translation_text] / 1000.0,
        silence_seconds,
    ]
    for part, expected in zip(metadata.parts, expected_durations):
        assert math.isclose(part.duration, expected, rel_tol=1e-6)
        if part.kind != "silence":
            non_space_graphemes = [
                m
                for m in regex.finditer(r"\X", part.text)
                if not m.group().isspace()
            ]
            assert len(part.steps) == len(non_space_graphemes)
            if part.steps:
                assert part.steps[0].start_ms == pytest.approx(part.start_offset * 1000.0)
                total_step_duration = sum(step.duration_ms for step in part.steps)
                assert total_step_duration == pytest.approx(part.duration * 1000.0)
        else:
            assert part.steps
            for step in part.steps:
                assert step.duration_ms == pytest.approx(SILENCE_DURATION_MS)

    events = highlight._build_events_from_metadata(
        metadata,
        sync_ratio=1.0,
        num_original_words=len(input_text.split()),
        num_translation_words=len(translation_text.split()),
        num_translit_words=0,
    )

    assert events
    assert sum(event.duration for event in events) == pytest.approx(total_seconds)

    original_events = [event for event in events if event.step and event.step.kind == "original"]
    translation_events = [
        event for event in events if event.step and event.step.kind == "translation"
    ]
    silence_events = [event for event in events if event.step and event.step.kind == "silence"]

    assert original_events
    assert translation_events
    assert silence_events

    assert original_events[0].original_index == 1
    assert original_events[-1].original_index == len(input_text.split())
    assert translation_events[-1].translation_index == len(translation_text.split())

    first_translation_step = translation_events[0].step
    assert first_translation_step is not None
    assert first_translation_step.char_index_start == 0
    assert translation_events[-1].step is not None
    assert translation_events[-1].step.char_index_end == len(translation_text)

    legacy_events = highlight._build_legacy_highlight_events(
        audio_duration=total_seconds,
        sync_ratio=1.0,
        original_words=input_text.split(),
        translation_units=translation_text.split(),
        transliteration_words=[],
    )

    assert legacy_events
    assert sum(event.duration for event in legacy_events) == pytest.approx(total_seconds)
    assert legacy_events[-1].translation_index == len(translation_text.split())


def test_highlight_round_trip_mixed_language_timings():
    sequence = ["translation"]
    mixed_text = "你好 a\u0301"
    per_char_duration = 80
    timings = []
    cursor = 0.0
    for ch in mixed_text:
        timings.append({"char": ch, "start_ms": cursor, "duration_ms": per_char_duration})
        cursor += per_char_duration

    segment = AudioSegment.silent(duration=int(cursor))
    setattr(segment, "character_timing", timings)

    segments = {"translation": segment}
    audio = segment

    metadata = highlight._compute_audio_highlight_metadata(
        audio,
        sequence,
        segments,
        tempo=1.0,
        texts={"translation": mixed_text},
    )

    assert metadata.parts
    translation_part = next(part for part in metadata.parts if part.kind == "translation")
    assert translation_part.steps

    events = highlight._build_events_from_metadata(
        metadata,
        sync_ratio=1.0,
        num_original_words=0,
        num_translation_words=len(mixed_text.split()),
        num_translit_words=0,
    )

    translation_events = [
        event for event in events if event.step and event.step.kind == "translation"
    ]
    assert translation_events
    assert translation_events[-1].step is not None
    assert translation_events[-1].step.char_index_end <= len(mixed_text)

    accent_event = next(
        event
        for event in translation_events
        if event.step and event.step.char_index_start == mixed_text.index("a")
    )
    assert accent_event.step is not None
    assert accent_event.step.char_index_end - accent_event.step.char_index_start == 2
    assert accent_event.step.duration_ms == pytest.approx(per_char_duration * 2)
