from __future__ import annotations

import queue
import threading
import time
from types import SimpleNamespace

import pytest

from modules import audio_video_generator as av_gen
from modules.audio_video_generator import MediaPipelineResult
from modules.core.rendering import pipeline as pipeline_module
from modules.core.rendering.pipeline import PipelineState, RenderPipeline
from modules.progress_tracker import ProgressTracker


class _DummyExporter:
    def __init__(self) -> None:
        self.requests = []

    def export(self, request):  # pragma: no cover - interface stub
        self.requests.append(request)
        return None


@pytest.mark.timeout(5)
def test_parallel_pipeline_stops_incrementing_progress_after_stop_event(monkeypatch):
    tracker = ProgressTracker()
    tracker.set_total(10)

    stop_event = threading.Event()
    config = SimpleNamespace(
        queue_size=0,
        tempo=1.0,
        macos_reading_speed=100,
        selected_voice="test",
        thread_count=2,
    )

    pipeline = RenderPipeline(
        pipeline_config=config,
        progress_tracker=tracker,
        stop_event=stop_event,
    )

    state = PipelineState(current_batch_start=1)
    exporter = _DummyExporter()

    media_queue: queue.Queue = queue.Queue()
    captured_stop_events: list[threading.Event] = []

    def fake_start_media_pipeline(*args, **kwargs):
        stop = kwargs.get("stop_event")
        if isinstance(stop, threading.Event):
            captured_stop_events.append(stop)
        return media_queue, []

    def fake_create_translation_queue(_size):
        return queue.Queue()

    def fake_start_translation_pipeline(*args, **kwargs):  # pragma: no cover - interface stub
        return None

    def fake_build_written_and_video_blocks(*_args, **_kwargs):
        return "written", "video"

    monkeypatch.setattr(av_gen, "start_media_pipeline", fake_start_media_pipeline)

    monkeypatch.setattr(
        pipeline_module,
        "create_translation_queue",
        fake_create_translation_queue,
    )
    monkeypatch.setattr(
        pipeline_module,
        "start_translation_pipeline",
        fake_start_translation_pipeline,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_target_sequence",
        lambda *_args, **_kwargs: [("fr", 1)],
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_written_and_video_blocks",
        fake_build_written_and_video_blocks,
    )
    monkeypatch.setattr(
        pipeline_module,
        "transliterate_sentence",
        lambda *_args, **_kwargs: "",
    )
    monkeypatch.setattr(
        pipeline_module,
        "split_translation_and_transliteration",
        lambda text: (text, ""),
    )

    sentences = ["First", "Second", "Third"]

    thread = threading.Thread(
        target=pipeline._process_pipeline,
        kwargs={
            "state": state,
            "exporter": exporter,
            "sentences": sentences,
            "start_sentence": 1,
            "total_refined": len(sentences),
            "input_language": "en",
            "target_languages": ["fr"],
            "generate_audio": False,
            "generate_video": False,
            "audio_mode": "1",
            "written_mode": "default",
            "sentences_per_file": 2,
            "include_transliteration": False,
            "output_html": True,
            "output_pdf": False,
            "translation_client": object(),
            "worker_pool": object(),
            "worker_count": 2,
            "total_fully": len(sentences),
        },
    )
    thread.start()

    media_queue.put(
        MediaPipelineResult(
            index=0,
            sentence_number=1,
            sentence="First",
            target_language="fr",
            translation="Bonjour",
            audio_segment=None,
        )
    )

    deadline = time.time() + 2.0
    while time.time() < deadline:
        if tracker.snapshot().completed >= 1:
            break
        time.sleep(0.01)
    else:
        pytest.fail("Initial progress update not observed")

    stop_event.set()

    media_queue.put(
        MediaPipelineResult(
            index=1,
            sentence_number=2,
            sentence="Second",
            target_language="fr",
            translation="Encore",
            audio_segment=None,
        )
    )

    thread.join(timeout=2.0)
    assert not thread.is_alive(), "Pipeline thread did not terminate"

    snapshot = tracker.snapshot()
    assert snapshot.completed == 1
    assert state.processed == 1
    assert captured_stop_events and captured_stop_events[0] is stop_event
