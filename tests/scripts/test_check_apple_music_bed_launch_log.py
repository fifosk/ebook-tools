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
InteractiveReaderTV[101] tvOS remote playPause forwarded to player broker
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression=true reason=readerTransportPause
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression watchdog started reason=readerTransportPause
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression reasserted reason=watchdog
InteractiveReaderTV[101] Library reader transport forced pause source=foreground requested=true playing=true musicPlaying=false systemMusicPlaying=false
InteractiveReaderTV[101] Apple Music reader transport pause adopted source=reader transport reason=readerTransportPause
InteractiveReaderTV[101] Apple Music reader transport kept tvOS playback surface suppressed reason=readerTransportPause
"""
)


GUARDED_PLAY_LOG = (
    PAUSE_RELEASE_LOG
    + """
InteractiveReaderTV[101] Job reader transport play command ignored reader-pause-guard action=play
"""
)


PAUSE_RESUME_LOG = (
    PAUSE_RELEASE_LOG
    + """
InteractiveReaderTV[101] Library reader transport play command requested=false playing=false musicPlaying=false
InteractiveReaderTV[101] Apple Music playback surface changed reason=resume revision=3
"""
)


OBSERVED_NON_PLAYING_PAUSE_LOG = (
    STARTUP_LOG
    + """
InteractiveReaderTV[101] tvOS remote playPause forwarded to player broker
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression=true reason=observedNonPlaying
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression watchdog started reason=observedNonPlaying
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression reasserted reason=watchdog
InteractiveReaderTV[101] Apple Music reader transport pause adopted source=observed non-playing reason=observedNonPlaying
InteractiveReaderTV[101] Library playback accepted Apple Music pause as reader transport source=musicAdoption
InteractiveReaderTV[101] Apple Music reader transport kept tvOS playback surface suppressed reason=observedNonPlaying
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


def test_pause_release_accepts_observed_music_only_pause_adoption(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(OBSERVED_NON_PLAYING_PAUSE_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-release") == []


def test_guarded_play_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(GUARDED_PLAY_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="guarded-play") == []


def test_pause_resume_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(PAUSE_RESUME_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-resume") == []


def test_pause_resume_allows_broker_resume_before_play_acceptance(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        PAUSE_RELEASE_LOG
        + """
InteractiveReaderTV[101] Job reader transport forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
InteractiveReaderTV[101] Job reader transport play command requested=false playing=false musicPlaying=false
InteractiveReaderTV[101] Apple Music playback surface changed reason=resume revision=9
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-resume") == []


def test_pause_release_requires_extra_reader_owned_pause_evidence(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(STARTUP_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert "tvOS remote Play/Pause reached the app broker" in missing
    assert "fullscreen Music artwork suppression was enabled" in missing
    assert "fullscreen Music artwork suppression watchdog started" in missing
    assert "fullscreen Music artwork suppression was reasserted" in missing
    assert "reader-owned Music pause was observed" in missing
    assert "reader transport used the reader-owned pause route" in missing
    assert "sentence narration mirrored the reader-owned Music pause" in missing
    assert "tvOS Music playback surface was suppressed without stealing reader transport" in missing


def test_pause_release_does_not_accept_passive_music_pause_as_reader_pause(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        STARTUP_LOG
        + """
InteractiveReaderTV[101] tvOS remote playPause forwarded to player broker
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression=true reason=readerTransportPause
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression watchdog started reason=readerTransportPause
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression reasserted reason=watchdog
InteractiveReaderTV[101] Library reader transport forced pause source=foreground requested=true playing=true musicPlaying=false systemMusicPlaying=false
InteractiveReaderTV[101] Apple Music observed non-playing confirmed; marking reader transport paused
InteractiveReaderTV[101] Apple Music reader transport kept tvOS playback surface suppressed reason=readerTransportPause
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release")

    assert missing == ["reader-owned Music pause was observed"]


def test_pause_release_requires_narration_pause_after_observed_music_pause(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        STARTUP_LOG
        + """
InteractiveReaderTV[101] tvOS remote playPause forwarded to player broker
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression=true reason=observedNonPlaying
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression watchdog started reason=observedNonPlaying
InteractiveReaderTV[101] Apple Music fullscreen artwork suppression reasserted reason=watchdog
InteractiveReaderTV[101] Apple Music reader transport pause adopted source=observed non-playing reason=observedNonPlaying
InteractiveReaderTV[101] Apple Music reader transport kept tvOS playback surface suppressed reason=observedNonPlaying
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release")

    assert missing == ["sentence narration mirrored the reader-owned Music pause"]


def test_guarded_play_requires_reader_pause_guard_evidence(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(PAUSE_RELEASE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="guarded-play")

    assert missing == ["stray Now Playing play callback was ignored during reader pause guard"]


def test_pause_resume_requires_reader_resume_evidence(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(PAUSE_RELEASE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport accepted an explicit resume command",
        "Apple Music bed resumed under reader ownership",
    ]


def test_pause_release_rejects_system_resume_before_explicit_reader_play(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        PAUSE_RELEASE_LOG
        + """
InteractiveReaderTV[101] Apple Music observed reader transport resume from system playback
InteractiveReaderTV[101] Library playback mirroring Apple Music play to narration requested=false playing=false musicPlaying=true manual=false readerPause=false
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release")

    assert missing == [
        "reader transport pause was followed by a system-driven resume before explicit reader play"
    ]


def test_pause_release_rejects_reader_recovery_before_explicit_reader_play(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        PAUSE_RELEASE_LOG
        + """
InteractiveReaderTV[101] Library reader transport in-place recovery requested=false playing=false time=12.345
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release")

    assert missing == [
        "reader transport pause was followed by a system-driven resume before explicit reader play"
    ]


def test_pause_release_rejects_broker_forced_play_before_explicit_reader_play(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        PAUSE_RELEASE_LOG
        + """
InteractiveReaderTV[101] Job reader transport forced play source=brokerHardwareResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
InteractiveReaderTV[101] Job reader transport play command requested=false playing=false musicPlaying=false
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release")

    assert missing == [
        "reader transport pause was followed by a system-driven resume before explicit reader play"
    ]


def test_pause_release_rejects_foreground_forced_play_before_explicit_reader_play(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        PAUSE_RELEASE_LOG
        + """
InteractiveReaderTV[101] Library reader transport forced play source=foregroundHardwareResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
InteractiveReaderTV[101] Library reader transport play command requested=false playing=false musicPlaying=false
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release")

    assert missing == [
        "reader transport pause was followed by a system-driven resume before explicit reader play"
    ]


def test_pause_resume_rejects_system_forced_play_before_explicit_reader_play(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        PAUSE_RELEASE_LOG
        + """
InteractiveReaderTV[101] Job reader transport forced play source=foregroundHardwareResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
InteractiveReaderTV[101] Job reader transport play command requested=false playing=false musicPlaying=false
InteractiveReaderTV[101] Apple Music playback surface changed reason=resume revision=9
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport pause was followed by a system-driven resume before explicit reader play"
    ]


def test_pause_release_allows_system_resume_after_explicit_reader_play(tmp_path: Path) -> None:
    log = tmp_path / "launch.log"
    log.write_text(
        PAUSE_RELEASE_LOG
        + """
InteractiveReaderTV[101] Library reader transport play command requested=false playing=false musicPlaying=false
InteractiveReaderTV[101] Apple Music observed reader transport resume from system playback
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-release") == []


def test_validation_reports_missing_log_without_dumping_contents(tmp_path: Path) -> None:
    missing = module.validate_log(tmp_path / "missing.log", mode="startup")

    assert missing == [f"launch log does not exist: {tmp_path / 'missing.log'}"]


def test_diagnostic_hint_explains_state_preserving_capture_for_launch_only_logs() -> None:
    missing = ["reader-owned Music pause was observed"]

    hints = module.diagnostic_hints(
        "Launched application with com.example.InteractiveReader.tvos bundle identifier.",
        mode="pause-release",
        missing=missing,
    )

    assert hints == [
        "log has no reader/Music playback breadcrumbs; for an in-progress Apple TV repro, "
        "capture with APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING=1 make apple-device-launch-console "
        "before pressing Play/Pause"
    ]


def test_diagnostic_hint_stays_quiet_for_playback_logs_with_specific_gaps() -> None:
    missing = ["sentence narration mirrored the reader-owned Music pause"]

    hints = module.diagnostic_hints(
        OBSERVED_NON_PLAYING_PAUSE_LOG,
        mode="pause-release",
        missing=missing,
    )

    assert hints == []


def test_default_log_path_matches_unattended_device_helper() -> None:
    assert module.default_log_path("Living Room Apple TV") == (
        module.REPO_ROOT / "test-results" / "apple-device-launch-console-Living-Room-Apple-TV.log"
    )
