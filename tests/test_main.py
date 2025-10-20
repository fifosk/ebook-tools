import time

from modules.progress_tracker import ProgressTracker

import main


class _StubSampler:
    def __init__(self):
        self.closed = False
        self._snapshot = main.SystemMetricsSnapshot(
            cpu_percent=12.5,
            memory_percent=42.0,
            memory_rss=512 * 1024 * 1024,
            read_rate=4096.0,
            write_rate=2048.0,
            timestamp=time.time(),
        )

    def snapshot(self):
        return self._snapshot

    def close(self):
        self.closed = True


def test_progress_logger_includes_system_metrics(monkeypatch):
    messages = []

    def fake_console_info(message, *args, **kwargs):
        text = str(message)
        if args:
            text = text % args
        messages.append(text)

    monkeypatch.setattr(main.log_mgr, "console_info", fake_console_info)

    tracker = ProgressTracker()
    sampler = _StubSampler()
    logger = main.log_mgr.logger
    progress_logger = main._CLIProgressLogger(
        tracker,
        logger_obj=logger,
        metrics_sampler=sampler,
    )

    tracker.set_total(8)
    tracker.record_media_completion(0, 1)

    progress_logger.close()

    assert any("CPU 12.5%" in message for message in messages)
    assert any("Memory 512.0 MiB (42.0%)" in message for message in messages)
    assert any("IO 4.0 KiB/s read, 2.0 KiB/s write" in message for message in messages)
    assert sampler.closed


def test_sampler_provides_initial_snapshot():
    sampler = main._SystemMetricsSampler(interval=60.0)
    try:
        snapshot = sampler.snapshot()
        assert snapshot is not None
        assert snapshot.memory_rss >= 0
    finally:
        sampler.close()
