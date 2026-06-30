from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apple_pull_device_playback_log.sh"
MAKEFILE = ROOT / "Makefile"
APP = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pull_helper_reads_debug_playback_transport_cache_from_app_container() -> None:
    script = _source(SCRIPT)

    assert "interactive-reader-playback-transport.log" in script
    assert "--domain-type appDataContainer" in script
    assert '--domain-identifier "${BUNDLE_ID}"' in script
    assert 'BUNDLE_ID="com.example.InteractiveReader.tvos"' in script
    assert 'BUNDLE_ID="com.example.InteractiveReader"' in script
    assert "apple-device-playback-transport-${safe_device}.log" in script
    assert "not book text or media titles" in script


def test_makefile_exposes_playback_log_pull_target() -> None:
    makefile = _source(MAKEFILE)

    assert "apple-device-pull-playback-log" in makefile
    assert "apple-device-verify-playback-transport-log" in makefile
    assert "apple-device-verify-playback-transport-pause-resume-log" in makefile
    assert "APPLE_DEVICE_PLAYBACK_LOG ?=" in makefile
    assert "APPLE_PLAYBACK_TRANSPORT_LOG_MODE ?= pause-release" in makefile
    assert "scripts/apple_pull_device_playback_log.sh" in makefile
    assert "scripts/check_apple_playback_transport_log.py" in makefile
    assert '--output "$(APPLE_DEVICE_PLAYBACK_LOG)"' in makefile


def test_debug_playback_transport_file_logger_is_token_safe_and_reused_by_players() -> None:
    shortcuts = _source(APP / "App" / "GlobalKeyboardShortcuts.swift")
    job = _source(APP / "Features" / "Playback" / "JobPlaybackView.swift")
    job_now_playing = _source(APP / "Features" / "Playback" / "JobPlaybackView+NowPlaying.swift")
    library = _source(APP / "Features" / "Playback" / "LibraryPlaybackView.swift")
    library_now_playing = _source(APP / "Features" / "Playback" / "LibraryPlaybackView+NowPlaying.swift")

    assert "func playbackTransportDebugLog" in shortcuts
    assert "PlaybackTransportDebugLogger" in shortcuts
    assert 'appendingPathComponent("interactive-reader-playback-transport.log")' in shortcuts
    assert "size.intValue > 512_000" in shortcuts

    for source, label in (
        (job, "Job"),
        (job_now_playing, "Job"),
        (library, "Library"),
        (library_now_playing, "Library"),
    ):
        assert "playbackTransportDebugLog(" in source, label
        assert "[PlaybackTransport]" in source, label
        debug_lines = "\n".join(line for line in source.splitlines() if "playbackTransportDebugLog" in line)
        assert "bookTitle" not in debug_lines, label
        assert "author" not in debug_lines, label
