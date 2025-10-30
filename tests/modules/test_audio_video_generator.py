import threading
from queue import Queue

import pytest
from pydub import AudioSegment

from modules.audio_video_generator import (
    _media_worker,
    generate_audio_for_sentence,
    render_video_slides,
)
from modules.progress_tracker import ProgressTracker
from modules.translation_engine import TranslationTask


def test_media_worker_does_not_increment_tracker_when_queueing_results():
    tracker = ProgressTracker(total_blocks=1)

    class DummySynthesizer:
        def synthesize_sentence(self, *args, **kwargs):
            return AudioSegment.silent(duration=0)

    synthesizer = DummySynthesizer()

    task_queue = Queue()
    result_queue = Queue()
    stop_event = threading.Event()

    task_queue.put(
        TranslationTask(
            index=0,
            sentence_number=1,
            sentence="Hello",
            target_language="en",
            translation="Hello",
        )
    )
    task_queue.put(None)

    worker = threading.Thread(
        target=_media_worker,
        args=(
            "TestWorker",
            task_queue,
            result_queue,
        ),
        kwargs={
            "total_sentences": 1,
            "input_language": "en",
            "audio_mode": "1",
            "language_codes": {"en": "en"},
            "selected_voice": "test",
            "voice_overrides": None,
            "tempo": 1.0,
            "macos_reading_speed": 100,
            "generate_audio": True,
            "stop_event": stop_event,
            "progress_tracker": tracker,
            "audio_synthesizer": synthesizer,
        },
        daemon=True,
    )
    worker.start()
    worker.join(timeout=2.0)
    assert not worker.is_alive()

    result = result_queue.get(timeout=1.0)
    assert result is not None

    snapshot = tracker.snapshot()
    assert snapshot.completed == 0


def test_generate_audio_for_sentence_emits_deprecation_warning(monkeypatch):
    class DummySynthesizer:
        def synthesize_sentence(self, *args, **kwargs):
            return AudioSegment.silent(duration=0)

    dummy = DummySynthesizer()
    monkeypatch.setattr(
        "modules.audio_video_generator.get_audio_synthesizer",
        lambda: dummy,
    )

    with pytest.deprecated_call():
        generate_audio_for_sentence(
            sentence_number=1,
            input_sentence="Hello",
            fluent_translation="Bonjour",
            input_language="English",
            target_language="French",
            audio_mode="1",
            total_sentences=1,
            language_codes={"English": "en", "French": "fr"},
            selected_voice="gTTS",
            voice_overrides=None,
            tempo=1.0,
            macos_reading_speed=100,
        )


def test_render_video_slides_emits_deprecation_warning(monkeypatch, tmp_path):
    class DummyService:
        def render(self, *args, **kwargs):
            return str(tmp_path / "output.mp4")

    monkeypatch.setattr(
        "modules.audio_video_generator.VideoService",
        lambda: DummyService(),
    )

    audio = [AudioSegment.silent(duration=100)]
    with pytest.deprecated_call():
        result = render_video_slides(
            text_blocks=["Hello"],
            audio_segments=audio,
            output_dir=str(tmp_path),
            batch_start=1,
            batch_end=1,
            base_no_ext="base",
            cover_img=None,
            book_author="Author",
            book_title="Title",
            cumulative_word_counts=[1],
            total_word_count=1,
            macos_reading_speed=100,
            input_language="English",
            total_sentences=1,
            tempo=1.0,
            sync_ratio=1.0,
            word_highlighting=False,
            highlight_granularity="word",
        )

    assert result.endswith("output.mp4")
