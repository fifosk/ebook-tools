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
1782670000.120 [PlaybackTransport] Library confirmed reader pause source=pauseCommand requested=false playing=false musicPlaying=false
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


RESUME_OFFSET_STABLE_RETRY_LOG = """
1782670003.000 [PlaybackTransport] Library resume offset requested sentence=2190 time=14.250 sequence=true
1782670003.050 [PlaybackTransport] Interactive sequence time seek accepted sentence=2190 time=14.250 track=translation
1782670003.500 [PlaybackTransport] Library resume offset retry sentence=2190 time=14.250 sequence=true
1782670003.550 [PlaybackTransport] Interactive sequence time seek accepted sentence=2190 time=14.250 track=translation
"""


RESUME_OFFSET_SINGLE_TRACK_LOG = """
1782670003.000 [PlaybackTransport] Job resume offset requested sentence=42 time=8.125 sequence=false
1782670003.050 [PlaybackTransport] Interactive time seek accepted sequence=false sentence=42 time=8.125
"""


MUSIC_ADOPTION_PAUSE_LOG = """
1782670000.000 [PlaybackTransport] Apple Music reader transport pause adopted source=observed non-playing reason=observedNonPlaying
1782670000.020 [PlaybackTransport] Library mirroring adopted Apple Music pause requested=true playing=true musicPlaying=false
1782670000.040 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicAdoption requested=true playing=true musicPlaying=false readerPause=true
1782670000.080 [PlaybackTransport] Library confirmed reader pause source=musicAdoption requested=false playing=false musicPlaying=false
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


UNSETTLED_FIRST_PAUSE_LOG = """
1782670000.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670000.050 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=true systemMusicPlaying=false
1782670000.060 [PlaybackTransport] Library pause command accepted requested=true playing=true musicPlaying=true
1782670001.000 [PlaybackTransport] Library broker tvOS Play/Pause command
"""


ACTIVE_OBSERVED_NONPLAYING_CUT_LOG = """
1783104500.730 [PlaybackTransport] Job forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1783104500.741 [PlaybackTransport] Job restoring narration playback request source=brokerResume sentence=2656
1783104500.741 [PlaybackTransport] Job resume offset requested sentence=2656 time=0.000 sequence=true
1783104500.742 [PlaybackTransport] Interactive sequence time seek accepted sentence=2656 time=0.000 track=original
1783104500.751 [PlaybackTransport] Job play command accepted requested=true playing=true musicPlaying=false deferredMusic=true
1783104515.025 [PlaybackTransport] Apple Music reader transport pause adopted source=active observed non-playing reason=observedNonPlaying
1783104515.025 [PlaybackTransport] Job accepted Apple Music pause as reader transport source=musicSurface requested=true playing=true musicPlaying=false readerPause=false
1783104515.034 [PlaybackTransport] Apple Music reader transport pause reinforced reason=musicSurface
1783104515.042 [PlaybackTransport] Job mirroring adopted Apple Music pause requested=false playing=false musicPlaying=false
1783104515.042 [PlaybackTransport] Job accepted Apple Music pause as reader transport source=musicAdoption requested=false playing=false musicPlaying=false readerPause=true
1783104515.203 [PlaybackTransport] Job confirmed reader pause source=musicAdoption requested=false playing=false musicPlaying=false systemMusicPlaying=false
"""


REQUESTED_ONLY_BROKER_PAUSE_LOG = """
1783105696.887 [PlaybackTransportBuild] release=2026.07.03.001 marketing=2026.7.3 bundle=20260703001 branch=unknown commit=unknown
1783105696.886 [PlaybackTransport] Job broker tvOS Play/Pause command
1783105696.890 [PlaybackTransport] Job forced pause source=brokerPause requested=true playing=false musicPlaying=true systemMusicPlaying=false
1783105696.891 [PlaybackTransport] Job pause command accepted requested=true playing=false musicPlaying=true
1783105696.912 [PlaybackTransport] Apple Music reader transport pause adopted source=reader transport reason=readerTransportPause
1783105696.914 [PlaybackTransport] Job reasserting reader pause after stray Apple Music play requested=false playing=false musicPlaying=true
1783105696.914 [PlaybackTransport] Job accepted Apple Music pause as reader transport source=musicPlayReassert requested=false playing=false musicPlaying=true readerPause=false
1783105696.946 [PlaybackTransport] Job accepted Apple Music pause as reader transport source=musicAdoption requested=false playing=false musicPlaying=false readerPause=true
1783105697.058 [PlaybackTransport] Job confirmed reader pause source=musicAdoption requested=false playing=false musicPlaying=false systemMusicPlaying=false
"""


REQUESTED_ONLY_MUSIC_SURFACE_PAUSE_LOG = """
1783106391.702 [PlaybackTransportBuild] release=2026.07.03.001 marketing=2026.7.3 bundle=20260703001 branch=unknown commit=unknown
1783106391.702 [PlaybackTransport] Job accepted Apple Music pause as reader transport source=musicSurface requested=true playing=false musicPlaying=false readerPause=false
1783106391.712 [PlaybackTransport] Apple Music reader transport pause reinforced reason=musicSurface
1783106391.868 [PlaybackTransport] Job confirmed reader pause source=musicSurface requested=false playing=false musicPlaying=false systemMusicPlaying=false
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


def test_resume_offset_accepts_stable_sequence_retry_track(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(RESUME_OFFSET_STABLE_RETRY_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="resume-offset") == []


def test_resume_offset_rejects_retry_that_flips_sequence_track(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670003.000 [PlaybackTransport] Job resume offset requested sentence=2190 time=14.250 sequence=true
1782670003.050 [PlaybackTransport] Interactive sequence time seek accepted sentence=2190 time=14.250 track=translation
1782670003.500 [PlaybackTransport] Job resume offset retry sentence=2190 time=14.250 sequence=true
1782670003.550 [PlaybackTransport] Interactive sequence time seek accepted sentence=2190 time=14.250 track=original
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="resume-offset")

    assert missing == [
        "sequence resume retry changed track from translation to original for sentence 2190"
    ]


def test_resume_offset_accepts_single_track_exact_seek(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(RESUME_OFFSET_SINGLE_TRACK_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="resume-offset") == []


def test_resume_offset_rejects_sequence_sentence_start_request(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670003.000 [PlaybackTransport] Library resume offset requested sentence=2190 time=0.000 sequence=true
1782670003.050 [PlaybackTransport] Interactive sequence time seek accepted sentence=2190 time=0.000 track=translation
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="resume-offset")

    assert missing == ["reader resume offset started at the beginning of the sentence"]


def test_resume_offset_rejects_single_track_sentence_start_request(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670003.000 [PlaybackTransport] Job resume offset requested sentence=42 time=0.000 sequence=false
1782670003.050 [PlaybackTransport] Interactive time seek accepted sequence=false sentence=42 time=0.000
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="resume-offset")

    assert missing == ["reader resume offset started at the beginning of the sentence"]


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


def test_track_reconfigure_accepts_current_sentence_preservation(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670002.000 [PlaybackTransport] Interactive track reconfigure mode=singleTrack(translation) sentence=41 sequenceActive=false requested=true playing=true
1782670003.000 [PlaybackTransport] Interactive track reconfigure mode=sequence sentence=41 sequenceActive=false requested=true playing=true
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="track-reconfigure") == []


def test_track_reconfigure_rejects_lost_active_sentence(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670002.000 [PlaybackTransport] Interactive track reconfigure mode=sequence sentence=-1 sequenceActive=false requested=true playing=true
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="track-reconfigure")

    assert missing == ["active track reconfigure lost the current sentence position"]


def test_track_reconfigure_rejects_active_reset_to_first_sentence(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670002.000 [PlaybackTransport] Interactive track reconfigure mode=singleTrack(translation) sentence=41 sequenceActive=false requested=true playing=true
1782670003.000 [PlaybackTransport] Interactive track reconfigure mode=sequence sentence=0 sequenceActive=false requested=true playing=true
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="track-reconfigure")

    assert missing == [
        "active track reconfigure reset to the first sentence after playback had progressed"
    ]


def test_track_reconfigure_allows_initial_first_sentence(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        """
1782670002.000 [PlaybackTransport] Interactive track reconfigure mode=sequence sentence=0 sequenceActive=false requested=true playing=true
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="track-reconfigure") == []


def test_track_reconfigure_requires_reconfigure_evidence(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_RESUME_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="track-reconfigure")

    assert missing == ["interactive track reconfigure captured position"]


def test_pause_release_accepts_music_pause_adoption_when_narration_mirrors_same_episode(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(MUSIC_ADOPTION_PAUSE_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-release") == []


def test_pause_release_rejects_split_pause_that_only_reaches_narration_on_second_click(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(SPLIT_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert missing == [
        "pause episode 1 did not reach narration before the next transport command",
        "pause episode 2 did not confirm narration stopped before the next transport command",
    ]


def test_pause_release_rejects_first_episode_with_only_reader_pause_flag(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(WEAK_FIRST_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert missing == [
        "pause episode 1 did not reach narration before the next transport command",
        "pause episode 2 did not confirm narration stopped before the next transport command",
    ]


def test_pause_release_rejects_unsettled_first_pause_episode(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(UNSETTLED_FIRST_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert missing == ["pause episode 1 did not confirm narration stopped before the next transport command"]


def test_pause_resume_rejects_later_unsettled_pause_episode(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_RESUME_LOG
        + """
1782670002.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670002.050 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=true systemMusicPlaying=false
1782670002.060 [PlaybackTransport] Library pause command accepted requested=true playing=true musicPlaying=true
1782670003.000 [PlaybackTransport] Library forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670003.010 [PlaybackTransport] Library restoring narration playback request source=brokerResume sentence=42
1782670003.020 [PlaybackTransport] Library play command accepted requested=true playing=true musicPlaying=false deferredMusic=true
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "pause episode 2 did not confirm narration stopped before the next transport command"
    ]


def test_pause_resume_requires_explicit_play_evidence(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport accepted explicit play",
        "reader resume reached healthy narration",
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
        "reader resume reached healthy narration",
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
        "reader resume reached healthy narration",
        "pause episode 2 did not confirm narration stopped before the next transport command",
        "reader received consecutive broker pauses without an intervening reader play",
    ]


def test_pause_resume_rejects_stale_pause_ignore_before_reader_playback_recovers(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_LOG
        + """
1782670001.200 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670001.220 [PlaybackTransport] Library forced play source=brokerResume requested=false playing=false musicPlaying=false systemMusicPlaying=false
1782670001.260 [PlaybackTransport] Library ignored stale adopted Apple Music pause after reader play source=brokerResume
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "reader transport accepted explicit play",
        "reader resume reached healthy narration",
        "stale Apple Music pause was ignored before reader playback recovered",
    ]


def test_pause_resume_rejects_pending_autoplay_music_pause_loop(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_RESUME_LOG
        + """
1782670002.000 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.050 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.100 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.150 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicSurface requested=true playing=true musicPlaying=false readerPause=false
1782670002.160 [PlaybackTransport] Library confirmed reader pause source=musicSurface requested=false playing=false musicPlaying=false
1782670002.200 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.250 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.300 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.350 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.400 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
""",
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-resume")

    assert missing == [
        "audio-state callback recovered pending interactive autoplay",
        "pending interactive autoplay looped while Music bed reported paused"
    ]


def test_pause_resume_rejects_active_observed_nonplaying_cutting_narration(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG + ACTIVE_OBSERVED_NONPLAYING_CUT_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-resume")

    assert "active Apple Music non-playing adopted while narration was still playing" in missing


def test_pause_release_rejects_active_observed_nonplaying_cutting_narration(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG + ACTIVE_OBSERVED_NONPLAYING_CUT_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert "active Apple Music non-playing adopted while narration was still playing" in missing


def test_pause_resume_rejects_requested_only_broker_pause_before_audio_audible(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG + REQUESTED_ONLY_BROKER_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-resume")

    assert "broker pause stopped requested narration before audio became audible" in missing


def test_pause_release_rejects_requested_only_broker_pause_before_audio_audible(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG + REQUESTED_ONLY_BROKER_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert "broker pause stopped requested narration before audio became audible" in missing


def test_pause_resume_rejects_music_surface_pause_before_audio_audible(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG + REQUESTED_ONLY_MUSIC_SURFACE_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-resume")

    assert "Apple Music surface pause stopped requested narration before audio became audible" in missing


def test_pause_release_rejects_music_surface_pause_before_audio_audible(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG + REQUESTED_ONLY_MUSIC_SURFACE_PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release")

    assert "Apple Music surface pause stopped requested narration before audio became audible" in missing


def test_fresh_only_ignores_stale_baseline_failures(tmp_path: Path) -> None:
    baseline = tmp_path / "playback.previous.log"
    log = tmp_path / "playback.log"
    stale_failure = (
        PAUSE_RESUME_LOG
        + """
1782670002.000 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.050 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.100 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.150 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicSurface requested=true playing=true musicPlaying=false readerPause=false
1782670002.160 [PlaybackTransport] Library confirmed reader pause source=musicSurface requested=false playing=false musicPlaying=false
1782670002.200 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.250 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.300 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.350 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
1782670002.400 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAudioState sentence=42
"""
    )
    baseline.write_text(stale_failure, encoding="utf-8")
    log.write_text(stale_failure + PAUSE_RESUME_LOG, encoding="utf-8")

    assert module.validate_log(log, mode="pause-resume") == [
        "audio-state callback recovered pending interactive autoplay",
        "pending interactive autoplay looped while Music bed reported paused"
    ]
    assert module.validate_log(
        log,
        mode="pause-resume",
        fresh_only=True,
        baseline_path=baseline,
    ) == []


def test_pause_resume_rejects_job_audio_state_autoplay_music_pause_loop(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_RESUME_LOG
        + """
1782670002.000 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.050 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.100 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.150 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.200 [PlaybackTransport] Job accepted Apple Music pause as reader transport source=musicSurface requested=true playing=true musicPlaying=false readerPause=false
1782670002.210 [PlaybackTransport] Job confirmed reader pause source=musicSurface requested=false playing=false musicPlaying=false
1782670002.250 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.300 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.350 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.400 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-resume") == [
        "audio-state callback recovered pending interactive autoplay",
        "pending interactive autoplay looped while Music bed reported paused"
    ]


def test_pause_resume_rejects_single_audio_state_autoplay_recovery(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_RESUME_LOG
        + """
1782670002.000 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-resume") == [
        "audio-state callback recovered pending interactive autoplay"
    ]


def test_pause_resume_allows_single_pending_autoplay_recovery(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        PAUSE_RESUME_LOG
        + """
1782670002.000 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryWatchdog sentence=42
1782670002.150 [PlaybackTransport] Library accepted Apple Music pause as reader transport source=musicSurface requested=true playing=true musicPlaying=false readerPause=false
1782670002.160 [PlaybackTransport] Library confirmed reader pause source=musicSurface requested=false playing=false musicPlaying=false
1782670004.200 [PlaybackTransport] Library recovering pending interactive autoplay reason=libraryAutoplayRetry sentence=43
""",
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-resume") == []


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


def test_diagnostic_hint_treats_build_header_as_not_enough_transport_evidence() -> None:
    missing = ["reader transport accepted pause"]

    hints = module.diagnostic_hints(
        "1782670000.000 [PlaybackTransportBuild] release=2026.07.03.001 marketing=2026.7.3 bundle=20260703001 branch=main commit=482baa85d000\n",
        mode="pause-release",
        missing=missing,
    )

    assert hints == [
        "log has no playback transport breadcrumbs; reproduce in a DEBUG Apple build, "
        "then run make apple-device-pull-and-verify-playback-transport-log without relaunching"
    ]


def test_diagnostic_hint_explains_sentence_start_resume_offset() -> None:
    missing = ["reader resume offset started at the beginning of the sentence"]

    hints = module.diagnostic_hints(
        RESUME_OFFSET_LOG,
        mode="resume-offset",
        missing=missing,
    )

    assert hints == [
        "resume offset was saved at sentence start; verify the app build ignores zero interactive "
        "resume offsets, then reproduce after the reader has spoken past the first word"
    ]


def test_required_build_commit_accepts_matching_header(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        "1782670000.000 [PlaybackTransportBuild] release=2026.07.03.001 marketing=2026.7.3 bundle=20260703001 branch=main commit=482baa85d000\n"
        + PAUSE_LOG,
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-release", required_commit="482baa85d") == []


def test_required_build_commit_rejects_mismatched_header(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        "1782670000.000 [PlaybackTransportBuild] release=2026.07.03.001 marketing=2026.7.3 bundle=20260703001 branch=main commit=deadbeef0000\n"
        + PAUSE_LOG,
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release", required_commit="482baa85d")

    assert missing == [
        "playback build header commit deadbeef0000 does not match required 482baa85d"
    ]


def test_required_build_commit_reports_missing_header_commit(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release", required_commit="482baa85d")

    assert missing == ["playback build header commit missing"]


def test_required_build_release_accepts_matching_header(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        "1782670000.000 [PlaybackTransportBuild] release=2026.07.04.008 marketing=2026.7.4 bundle=20260704008 branch=main commit=unknown\n"
        + PAUSE_LOG,
        encoding="utf-8",
    )

    assert module.validate_log(log, mode="pause-release", required_release="2026.07.04.008") == []


def test_required_build_release_rejects_stale_header(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(
        "1782670000.000 [PlaybackTransportBuild] release=2026.07.03.001 marketing=2026.7.3 bundle=20260703001 branch=unknown commit=unknown\n"
        + PAUSE_LOG,
        encoding="utf-8",
    )

    missing = module.validate_log(log, mode="pause-release", required_release="2026.07.04.008")

    assert missing == [
        "playback build header release 2026.07.03.001 does not match required 2026.07.04.008"
    ]


def test_required_build_release_reports_missing_header_release(tmp_path: Path) -> None:
    log = tmp_path / "playback.log"
    log.write_text(PAUSE_LOG, encoding="utf-8")

    missing = module.validate_log(log, mode="pause-release", required_release="2026.07.04.008")

    assert missing == ["playback build header release missing"]


def test_diagnostic_hint_stays_quiet_for_specific_playback_transport_gaps() -> None:
    missing = ["reader transport accepted explicit play"]

    hints = module.diagnostic_hints(PAUSE_LOG, mode="pause-resume", missing=missing)

    assert hints == []


def test_diagnostic_hint_explains_autoplay_recovery_loop() -> None:
    missing = ["pending interactive autoplay looped while Music bed reported paused"]

    hints = module.diagnostic_hints(
        PAUSE_RESUME_LOG
        + """
1782670002.000 [PlaybackTransport] Job recovering pending interactive autoplay reason=jobAudioState sentence=2657
1782670002.150 [PlaybackTransport] Job accepted Apple Music pause as reader transport source=musicSurface requested=true playing=true musicPlaying=false readerPause=false
""",
        mode="pause-resume",
        missing=missing,
    )

    assert hints == [
        "autoplay recovery loop detected; confirm the device is running a build where "
        "Job/Library audio-state callbacks do not call pending-autoplay recovery, then "
        "pull a fresh-only log after reproducing once"
    ]


def test_diagnostic_hint_explains_stale_device_release() -> None:
    missing = [
        "playback build header release 2026.07.03.001 does not match required 2026.07.04.008"
    ]

    hints = module.diagnostic_hints(
        "1782670000.000 [PlaybackTransportBuild] release=2026.07.03.001 marketing=2026.7.3 bundle=20260703001 branch=unknown commit=unknown\n"
        + PAUSE_LOG,
        mode="pause-release",
        missing=missing,
    )

    assert hints == [
        "device playback log came from an older app release; deploy the current Apple build "
        "before treating playback breadcrumbs as evidence for the latest source"
    ]


def test_diagnostic_hint_explains_consecutive_broker_pause_regression() -> None:
    missing = ["reader received consecutive broker pauses without an intervening reader play"]

    hints = module.diagnostic_hints(
        PAUSE_LOG
        + """
1782670010.000 [PlaybackTransport] Library broker tvOS Play/Pause command
1782670010.020 [PlaybackTransport] Library forced pause source=brokerPause requested=true playing=true musicPlaying=true systemMusicPlaying=false
""",
        mode="pause-resume",
        missing=missing,
    )

    assert hints == [
        "consecutive broker pauses detected; inspect whether stale Apple Music state "
        "made the second remote press resolve as pause instead of resume"
    ]


def test_default_log_path_matches_pull_helper() -> None:
    assert module.default_log_path("Living Room") == (
        module.REPO_ROOT / "test-results" / "apple-device-playback-transport-Living-Room.log"
    )


def test_default_baseline_log_path_matches_pull_helper() -> None:
    log = module.REPO_ROOT / "test-results" / "apple-device-playback-transport-Living-Room.log"

    assert module.default_baseline_log_path(log) == (
        module.REPO_ROOT / "test-results" / "apple-device-playback-transport-Living-Room.previous.log"
    )
