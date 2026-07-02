#!/usr/bin/env python3
"""Validate token-safe Apple playback transport breadcrumbs pulled from a device."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


PAUSE_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "tvOS Play/Pause reached reader playback",
        (
            r"\[PlaybackTransport\] Apple Music reader transport pause adopted",
            r"\[PlaybackTransport\] (?:Job|Library) (?:foreground|broker) tvOS Play/Pause command",
            r"\[PlaybackTransport\] (?:Job|Library) forced pause source=",
            r"\[PlaybackTransport\] (?:Job|Library) pause command accepted requested=",
        ),
    ),
    (
        "reader transport accepted pause",
        (
            r"\[PlaybackTransport\] Apple Music reader transport pause adopted",
            r"\[PlaybackTransport\] (?:Job|Library) forced pause source=",
            r"\[PlaybackTransport\] (?:Job|Library) pause command accepted requested=",
            r"\[PlaybackTransport\] (?:Job|Library) accepted Apple Music pause as reader transport source=",
        ),
    ),
    (
        "pause reached narration state",
        (
            r"\[PlaybackTransport\] (?:Job|Library) forced pause source=.*playing=true",
            r"\[PlaybackTransport\] (?:Job|Library) accepted Apple Music pause as reader transport source=.*playing=true",
            r"\[PlaybackTransport\] (?:Job|Library) pause command accepted requested=true",
        ),
    ),
)


RESUME_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "reader transport accepted explicit play",
        (
            r"\[PlaybackTransport\] (?:Job|Library) play command accepted requested=true",
            r"\[PlaybackTransport\] (?:Job|Library) restoring narration playback request source=",
        ),
    ),
    (
        "stale Music pause was ignored or play was accepted cleanly",
        (
            r"\[PlaybackTransport\] (?:Job|Library) ignored stale adopted Apple Music pause after reader play",
            r"\[PlaybackTransport\] (?:Job|Library) play command accepted requested=true",
            r"\[PlaybackTransport\] (?:Job|Library) restoring narration playback request source=",
        ),
    ),
)


RESUME_OFFSET_REQUIREMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "reader requested saved resume offset",
        (
            r"\[PlaybackTransport\] (?:Job|Library) resume offset requested sentence=\d+ time=\d",
            r"\[PlaybackTransport\] (?:Job|Library) resume offset retry sentence=\d+ time=\d",
        ),
    ),
    (
        "reader applied exact resume offset",
        (
            r"\[PlaybackTransport\] Interactive sequence time seek accepted sentence=\d+ time=\d",
            r"\[PlaybackTransport\] Interactive time seek accepted sequence=false sentence=\d+ time=\d",
        ),
    ),
)


DEAD_RESUME_PATTERN = re.compile(
    r"\[PlaybackTransport\] (?:Job|Library) forced play source=(?:brokerResume|interactiveOverride) "
    r"requested=false playing=false musicPlaying=false systemMusicPlaying=false\s*\n"
    r".*?\[PlaybackTransport\] (?:Job|Library) play command accepted "
    r"requested=false playing=false musicPlaying=false",
    flags=re.MULTILINE | re.DOTALL,
)


FORBIDDEN_BEFORE_EXPLICIT_PLAY: tuple[str, ...] = (
    r"\[PlaybackTransport\] (?:Job|Library) forced play source=(?:foregroundHardwareResume|brokerHardwareResume)",
    r"\[PlaybackTransport\] (?:Job|Library) play command accepted requested=",
)


PLAYBACK_TRANSPORT_BREADCRUMB_PATTERNS: tuple[str, ...] = (
    r"\[PlaybackTransport\]",
    r"Apple Music reader transport pause adopted",
    r"(?:Job|Library) (?:foreground|broker) tvOS Play/Pause command",
    r"(?:Job|Library) (?:forced pause|forced play|pause command accepted|play command accepted)",
    r"(?:Job|Library) resume offset (?:requested|retry|fallback)",
    r"Interactive (?:sequence )?time seek",
)


FIRST_PAUSE_EVENT_PATTERN = re.compile(
    r"\[PlaybackTransport\] (?:"
    r"Apple Music reader transport pause adopted|"
    r"(?:Job|Library) (?:foreground|broker) tvOS Play/Pause command|"
    r"(?:Job|Library) forced pause source=|"
    r"(?:Job|Library) pause command accepted|"
    r"(?:Job|Library) accepted Apple Music pause as reader transport"
    r")"
)


NEXT_TRANSPORT_EVENT_PATTERN = re.compile(
    r"\[PlaybackTransport\] (?:"
    r"(?:Job|Library) (?:foreground|broker) tvOS Play/Pause command|"
    r"(?:Job|Library) forced play source=|"
    r"(?:Job|Library) play command accepted"
    r")"
)


NARRATION_PAUSE_EVIDENCE_PATTERN = re.compile(
    r"\[PlaybackTransport\] (?:"
    r"(?:Job|Library) forced pause source=.*(?:requested=true|playing=true)|"
    r"(?:Job|Library) pause command accepted requested=true|"
    r"(?:Job|Library) accepted Apple Music pause as reader transport source=.*(?:requested=true|playing=true)|"
    r"(?:Job|Library) mirroring adopted Apple Music pause requested=.*(?:requested=true|playing=true)"
    r")",
    flags=re.MULTILINE,
)


TRANSPORT_EVENT_LINE_PATTERN = re.compile(
    r"^(?P<time>\d+(?:\.\d+)?) \[PlaybackTransport\] (?P<surface>Job|Library) (?P<event>.+)$"
)


RESUME_OFFSET_REQUEST_LINE_PATTERN = re.compile(
    r"^\d+(?:\.\d+)? \[PlaybackTransport\] (?P<surface>Job|Library) resume offset "
    r"(?P<kind>requested|retry) sentence=(?P<sentence>\d+) time=(?P<time>\d+(?:\.\d+)?) "
    r"sequence=true"
)


SEQUENCE_TIME_SEEK_ACCEPTED_LINE_PATTERN = re.compile(
    r"^\d+(?:\.\d+)? \[PlaybackTransport\] Interactive sequence time seek accepted "
    r"sentence=(?P<sentence>\d+) time=(?P<time>\d+(?:\.\d+)?) track=(?P<track>original|translation)"
)


def _safe_device_id(device: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", device).strip("-") or "device"


def default_log_path(device: str | None) -> Path:
    env_path = os.environ.get("APPLE_DEVICE_PLAYBACK_LOG", "").strip()
    if env_path:
        return Path(env_path)
    if not device:
        raise SystemExit(
            "Provide a playback transport log path, APPLE_DEVICE_PLAYBACK_LOG, "
            "or --device/APPLE_DEVICE_ID so the default test-results log can be resolved."
        )
    return REPO_ROOT / "test-results" / f"apple-device-playback-transport-{_safe_device_id(device)}.log"


def _missing_requirements(text: str, requirements: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    missing: list[str] = []
    for label, patterns in requirements:
        if not any(re.search(pattern, text, flags=re.MULTILINE) for pattern in patterns):
            missing.append(label)
    return missing


def _pause_guard_violations(text: str) -> list[str]:
    pause_match = re.search(
        r"\[PlaybackTransport\] (?:Job|Library) (?:forced pause source=|pause command accepted|accepted Apple Music pause as reader transport)",
        text,
        flags=re.MULTILINE,
    )
    if not pause_match:
        return []
    play_match = re.search(
        r"\[PlaybackTransport\] (?:Job|Library) play command accepted",
        text[pause_match.end() :],
        flags=re.MULTILINE,
    )
    guarded_window_end = pause_match.end() + play_match.start() if play_match else len(text)
    guarded_window = text[pause_match.end() : guarded_window_end]
    if any(re.search(pattern, guarded_window, flags=re.MULTILINE) for pattern in FORBIDDEN_BEFORE_EXPLICIT_PLAY):
        return ["reader pause was followed by a playback resume before explicit reader play"]
    return []


def _first_pause_episode_violations(text: str) -> list[str]:
    lines = text.splitlines()
    first_index: int | None = None
    for index, line in enumerate(lines):
        if FIRST_PAUSE_EVENT_PATTERN.search(line):
            first_index = index
            break
    if first_index is None:
        return []

    end_index = len(lines)
    for index in range(first_index + 1, len(lines)):
        if NEXT_TRANSPORT_EVENT_PATTERN.search(lines[index]):
            end_index = index
            break

    first_episode = "\n".join(lines[first_index:end_index])
    if NARRATION_PAUSE_EVIDENCE_PATTERN.search(first_episode):
        return []
    return ["first pause episode did not reach narration before the next transport command"]


def _dead_resume_violations(text: str) -> list[str]:
    for match in DEAD_RESUME_PATTERN.finditer(text):
        episode = match.group(0)
        if re.search(
            r"\[PlaybackTransport\] (?:Job|Library) restoring narration playback request source=",
            episode,
            flags=re.MULTILINE,
        ):
            continue
        later_text = text[match.end() :]
        if re.search(
            r"\[PlaybackTransport\] (?:Job|Library) restoring narration playback request source=.*\n"
            r".*?\[PlaybackTransport\] (?:Job|Library) play command accepted requested=true",
            later_text,
            flags=re.MULTILINE | re.DOTALL,
        ):
            continue
        return ["reader resume accepted without restoring narration playback request"]
    return []


def _consecutive_broker_pause_violations(text: str) -> list[str]:
    last_pause_without_play: tuple[str, float] | None = None
    for line in text.splitlines():
        match = TRANSPORT_EVENT_LINE_PATTERN.match(line)
        if not match:
            continue
        timestamp = float(match.group("time"))
        surface = match.group("surface")
        event = match.group("event")
        if (
            "forced play source=brokerResume" in event
            or "play command accepted requested=true" in event
            or "restoring narration playback request source=" in event
        ):
            last_pause_without_play = None
            continue
        if "forced pause source=brokerPause" not in event:
            continue
        if last_pause_without_play and last_pause_without_play[0] == surface:
            elapsed = timestamp - last_pause_without_play[1]
            if elapsed > 1.5:
                return [
                    "reader received consecutive broker pauses without an intervening reader play"
                ]
        last_pause_without_play = (surface, timestamp)
    return []


def _resume_offset_violations(text: str) -> list[str]:
    violations: list[str] = []
    if re.search(
        r"\[PlaybackTransport\] (?:Job|Library) resume offset fallback=sentenceStart",
        text,
        flags=re.MULTILINE,
    ):
        violations.append("reader resume offset fell back to the beginning of the sentence")
    if re.search(
        r"\[PlaybackTransport\] Interactive sequence time seek fallback=sentenceStart",
        text,
        flags=re.MULTILINE,
    ):
        violations.append("sequence resume offset fell back to the beginning of the sentence")
    if re.search(
        r"\[PlaybackTransport\] Interactive sequence time seek failed",
        text,
        flags=re.MULTILINE,
    ):
        violations.append("sequence resume offset could not be applied")
    violations.extend(_resume_retry_track_flip_violations(text))
    return violations


def _resume_retry_track_flip_violations(text: str) -> list[str]:
    pending: tuple[str, str, str, str] | None = None
    first_accepts: dict[tuple[str, str, str], str] = {}
    for line in text.splitlines():
        request_match = RESUME_OFFSET_REQUEST_LINE_PATTERN.match(line)
        if request_match:
            pending = (
                request_match.group("surface"),
                request_match.group("kind"),
                request_match.group("sentence"),
                request_match.group("time"),
            )
            continue
        accepted_match = SEQUENCE_TIME_SEEK_ACCEPTED_LINE_PATTERN.match(line)
        if not accepted_match or pending is None:
            continue
        surface, kind, sentence, requested_time = pending
        accepted_sentence = accepted_match.group("sentence")
        accepted_time = accepted_match.group("time")
        if accepted_sentence != sentence or accepted_time != requested_time:
            continue
        track = accepted_match.group("track")
        key = (surface, sentence, requested_time)
        if kind == "requested":
            first_accepts.setdefault(key, track)
        elif kind == "retry":
            first_track = first_accepts.get(key)
            if first_track is not None and first_track != track:
                return [
                    "sequence resume retry changed track "
                    f"from {first_track} to {track} for sentence {sentence}"
                ]
        pending = None
    return []


def validate_log(path: Path, *, mode: str) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return [f"playback transport log does not exist: {path}"]
    except OSError as exc:
        return [f"playback transport log could not be read: {exc}"]

    requirements = PAUSE_REQUIREMENTS
    if mode == "pause-resume":
        requirements = PAUSE_REQUIREMENTS + RESUME_REQUIREMENTS
    elif mode == "resume-offset":
        requirements = RESUME_OFFSET_REQUIREMENTS
    missing = _missing_requirements(text, requirements)
    if mode != "resume-offset":
        missing.extend(_pause_guard_violations(text))
        missing.extend(_first_pause_episode_violations(text))
    if mode == "pause-resume":
        missing.extend(_dead_resume_violations(text))
        missing.extend(_consecutive_broker_pause_violations(text))
    elif mode == "resume-offset":
        missing.extend(_resume_offset_violations(text))
    return missing


def diagnostic_hints(text: str, *, mode: str, missing: list[str]) -> list[str]:
    if not missing:
        return []
    if any(re.search(pattern, text, flags=re.MULTILINE) for pattern in PLAYBACK_TRANSPORT_BREADCRUMB_PATTERNS):
        return []
    return [
        "log has no playback transport breadcrumbs; reproduce in a DEBUG Apple build, "
        "then run make apple-device-pull-and-verify-playback-transport-log without relaunching"
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", help="Pulled playback transport log path to validate.")
    parser.add_argument(
        "--device",
        default=os.environ.get("APPLE_DEVICE_ID", ""),
        help="Device id/name used to resolve the default playback transport log path.",
    )
    parser.add_argument(
        "--mode",
        choices=("pause-release", "pause-resume", "resume-offset"),
        default=os.environ.get("APPLE_PLAYBACK_TRANSPORT_LOG_MODE", "pause-release"),
        help=(
            "pause-release checks the reader-owned pause route; pause-resume also checks explicit resume; "
            "resume-offset checks saved in-sentence resume offsets."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    path = Path(args.log) if args.log else default_log_path(args.device.strip() or None)
    missing = validate_log(path, mode=args.mode)
    if missing:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        print(f"Apple playback transport log validation failed for {path}", file=sys.stderr)
        for label in missing:
            print(f"- missing: {label}", file=sys.stderr)
        for hint in diagnostic_hints(text, mode=args.mode, missing=missing):
            print(f"- hint: {hint}", file=sys.stderr)
        return 1
    print(f"Apple playback transport log validation passed: {path} mode={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
