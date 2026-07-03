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
        "reader resume reached healthy narration",
        (
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


NARRATION_PAUSE_SETTLED_PATTERN = re.compile(
    r"\[PlaybackTransport\] (?:"
    r"(?:Job|Library) confirmed reader pause source=.*requested=false playing=false|"
    r"(?:Job|Library) accepted Apple Music pause as reader transport source=.*requested=false playing=false|"
    r"(?:Job|Library) mirroring adopted Apple Music pause requested=false playing=false"
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


AUTOPLAY_RECOVERY_LINE_PATTERN = re.compile(
    r"^(?P<time>\d+(?:\.\d+)?) \[PlaybackTransport\] (?P<surface>Job|Library) "
    r"recovering pending interactive autoplay .* sentence=(?P<sentence>\d+)"
)

PLAYBACK_BUILD_HEADER_PATTERN = re.compile(
    r"^\d+(?:\.\d+)? \[PlaybackTransportBuild\] (?P<metadata>.+)$",
    flags=re.MULTILINE,
)

PLAYBACK_BUILD_COMMIT_PATTERN = re.compile(r"(?:^|\s)commit=(?P<commit>[A-Za-z0-9._-]+)(?:\s|$)")


MUSIC_SURFACE_PAUSE_LINE_PATTERN = re.compile(
    r"^(?P<time>\d+(?:\.\d+)?) \[PlaybackTransport\] (?P<surface>Job|Library) "
    r"accepted Apple Music pause as reader transport source=musicSurface "
    r"requested=true playing=true musicPlaying=false"
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


def default_baseline_log_path(path: Path) -> Path:
    if path.suffix == ".log":
        return path.with_name(f"{path.stem}.previous.log")
    return path.with_name(f"{path.name}.previous")


def _fresh_suffix_after_baseline(text: str, baseline_text: str) -> str:
    baseline_lines = baseline_text.splitlines(keepends=True)
    if not baseline_lines:
        return text
    current_lines = text.splitlines(keepends=True)
    if len(current_lines) < len(baseline_lines):
        return text
    if current_lines[: len(baseline_lines)] != baseline_lines:
        return text
    return "".join(current_lines[len(baseline_lines) :])


def _read_fresh_text(path: Path, *, fresh_only: bool, baseline_path: Path | None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not fresh_only:
        return text
    resolved_baseline = baseline_path or default_baseline_log_path(path)
    try:
        baseline_text = resolved_baseline.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return text
    except OSError:
        return text
    return _fresh_suffix_after_baseline(text, baseline_text)


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


def _pause_episode_violations(text: str) -> list[str]:
    lines = text.splitlines()
    violations: list[str] = []
    episode_number = 0
    index = 0
    while index < len(lines):
        if not FIRST_PAUSE_EVENT_PATTERN.search(lines[index]):
            index += 1
            continue
        episode_number += 1
        end_index = len(lines)
        for candidate in range(index + 1, len(lines)):
            if NEXT_TRANSPORT_EVENT_PATTERN.search(lines[candidate]):
                end_index = candidate
                break

        episode = "\n".join(lines[index:end_index])
        if not NARRATION_PAUSE_EVIDENCE_PATTERN.search(episode):
            violations.append(
                f"pause episode {episode_number} did not reach narration before the next transport command"
            )
        elif not NARRATION_PAUSE_SETTLED_PATTERN.search(episode):
            violations.append(
                f"pause episode {episode_number} did not confirm narration stopped before the next transport command"
            )
        index = max(end_index, index + 1)
    return violations


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


def _stale_pause_ignore_violations(text: str) -> list[str]:
    reader_play_seen = False
    for line in text.splitlines():
        match = TRANSPORT_EVENT_LINE_PATTERN.match(line)
        if not match:
            continue
        event = match.group("event")
        if (
            "play command accepted requested=true" in event
            or "restoring narration playback request source=" in event
        ):
            reader_play_seen = True
            continue
        if (
            "forced pause source=" in event
            or "pause command accepted" in event
            or "accepted Apple Music pause as reader transport" in event
        ):
            reader_play_seen = False
            continue
        if "ignored stale adopted Apple Music pause after reader play" not in event:
            continue
        if not reader_play_seen:
            return [
                "stale Apple Music pause was ignored before reader playback recovered"
            ]
    return []


def _autoplay_recovery_loop_violations(text: str) -> list[str]:
    recoveries: list[tuple[float, str, str]] = []
    music_surface_pause_times: dict[str, list[float]] = {}
    for line in text.splitlines():
        recovery_match = AUTOPLAY_RECOVERY_LINE_PATTERN.match(line)
        if recovery_match:
            recoveries.append(
                (
                    float(recovery_match.group("time")),
                    recovery_match.group("surface"),
                    recovery_match.group("sentence"),
                )
            )
            continue
        music_pause_match = MUSIC_SURFACE_PAUSE_LINE_PATTERN.match(line)
        if music_pause_match:
            music_surface_pause_times.setdefault(music_pause_match.group("surface"), []).append(
                float(music_pause_match.group("time"))
            )

    for index, (start_time, surface, sentence) in enumerate(recoveries):
        window_end = start_time + 2.0
        recovery_count = 0
        for recovery_time, recovery_surface, recovery_sentence in recoveries[index:]:
            if recovery_time > window_end:
                break
            if recovery_surface == surface and recovery_sentence == sentence:
                recovery_count += 1
        if recovery_count < 8:
            continue
        has_music_pause = any(
            start_time <= pause_time <= window_end
            for pause_time in music_surface_pause_times.get(surface, [])
        )
        if has_music_pause:
            return [
                "pending interactive autoplay looped while Music bed reported paused"
            ]
    return []


def _build_commit_violations(text: str, required_commit: str | None) -> list[str]:
    required = (required_commit or "").strip()
    if not required:
        return []
    commits: list[str] = []
    for match in PLAYBACK_BUILD_HEADER_PATTERN.finditer(text):
        commit_match = PLAYBACK_BUILD_COMMIT_PATTERN.search(match.group("metadata"))
        if commit_match:
            commits.append(commit_match.group("commit"))
    if not commits:
        return ["playback build header commit missing"]
    latest = commits[-1]
    if latest == "unknown":
        return ["playback build header commit is unknown"]
    if latest.startswith(required) or required.startswith(latest):
        return []
    return [
        f"playback build header commit {latest} does not match required {required}"
    ]


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


def validate_log(
    path: Path,
    *,
    mode: str,
    fresh_only: bool = False,
    baseline_path: Path | None = None,
    required_commit: str | None = None,
) -> list[str]:
    try:
        text = _read_fresh_text(path, fresh_only=fresh_only, baseline_path=baseline_path)
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
        missing.extend(_pause_episode_violations(text))
        missing.extend(_autoplay_recovery_loop_violations(text))
    if mode == "pause-resume":
        missing.extend(_dead_resume_violations(text))
        missing.extend(_consecutive_broker_pause_violations(text))
        missing.extend(_stale_pause_ignore_violations(text))
    elif mode == "resume-offset":
        missing.extend(_resume_offset_violations(text))
    missing.extend(_build_commit_violations(text, required_commit))
    return missing


def diagnostic_hints(text: str, *, mode: str, missing: list[str]) -> list[str]:
    if not missing:
        return []
    hints: list[str] = []
    if "pending interactive autoplay looped while Music bed reported paused" in missing:
        hints.append(
            "autoplay recovery loop detected; confirm the device is running a build where "
            "Job/Library audio-state callbacks do not call pending-autoplay recovery, then "
            "pull a fresh-only log after reproducing once"
        )
    if "reader received consecutive broker pauses without an intervening reader play" in missing:
        hints.append(
            "consecutive broker pauses detected; inspect whether stale Apple Music state "
            "made the second remote press resolve as pause instead of resume"
        )
    if any(re.search(pattern, text, flags=re.MULTILINE) for pattern in PLAYBACK_TRANSPORT_BREADCRUMB_PATTERNS):
        return hints
    hints.append(
        "log has no playback transport breadcrumbs; reproduce in a DEBUG Apple build, "
        "then run make apple-device-pull-and-verify-playback-transport-log without relaunching"
    )
    return hints


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
    parser.add_argument(
        "--fresh-only",
        action="store_true",
        default=os.environ.get("APPLE_PLAYBACK_TRANSPORT_FRESH_ONLY", "").strip().lower()
        in {"1", "true", "yes"},
        help=(
            "Validate only the suffix after the previous local pull baseline. "
            "The default baseline is <log>.previous.log."
        ),
    )
    parser.add_argument(
        "--baseline-log",
        default=os.environ.get("APPLE_DEVICE_PLAYBACK_BASELINE_LOG", ""),
        help="Previous pulled playback log used by --fresh-only.",
    )
    parser.add_argument(
        "--require-commit",
        default=os.environ.get("APPLE_PLAYBACK_TRANSPORT_REQUIRED_COMMIT", ""),
        help="Require the latest [PlaybackTransportBuild] header to match this git commit prefix.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    path = Path(args.log) if args.log else default_log_path(args.device.strip() or None)
    baseline_path = Path(args.baseline_log) if args.baseline_log.strip() else None
    missing = validate_log(
        path,
        mode=args.mode,
        fresh_only=args.fresh_only,
        baseline_path=baseline_path,
        required_commit=args.require_commit,
    )
    if missing:
        try:
            text = _read_fresh_text(path, fresh_only=args.fresh_only, baseline_path=baseline_path)
        except OSError:
            text = ""
        print(f"Apple playback transport log validation failed for {path}", file=sys.stderr)
        for label in missing:
            print(f"- missing: {label}", file=sys.stderr)
        for hint in diagnostic_hints(text, mode=args.mode, missing=missing):
            print(f"- hint: {hint}", file=sys.stderr)
        return 1
    fresh_label = " fresh-only" if args.fresh_only else ""
    print(f"Apple playback transport log validation passed: {path} mode={args.mode}{fresh_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
