from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_playback_transport_log.py"
SPEC = importlib.util.spec_from_file_location("check_apple_playback_transport_log", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


PAUSE_LOG = """
1782670000.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670000.050 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=true systemMusicPlaying=true
1782670000.060 [PlaybackTransport] Library pause command accepted requested=true playing=true musicPlaying=true
1782670000.080 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicSurface requested=false playing=false musicPlaying=false readerPause=true
"""


PAUSE_RESUME_LOG = (
    PAUSE_LOG
    + """
1782670001.200 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670001.220 [PlaybackTransport] Library forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670001.230 [PlaybackTransport] Library play command accepted requested=false playing=false musicPlaying=false
1782670001.260 [PlaybackTransport] Library ignored stale adopted Apple Music pause after reader play source=brokerResume
"""
)


def test_pause_release_playback_transport_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-release") == []


def test_pause_resume_playback_transport_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_RESUME_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-resume") == []


def test_pause_resume_requires_explicit_play_evidence(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport accepted explicit play",
        "stale Music pause was ignored or play was accepted cleanly",
    ]


def test_pause_release_rejects_forced_hardware_resume_before_explicit_play(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_LOG
        + """
1782670000.200 [PlaybackTransport] Library forced play source=brokerHardwareResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670000.250 [PlaybackTransport] Library play command accepted requested=false playing=false musicPlaying=false
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release")

    assert missing == ["reader pause was followed by a playback resume before explicit reader play"]


def test_missing_playback_transport_log_reports_path(tmp_path: Path) -> None:
    missing = module.validate_log(tmp_path / "missing.log", mode="pause-release")

    assert missing == [f"playback transport log does not exist: {tmp_path / 'missing.log'}"]


def test_default_log_path_matches_pull_helper() -> None:
    assert module.default_log_path("Living Room") == (
        module.REPO_ROOT / "test-results" / "apple-device-playback-transport-Living-Room.log"
    )
