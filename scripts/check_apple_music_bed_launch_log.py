#!/usr/bin/env python3
"""Validate token-safe Apple Music reading-bed launch-console breadcrumbs."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


STARTUP_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "MusicKit entered Apple Music bed ownership",
        (
            r"Apple Music reading bed ownership=appleMusicBed",
            r"ownership=appleMusicBed",
        ),
    ),
    (
        "reader attached the sentence AVPlayer to Now Playing",
        (
            r"Reader NowPlaying session attached player=true",
        ),
    ),
    (
        "reader Now Playing session became active",
        (
            r"Reader NowPlaying session active=true canBecomeActive=true",
        ),
    ),
    (
        "reader remote commands are enabled",
        (
            r"Reader NowPlaying remoteCommandsEnabled=true",
        ),
    ),
    (
        "reader transport metadata was published",
        (
            r"Reader NowPlaying transport=(?:playing|paused).*playbackRate=",
        ),
    ),
    (
        "reader Now Playing session was reasserted",
        (
            r"Reader NowPlaying session reassert requested",
        ),
    ),
)


PAUSE_RELEASE_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "tvOS remote Play/Pause reached the app broker",
        (
            r"tvOS remote playPause forwarded to player broker",
        ),
    ),
    (
        "fullscreen Music artwork suppression was enabled",
        (
            r"Apple Music fullscreen artwork suppression=true",
            r"fullscreen=blocked",
        ),
    ),
    (
        "fullscreen Music artwork suppression watchdog started",
        (
            r"Apple Music fullscreen artwork suppression watchdog started",
        ),
    ),
    (
        "fullscreen Music artwork suppression was reasserted",
        (
            r"Apple Music fullscreen artwork suppression reasserted",
        ),
    ),
    (
        "reader-owned Music pause was observed",
        (
            r"Apple Music reader transport pause adopted",
            r"Apple Music reader transport pause requested",
        ),
    ),
    (
        "reader transport used the reader-owned pause route",
        (
            r"(?:Job|Library) reader transport forced pause source=",
            r"Apple Music reader transport pause adopted source=observed non-playing reason=observedNonPlaying",
        ),
    ),
    (
        "sentence narration mirrored the reader-owned Music pause",
        (
            r"(?:Job|Library) playback accepted Apple Music pause as reader transport source=(?:musicAdoption|musicSurface|watchdog)",
            r"(?:Job|Library) playback mirroring adopted Apple Music pause to narration",
            r"(?:Job|Library) reader transport forced pause source=",
        ),
    ),
    (
        "tvOS Music playback surface was suppressed without stealing reader transport",
        (
            r"Apple Music reader transport kept tvOS playback surface suppressed",
            r"fullscreen=blocked",
        ),
    ),
)


GUARDED_PLAY_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "stray Now Playing play callback was ignored during reader pause guard",
        (
            r"reader transport play command ignored reader-pause-guard",
            r"reader-pause-guard",
        ),
    ),
)


PAUSE_RESUME_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "reader transport accepted an explicit resume command",
        (
            r"(?:Job|Library) reader transport play command requested=",
            r"(?:Job|Library) reader transport forced play source=",
        ),
    ),
    (
        "Apple Music bed resumed under reader ownership",
        (
            r"Apple Music playback surface changed reason=resume",
            r"Apple Music observed reader transport resume from system playback",
            r"Apple Music E2E simulated bed play",
            r"music=playing",
        ),
    ),
)


PLAYBACK_BREADCRUMB_PATTERNS: tuple[str, ...] = (
    r"Reader NowPlaying",
    r"Apple Music reading bed ownership=",
    r"Apple Music reader transport",
    r"(?:Job|Library) playback accepted Apple Music pause as reader transport",
    r"(?:Job|Library) reader transport",
)


def _safe_device_id(device: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", device).strip("-") or "device"


def default_log_path(device: str | None) -> Path:
    env_path = os.environ.get("APPLE_DEVICE_LAUNCH_LOG", "").strip()
    if env_path:
        return Path(env_path)
    if not device:
        raise SystemExit(
            "Provide a launch log path, APPLE_DEVICE_LAUNCH_LOG, or --device/APPLE_DEVICE_ID "
            "so the default test-results log can be resolved."
        )
    return REPO_ROOT / "test-results" / f"apple-device-launch-console-{_safe_device_id(device)}.log"


def _missing_requirements(text: str, requirements: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    missing: list[str] = []
    for label, patterns in requirements:
        if not any(re.search(pattern, text, flags=re.MULTILINE) for pattern in patterns):
            missing.append(label)
    return missing


def _pause_guard_violations(text: str) -> list[str]:
    pause_match = re.search(
        r"(?:Apple Music reader transport pause adopted|(?:Job|Library) reader transport forced pause source=)",
        text,
        flags=re.MULTILINE,
    )
    if not pause_match:
        return []

    play_match = re.search(
        r"(?:Job|Library) reader transport play command requested=",
        text[pause_match.end() :],
        flags=re.MULTILINE,
    )
    guarded_window_end = pause_match.end() + play_match.start() if play_match else len(text)
    guarded_window = text[pause_match.end() : guarded_window_end]
    forbidden_patterns = (
        r"Apple Music observed reader transport resume from system playback",
        r"(?:Job|Library) playback mirroring Apple Music play to narration",
        r"(?:Job|Library) reader transport forced play source=(?:foregroundHardwareResume|brokerHardwareResume|brokerResume)",
        r"(?:Job|Library) reader transport in-place recovery requested=",
        r"(?:Job|Library) reader transport recovery requested=",
        r"(?:Job|Library) reader transport deferred Music resume held",
        r"Apple Music playback surface changed reason=resume",
    )
    if any(re.search(pattern, guarded_window, flags=re.MULTILINE) for pattern in forbidden_patterns):
        return ["reader transport pause was followed by a system-driven resume before explicit reader play"]
    return []


def diagnostic_hints(text: str, *, mode: str, missing: list[str]) -> list[str]:
    if not missing or mode == "startup":
        return []
    if any(re.search(pattern, text, flags=re.MULTILINE) for pattern in PLAYBACK_BREADCRUMB_PATTERNS):
        return []
    return [
        "log has no reader/Music playback breadcrumbs; for an in-progress Apple TV repro, "
        "capture with APPLE_DEVICE_LAUNCH_PRESERVE_RUNNING=1 make apple-device-launch-console "
        "before pressing Play/Pause"
    ]


def validate_log(path: Path, *, mode: str) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return [f"launch log does not exist: {path}"]
    except OSError as exc:
        return [f"launch log could not be read: {exc}"]

    requirements = STARTUP_REQUIREMENTS
    if mode == "pause-release":
        requirements = STARTUP_REQUIREMENTS + PAUSE_RELEASE_REQUIREMENTS
    elif mode == "guarded-play":
        requirements = STARTUP_REQUIREMENTS + PAUSE_RELEASE_REQUIREMENTS + GUARDED_PLAY_REQUIREMENTS
    elif mode == "pause-resume":
        requirements = STARTUP_REQUIREMENTS + PAUSE_RELEASE_REQUIREMENTS + PAUSE_RESUME_REQUIREMENTS
    missing = _missing_requirements(text, requirements)
    if mode in {"pause-release", "guarded-play", "pause-resume"}:
        missing.extend(_pause_guard_violations(text))
    return missing


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", help="Launch-console log path to validate.")
    parser.add_argument(
        "--device",
        default=os.environ.get("APPLE_DEVICE_ID", ""),
        help="Device id/name used to resolve the default launch-console log path.",
    )
    parser.add_argument(
        "--mode",
        choices=("startup", "pause-release", "guarded-play", "pause-resume"),
        default=os.environ.get("APPLE_MUSIC_BED_LAUNCH_LOG_MODE", "startup"),
        help=(
            "Validation mode. startup checks ownership breadcrumbs; pause-release also checks "
            "reader-owned pause/release breadcrumbs; guarded-play additionally requires evidence "
            "that a stray Now Playing play callback was ignored during the reader pause guard; "
            "pause-resume requires an accepted reader-owned resume after pause-release evidence."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    path = Path(args.log) if args.log else default_log_path(args.device.strip() or None)
    missing = validate_log(path, mode=args.mode)
    if missing:
        print(f"Apple Music bed launch log validation failed for {path}", file=sys.stderr)
        for label in missing:
            print(f"- missing: {label}", file=sys.stderr)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for hint in diagnostic_hints(text, mode=args.mode, missing=missing):
            print(f"- hint: {hint}", file=sys.stderr)
        return 1
    print(f"Apple Music bed launch log validation passed: {path} mode={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
