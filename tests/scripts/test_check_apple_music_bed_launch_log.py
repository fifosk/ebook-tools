from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_music_bed_launch_log.py"
SPEC = importlib.util.spec_from_file_location("check_apple_music_bed_launch_log", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


STARTUP_LOG = """
InteractiveReaderTV[101] Apple Music reading bed ownership=appleMusicBed playing=true observedAsBed=true
InteractiveReaderTV[101] Reader NowPlaying session attached player=true
InteractiveReaderTV[101] Reader NowPlaying session active=true canBecomeActive=true
InteractiveReaderTV[101] Reader NowPlaying remoteCommandsEnabled=true
InteractiveReaderTV[101] Reader NowPlaying transport=playing playbackRate=1.0 force=true position=0.0 duration=42.0
InteractiveReaderTV[101] Reader NowPlaying session reassert requested metadata=true stateKnown=true
"""


PAUSE_RELEASE_LOG = (
    STARTUP_LOG
    + """
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression=true reason=readerTransportPause
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression watchdog started reason=readerTransportPause
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression reasserted reason=watchdog
InteractiveReaderTV[101] Apple Music observed non-playing confirmed; marking reader transport paused
InteractiveReaderTV[101] Apple Music reader transport kept tvOS playback surface suppressed reason=readerTransportPause
"""
)


def test_startup_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(STARTUP_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="startup") == []


def test_pause_release_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(PAUSE_RELEASE_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-release") == []


def test_pause_release_requires_extra_reader_owned_pause_evidence(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(STARTUP_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert "fullscreen Music artwork suppression was enabled" in missing
    assert "fullscreen Music artwork suppression watchdog started" in missing
    assert "fullscreen Music artwork suppression was reasserted" in missing
    assert "reader-owned Music pause was observed" in missing
    assert "tvOS Music playback surface was suppressed without stealing reader transport" in missing


def test_validation_reports_missing_log_without_dumping_contents(tmp_path: Path) -> None:
    missing = module.validate_log(tmp_path / "missing.log", mode="startup")

    assert missing == [f"launch log does not exist: {tmp_path / 'missing.log'}"]


def test_default_log_path_matches_unattended_device_helper() -> None:
    assert module.default_log_path("Living Room Apple TV") == (
        module.REPO_ROOT / "test-results" / "apple-device-launch-console-Living-Room-Apple-TV.log"
    )
