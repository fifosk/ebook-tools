import threading
from queue import Queue

from pydub import AudioSegment

from modules.audio_video_generator import _media_worker
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
