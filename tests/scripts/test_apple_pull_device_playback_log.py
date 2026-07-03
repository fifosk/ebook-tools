from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apple_pull_device_playback_log.sh"
MAKEFILE = ROOT / "Makefile"
APP = ROOT / "ios" / "InteractiveReader" / "InteractiveReader"
XCODE_PROJECT = ROOT / "ios" / "InteractiveReader" / "InteractiveReader.xcodeproj" / "project.pbxproj"


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
    assert "APPLE_DEVICE_LOG_TIMESTAMP" in script
    assert "APPLE_DEVICE_PLAYBACK_BASELINE_LOG" in script
    assert 'BASELINE_PATH="${OUTPUT_PATH%.log}.previous.log"' in script
    assert 'cp "${OUTPUT_PATH}" "${BASELINE_PATH}"' in script
    assert "Playback transport baseline log:" in script
    assert 'LOG_ARCHIVE="${OUTPUT_PATH%.log}-${LOG_TIMESTAMP}.log"' in script
    assert 'COREDEVICE_LOG_ARCHIVE="${OUTPUT_PATH%.log}-${LOG_TIMESTAMP}.coredevice.log"' in script
    assert 'cp "${OUTPUT_PATH}" "${LOG_ARCHIVE}"' in script
    assert 'Playback transport log archive: ${LOG_ARCHIVE}' in script
    assert "Playback transport CoreDevice archive:" in script
    assert "not book text or media titles" in script


def test_makefile_exposes_playback_log_pull_target() -> None:
    makefile = _source(MAKEFILE)

    assert "apple-device-pull-playback-log" in makefile
    assert "apple-device-pull-and-verify-playback-transport-log" in makefile
    assert "apple-device-pull-and-verify-playback-transport-pause-resume-log" in makefile
    assert "apple-device-pull-and-verify-playback-resume-offset-log" in makefile
    assert "apple-device-verify-playback-transport-log" in makefile
    assert "apple-device-verify-playback-transport-pause-resume-log" in makefile
    assert "apple-device-verify-playback-resume-offset-log" in makefile
    assert "APPLE_DEVICE_PLAYBACK_LOG ?=" in makefile
    assert "APPLE_DEVICE_PLAYBACK_BASELINE_LOG ?=" in makefile
    assert "APPLE_PLAYBACK_TRANSPORT_FRESH_ONLY ?= 0" in makefile
    assert "APPLE_PLAYBACK_TRANSPORT_LOG_MODE ?= pause-release" in makefile
    assert "APPLE_PLAYBACK_TRANSPORT_REQUIRED_COMMIT ?=" in makefile
    assert "APPLE_PLAYBACK_TRANSPORT_CURRENT_COMMIT ?= $(shell git rev-parse --short=12 HEAD" in makefile
    assert "scripts/apple_pull_device_playback_log.sh" in makefile
    assert "scripts/check_apple_playback_transport_log.py" in makefile
    assert '--output "$(APPLE_DEVICE_PLAYBACK_LOG)"' in makefile
    assert '--baseline-output "$(APPLE_DEVICE_PLAYBACK_BASELINE_LOG)"' in makefile
    assert "APPLE_PLAYBACK_TRANSPORT_FRESH_ONLY=1" in makefile
    assert "--fresh-only" in makefile
    assert '--require-commit "$(APPLE_PLAYBACK_TRANSPORT_REQUIRED_COMMIT)"' in makefile
    assert '--baseline-log "$(APPLE_DEVICE_PLAYBACK_BASELINE_LOG)"' in makefile
    assert "$(MAKE) apple-device-pull-playback-log" in makefile
    assert "$(MAKE) apple-device-verify-playback-transport-log" in makefile
    assert "apple-device-pull-and-verify-current-playback-transport-log" in makefile
    assert 'APPLE_PLAYBACK_TRANSPORT_REQUIRED_COMMIT="$(APPLE_PLAYBACK_TRANSPORT_CURRENT_COMMIT)"' in makefile
    assert "apple-device-pull-and-verify-current-reader-repro-log" in makefile
    phony = makefile.split(".PHONY:", 1)[1].split("\n\n", 1)[0]
    assert "apple-device-pull-and-verify-current-playback-transport-log" in phony
    assert "apple-device-pull-and-verify-current-playback-transport-pause-resume-log" in phony
    assert "apple-device-pull-and-verify-current-playback-resume-offset-log" in phony
    assert "apple-device-pull-and-verify-current-reader-repro-log" in phony
    assert "$(MAKE) apple-device-verify-playback-transport-pause-resume-log APPLE_PLAYBACK_TRANSPORT_FRESH_ONLY=1" in makefile
    assert "$(MAKE) apple-device-verify-playback-resume-offset-log APPLE_PLAYBACK_TRANSPORT_FRESH_ONLY=1" in makefile
    assert (
        "$(MAKE) apple-device-pull-and-verify-playback-transport-log "
        "APPLE_PLAYBACK_TRANSPORT_LOG_MODE=pause-resume"
    ) in makefile
    assert (
        "$(MAKE) apple-device-pull-and-verify-playback-transport-log "
        "APPLE_PLAYBACK_TRANSPORT_LOG_MODE=resume-offset"
    ) in makefile


def test_debug_playback_transport_file_logger_is_token_safe_and_reused_by_players() -> None:
    shortcuts = _source(APP / "App" / "GlobalKeyboardShortcuts.swift")
    job = _source(APP / "Features" / "Playback" / "JobPlaybackView.swift")
    job_resume = _source(APP / "Features" / "Playback" / "JobPlaybackView+Resume.swift")
    job_now_playing = _source(APP / "Features" / "Playback" / "JobPlaybackView+NowPlaying.swift")
    library = _source(APP / "Features" / "Playback" / "LibraryPlaybackView.swift")
    library_resume = _source(APP / "Features" / "Playback" / "LibraryPlaybackView+Resume.swift")
    library_now_playing = _source(APP / "Features" / "Playback" / "LibraryPlaybackView+NowPlaying.swift")
    music = _source(APP / "Services" / "MusicKitCoordinator.swift")
    selection = _source(APP / "Features" / "InteractivePlayer" / "InteractivePlayerViewModel+Selection.swift")

    assert "func playbackTransportDebugLog" in shortcuts
    assert "PlaybackTransportDebugLogger" in shortcuts
    assert 'appendingPathComponent("interactive-reader-playback-transport.log")' in shortcuts
    assert "[PlaybackTransportBuild] \\(metadata)" in shortcuts
    assert "release=\\(AppVersion.release)" in shortcuts
    assert "marketing=\\(AppVersion.marketingVersion)" in shortcuts
    assert "bundle=\\(AppVersion.bundleVersion)" in shortcuts
    assert "branch=\\(AppVersion.branch)" in shortcuts
    assert "commit=\\(AppVersion.commit)" in shortcuts
    assert "writeSessionHeaderIfNeeded(fileURL)" in shortcuts
    assert "size.intValue > 512_000" in shortcuts
    assert "Apple Music reader transport pause adopted source=" in music
    assert "playbackTransportDebugLog(" in music

    app_version = _source(APP / "Features" / "Shared" / "AppVersion.swift")
    assert 'readInfoValue("EBOOK_TOOLS_COMMIT")' in app_version
    assert 'readBundleTextResource("commit", fileExtension: "stamp")' in app_version
    assert 'readBundleTextResource("branch", fileExtension: "stamp")' in app_version
    assert 'ProcessInfo.processInfo.environment["EBOOK_TOOLS_COMMIT"]' in app_version

    ios_plist = _source(APP / "Supporting" / "Info.plist")
    tvos_plist = _source(APP / "Supporting" / "Info-tvOS.plist")
    assert "EBOOK_TOOLS_COMMIT" in ios_plist
    assert "EBOOK_TOOLS_COMMIT" in tvos_plist

    for source, label in (
        (job, "Job"),
        (job_resume, "Job resume"),
        (job_now_playing, "Job"),
        (library, "Library"),
        (library_resume, "Library resume"),
        (library_now_playing, "Library"),
        (selection, "Interactive selection"),
    ):
        assert "playbackTransportDebugLog(" in source, label
        assert "[PlaybackTransport]" in source, label
        debug_lines = "\n".join(line for line in source.splitlines() if "playbackTransportDebugLog" in line)
        assert "bookTitle" not in debug_lines, label
        assert "author" not in debug_lines, label

    assert "resume offset requested sentence=" in job_resume
    assert "resume offset requested sentence=" in library_resume
    assert "Interactive sequence time seek accepted sentence=" in selection
    assert "Interactive time seek accepted sequence=false sentence=" in selection


def test_git_build_metadata_phase_refreshes_stamp_files_every_build() -> None:
    project = _source(XCODE_PROJECT)

    for phase_name in ("Set Git Build Metadata", "Set Git Build Metadata (tvOS)"):
        phase_start = project.index(f"/* {phase_name} */")
        phase_body = project[phase_start : project.index("};", phase_start)]
        output_paths = phase_body.split("outputPaths = (", 1)[1].split(");", 1)[0]

        assert "alwaysOutOfDate = 1;" in phase_body
        assert "branch.stamp" in output_paths
        assert "commit.stamp" in output_paths
        assert 'echo \\"${BRANCH}\\" > \\"${STAMP_DIR}/branch.stamp\\"' in phase_body
        assert 'echo \\"${COMMIT}\\" > \\"${STAMP_DIR}/commit.stamp\\"' in phase_body
