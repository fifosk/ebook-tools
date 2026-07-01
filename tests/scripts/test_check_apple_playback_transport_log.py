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
1782670001.230 [PlaybackTransport] Library play command accepted requested=true playing=true musicPlaying=false deferredMusic=true
1782670001.260 [PlaybackTransport] Library ignored stale adopted Apple Music pause after reader play source=brokerResume
"""
)


RESUME_OFFSET_LOG = """
1782670003.000 [PlaybackTransport] Library resume offset requested sentence=2190 time=14.250 sequence=true
1782670003.050 [PlaybackTransport] Interactive sequence time seek accepted sentence=2190 time=14.250 track=translation
"""


RESUME_OFFSET_SINGLE_TRACK_LOG = """
1782670003.000 [PlaybackTransport] Job resume offset requested sentence=42 time=8.125 sequence=false
1782670003.050 [PlaybackTransport] Interactive time seek accepted sequence=false sentence=42 time=8.125
"""


MUSIC_ADOPTION_PAUSE_LOG = """
1782670000.000 [PlaybackTransport] Apple Music reader transport pause adopted source=observed non-playing reason=observedNonPlaying
1782670000.020 [PlaybackTransport] Library mirroring adopted Apple Music pause requested=true playing=true musicPlaying=false
1782670000.040 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicAdoption requested=true playing=true musicPlaying=false readerPause=true
"""


SPLIT_PAUSE_LOG = """
1782670000.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670000.020 [PlaybackTransport] Apple Music reader transport pause adopted source=observed non-playing reason=observedNonPlaying
1782670001.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670001.050 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=false systemMusicPlaying=false
1782670001.060 [PlaybackTransport] Library pause command accepted requested=true playing=true musicPlaying=false
"""


WEAK_FIRST_PAUSE_LOG = """
1782670000.000 [PlaybackTransport] Apple Music reader transport pause adopted source=observed non-playing reason=observedNonPlaying
1782670000.040 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicAdoption requested=false playing=false musicPlaying=false readerPause=true
1782670001.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670001.050 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=false systemMusicPlaying=false
1782670001.060 [PlaybackTransport] Library pause command accepted requested=true playing=true musicPlaying=false
"""


def test_pause_release_playback_transport_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-release") == []


def test_pause_resume_playback_transport_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_RESUME_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-resume") == []


def test_resume_offset_playback_transport_log_validation_passes(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(RESUME_OFFSET_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="resume-offset") == []


def test_resume_offset_accepts_single_track_exact_seek(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(RESUME_OFFSET_SINGLE_TRACK_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="resume-offset") == []


def test_resume_offset_rejects_sentence_start_fallback(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670003.000 [PlaybackTransport] Library resume offset requested sentence=2190 time=14.250 sequence=true
1782670003.050 [PlaybackTransport] Interactive sequence time seek fallback=sentenceStart sentence=2190 time=14.250
1782670003.060 [PlaybackTransport] Interactive sequence time seek accepted sentence=2190 time=12.000 track=translation
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="resume-offset")

    assert missing == ["sequence resume offset fell back to the beginning of the sentence"]


def test_resume_offset_requires_request_and_exact_seek(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="resume-offset")

    assert missing == [
        "reader requested saved resume offset",
        "reader applied exact resume offset",
    ]


def test_pause_release_accepts_music_pause_adoption_when_narration_mirrors_same_episode(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(MUSIC_ADOPTION_PAUSE_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-release") == []


def test_pause_release_rejects_split_pause_that_only_reaches_narration_on_second_click(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(SPLIT_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert missing == ["first pause episode did not reach narration before the next transport command"]


def test_pause_release_rejects_first_episode_with_only_reader_pause_flag(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(WEAK_FIRST_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert missing == ["first pause episode did not reach narration before the next transport command"]


def test_pause_resume_requires_explicit_play_evidence(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport accepted explicit play",
        "stale Music pause was ignored or play was accepted cleanly",
    ]


def test_pause_resume_rejects_dead_broker_resume_without_reader_request(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_LOG
        + """
1782670001.200 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670001.220 [PlaybackTransport] Library forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670001.230 [PlaybackTransport] Library play command accepted requested=false playing=false musicPlaying=false
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport accepted explicit play",
        "stale Music pause was ignored or play was accepted cleanly",
        "reader resume accepted without restoring narration playback request",
    ]


def test_pause_resume_ignores_stale_dead_resume_when_newer_resume_restores_narration(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_LOG
        + """
1782670001.200 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670001.220 [PlaybackTransport] Library forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670001.230 [PlaybackTransport] Library play command accepted requested=false playing=false musicPlaying=false
1782670010.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670010.020 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=true systemMusicPlaying=false
1782670010.030 [PlaybackTransport] Library pause command accepted requested=true playing=true musicPlaying=true
1782670010.060 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicSurface requested=false playing=false musicPlaying=false readerPause=true
1782670012.200 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670012.220 [PlaybackTransport] Library forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670012.225 [PlaybackTransport] Library restoring narration playback request source=brokerResume sentence=42
1782670012.230 [PlaybackTransport] Library play command accepted requested=true playing=true musicPlaying=false deferredMusic=true
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-resume") == []


def test_pause_resume_rejects_consecutive_broker_pauses_without_reader_play(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_LOG
        + """
1782670010.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670010.020 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=true systemMusicPlaying=false
1782670010.030 [PlaybackTransport] Library pause command accepted requested=true playing=true musicPlaying=true
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport accepted explicit play",
        "stale Music pause was ignored or play was accepted cleanly",
        "reader received consecutive broker pauses without an intervening reader play",
    ]


def test_pause_resume_accepts_restored_narration_request_after_dead_broker_resume(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_LOG
        + """
1782670001.200 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670001.220 [PlaybackTransport] Library forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670001.225 [PlaybackTransport] Library restoring narration playback request source=brokerResume sentence=42
1782670001.230 [PlaybackTransport] Library play command accepted requested=false playing=false musicPlaying=false
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-resume") == []


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


def test_diagnostic_hint_explains_empty_playback_transport_log() -> None:
    missing = ["reader transport accepted pause"]

    hints = module.diagnostic_hints(
        "Launched application with com.example.InteractiveReader.tvos bundle identifier.",
        mode="pause-release",
        missing=missing,
    )

    assert hints == [
        "log has no playback transport breadcrumbs; reproduce in a DEBUG Apple build, "
        "then run make apple-device-pull-and-verify-playback-transport-log without relaunching"
    ]


def test_diagnostic_hint_stays_quiet_for_specific_playback_transport_gaps() -> None:
    missing = ["reader transport accepted explicit play"]

    hints = module.diagnostic_hints(PAUSE_LOG, mode="pause-resume", missing=missing)

    assert hints == []


def test_default_log_path_matches_pull_helper() -> None:
    assert module.default_log_path("Living Room") == (
        module.REPO_ROOT / "test-results" / "apple-device-playback-transport-Living-Room.log"
    )
