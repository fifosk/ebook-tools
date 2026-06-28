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
            r"Apple Music observed non-playing confirmed; marking reader transport paused",
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
    return _missing_requirements(text, requirements)


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
        choices=("startup", "pause-release", "guarded-play"),
        default=os.environ.get("APPLE_MUSIC_BED_LAUNCH_LOG_MODE", "startup"),
        help=(
            "Validation mode. startup checks ownership breadcrumbs; pause-release also checks "
            "reader-owned pause/release breadcrumbs; guarded-play additionally requires evidence "
            "that a stray Now Playing play callback was ignored during the reader pause guard."
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
        return 1
    print(f"Apple Music bed launch log validation passed: {path} mode={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
