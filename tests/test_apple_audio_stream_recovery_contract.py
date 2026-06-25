from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "ios" / "InteractiveReader" / "InteractiveReader" / "Services"
AUDIO_COORDINATOR = SERVICES / "AudioPlayerCoordinator.swift"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_audio_coordinator_retries_primary_stream_failures_once() -> None:
    source = _source(AUDIO_COORDINATOR)

    assert "private var streamFailureRetryCountByURL: [URL: Int] = [:]" in source
    assert "private let maxStreamFailureRetriesPerURL = 1" in source
    assert "self.retryFailedStreamIfPossible(failedItem)" in source
    assert "private func retryFailedStreamIfPossible(_ failedItem: AVPlayerItem)" in source
    assert "guard role == .primary else { return }" in source
    assert "guard isPlaybackRequested else { return }" in source
    assert "guard attempts < maxStreamFailureRetriesPerURL else" in source
    assert "streamFailureRetryCountByURL[failedURL] = attempts + 1" in source
    assert "loadFileAndSeek(at: failedIndex, seekTo: resumeTime)" in source


def test_audio_stream_retry_preserves_multifile_timeline_state() -> None:
    source = _source(AUDIO_COORDINATOR)

    assert "let allActiveURLs = activeURLs" in source
    assert "let urlsFromTarget = Array(allActiveURLs[fileIndex...])" in source
    assert "activeURLs = allActiveURLs" in source
    assert "activeURL = urlsFromTarget.first" in source
    assert "streamFailureRetryCountByURL = [:]" in source


def test_stall_observer_is_owned_and_removed_on_rebuild() -> None:
    source = _source(AUDIO_COORDINATOR)

    assert "private var stallObserver: NSObjectProtocol?" in source
    assert "stallObserver = NotificationCenter.default.addObserver(" in source
    assert "if let observer = stallObserver" in source
    assert "NotificationCenter.default.removeObserver(observer)" in source
    assert "stallObserver = nil" in source
