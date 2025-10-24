import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.core.rendering.pipeline import PipelineState, RenderPipeline


class StubProgressTracker:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish_progress(self, metadata=None) -> None:  # pragma: no cover - simple stub
        self.events.append(dict(metadata or {}))


class DummyConfig:
    pass


def test_handle_completed_export_records_video_and_preview() -> None:
    tracker = StubProgressTracker()
    pipeline = RenderPipeline(pipeline_config=DummyConfig(), progress_tracker=tracker)
    state = PipelineState()
    state.sentences_per_file = 5

    pipeline._handle_completed_export(
        state,
        "storage/runtime/batch-001.mp4",
        ["storage/runtime/batch-001_0001.png", "storage/runtime/batch-001_0001.png"],
    )

    assert state.batch_video_files == ["storage/runtime/batch-001.mp4"]
    assert state.batch_preview_files == ["storage/runtime/batch-001_0001.png"]
    assert tracker.events, "progress events should be published"
    emitted = tracker.events[-1]
    assert emitted["stage"] == "batch_export"
    assert emitted["batch_index"] == 1
    assert emitted["batch_video_file"] == "storage/runtime/batch-001.mp4"
    assert emitted["batch_preview"] == "storage/runtime/batch-001_0001.png"
    assert emitted["preview_path"] == "storage/runtime/batch-001_0001.png"
    assert emitted["batch_previews"] == ["storage/runtime/batch-001_0001.png"]
    assert state.next_preview_refresh_at == 10


def test_handle_completed_export_updates_previews_without_new_video() -> None:
    tracker = StubProgressTracker()
    pipeline = RenderPipeline(pipeline_config=DummyConfig(), progress_tracker=tracker)
    state = PipelineState()
    state.batch_video_files.append("storage/runtime/batch-001.mp4")
    state.batch_preview_files.append("storage/runtime/batch-001_0001.png")

    pipeline._handle_completed_export(
        state,
        None,
        ["storage/runtime/batch-001_0002.png", "storage/runtime/batch-001_0002.png"],
    )

    assert state.batch_video_files == ["storage/runtime/batch-001.mp4"]
    assert state.batch_preview_files == [
        "storage/runtime/batch-001_0001.png",
        "storage/runtime/batch-001_0002.png",
    ]
    emitted = tracker.events[-1]
    assert emitted["stage"] == "batch_export"
    assert "batch_index" not in emitted
    assert emitted["batch_preview"] == "storage/runtime/batch-001_0002.png"
    assert emitted["preview_path"] == "storage/runtime/batch-001_0002.png"
    assert emitted["batch_previews"] == ["storage/runtime/batch-001_0002.png"]


def test_preview_refresh_event_emitted_after_configured_interval() -> None:
    tracker = StubProgressTracker()
    pipeline = RenderPipeline(pipeline_config=DummyConfig(), progress_tracker=tracker)
    state = PipelineState()
    state.sentences_per_file = 4
    state.processed = 4

    pipeline._handle_completed_export(
        state,
        "storage/runtime/batch-001.mp4",
        ["storage/runtime/batch-001_0001.png"],
    )

    # discard initial batch_export event
    tracker.events.clear()

    # Advance processing to the next batch boundary and ensure a refresh event fires.
    state.processed = 8
    pipeline._maybe_publish_preview_refresh(state)

    assert tracker.events, "expected a refresh event to be emitted"
    refresh = tracker.events[-1]
    assert refresh["stage"] == "batch_preview_refresh"
    assert refresh["batch_preview"] == "storage/runtime/batch-001_0001.png"
    assert refresh["preview_path"] == "storage/runtime/batch-001_0001.png"
    assert refresh["batch_previews"] == ["storage/runtime/batch-001_0001.png"]


def test_finalise_preview_refresh_emits_event_when_threshold_not_met() -> None:
    tracker = StubProgressTracker()
    pipeline = RenderPipeline(pipeline_config=DummyConfig(), progress_tracker=tracker)
    state = PipelineState()
    state.sentences_per_file = 6
    state.processed = 6

    pipeline._handle_completed_export(
        state,
        "storage/runtime/batch-001.mp4",
        ["storage/runtime/batch-001_0001.png"],
    )

    tracker.events.clear()

    # No additional sentences processed; finalisation should still trigger a refresh event.
    pipeline._finalise_preview_refresh(state)

    assert tracker.events, "expected finalisation to emit a refresh event"
    emitted = tracker.events[-1]
    assert emitted["stage"] == "batch_preview_refresh"
    assert emitted["batch_preview"] == "storage/runtime/batch-001_0001.png"
