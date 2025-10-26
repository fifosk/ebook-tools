import pytest
from pydub import AudioSegment

from modules.media.exceptions import MediaBackendError
from modules.video.api import VideoService
from modules.video.backends.base import VideoRenderOptions


class _RecordingVideoClient:
    def __init__(self, render_result=None, concatenate_result=None, render_error=None, concat_error=None):
        self.render_calls = []
        self.concatenate_calls = []
        self._render_result = render_result or {"result": {"path": "/tmp/remote.mp4"}}
        self._concatenate_result = concatenate_result or {"result": {"path": "/tmp/concat.mp4"}}
        self._render_error = render_error
        self._concat_error = concat_error

    def render(self, **kwargs):
        self.render_calls.append(kwargs)
        if self._render_error:
            raise self._render_error
        return self._render_result

    def concatenate(self, *args, **kwargs):
        self.concatenate_calls.append((args, kwargs))
        if self._concat_error:
            raise self._concat_error
        return self._concatenate_result


def _build_service(monkeypatch, client):
    service = VideoService(
        backend="api",
        backend_settings={"api": {"base_url": "https://example"}},
    )
    monkeypatch.setattr(VideoService, "_resolve_api_client", lambda self: client)
    return service


def _render_options():
    return VideoRenderOptions(batch_start=1, batch_end=1)


@pytest.fixture
def audio_segment():
    return AudioSegment.silent(duration=10)


def test_video_service_render_uses_api_client(monkeypatch, audio_segment):
    metrics = []
    monkeypatch.setattr(
        "modules.video.api.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )
    client = _RecordingVideoClient()
    service = _build_service(monkeypatch, client)

    result = service.render(
        ["slide"],
        [audio_segment],
        "/tmp/output.mp4",
        _render_options(),
    )

    assert result == "/tmp/remote.mp4"
    assert client.render_calls, "API client should be invoked"
    assert metrics, "Telemetry metric should be recorded"
    metric_name, attributes = metrics[-1]
    assert metric_name == "video.api.render.duration"
    assert attributes["status"] == "success"


def test_video_service_render_api_errors_record_metrics(monkeypatch, audio_segment, caplog):
    metrics = []
    monkeypatch.setattr(
        "modules.video.api.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )
    error = MediaBackendError("boom")
    client = _RecordingVideoClient(render_error=error)
    service = _build_service(monkeypatch, client)

    with caplog.at_level("ERROR"):
        with pytest.raises(MediaBackendError):
            service.render(
                ["slide"],
                [audio_segment],
                "/tmp/output.mp4",
                _render_options(),
            )

    assert client.render_calls, "API client should be invoked before failing"
    assert metrics, "Telemetry metric should be recorded on failure"
    metric_name, attributes = metrics[-1]
    assert metric_name == "video.api.render.duration"
    assert attributes["status"] == "error"
    assert any("Remote video render failed" in message for message in caplog.messages)


def test_video_service_concatenate_uses_api_client(monkeypatch):
    metrics = []
    monkeypatch.setattr(
        "modules.video.api.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )
    client = _RecordingVideoClient()
    service = _build_service(monkeypatch, client)

    result = service.concatenate(["one.mp4", "two.mp4"], "/tmp/output.mp4")

    assert result == "/tmp/concat.mp4"
    assert client.concatenate_calls, "API client should be invoked"
    assert metrics, "Telemetry metric should be recorded"
    metric_name, attributes = metrics[-1]
    assert metric_name == "video.api.concatenate.duration"
    assert attributes["status"] == "success"


def test_video_service_concatenate_error(monkeypatch, caplog):
    metrics = []
    monkeypatch.setattr(
        "modules.video.api.observability.record_metric",
        lambda name, value, attributes=None: metrics.append((name, attributes)),
    )
    error = MediaBackendError("nope")
    client = _RecordingVideoClient(concat_error=error)
    service = _build_service(monkeypatch, client)

    with caplog.at_level("ERROR"):
        with pytest.raises(MediaBackendError):
            service.concatenate(["one.mp4"], "/tmp/output.mp4")

    assert client.concatenate_calls, "API client should be invoked"
    assert metrics, "Telemetry metric should be recorded"
    metric_name, attributes = metrics[-1]
    assert metric_name == "video.api.concatenate.duration"
    assert attributes["status"] == "error"
    assert any("Remote video concatenate failed" in message for message in caplog.messages)
