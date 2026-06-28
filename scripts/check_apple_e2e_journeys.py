#!/usr/bin/env python3
"""Validate Apple JSON E2E journeys against the Swift journey runner contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from write_apple_e2e_config import load_journey_platforms, platform_for_profile

DEFAULT_JOURNEY_DIR = ROOT / "tests/e2e/journeys"
DEFAULT_RUNNER = (
    ROOT / "ios/InteractiveReader/InteractiveReaderUITests/JourneyRunner.swift"
)
DEFAULT_MAKEFILE = ROOT / "Makefile"

TOP_LEVEL_KEYS = {"id", "name", "description", "platforms", "steps"}
STEP_REQUIRED_KEYS: dict[str, set[str]] = {
    "assert_frame": {"selector"},
    "assert_non_empty_value": {"selector"},
    "assert_value_key_at_least": {"selector", "min_value"},
    "assert_value_contains": {"selector", "text"},
    "assert_visible": {"selector"},
    "enter_text": {"selector"},
    "select_option": {"selector", "text"},
    "tap": {"selector"},
}
NON_NEGATIVE_INT_KEYS = {"count", "interval_ms", "ms", "timeout"}
NUMERIC_KEYS = {
    "max_aspect_ratio",
    "max_height",
    "max_width",
    "min_aspect_ratio",
    "min_height",
    "min_value",
    "min_width",
}
MUSIC_BED_STATUS_SELECTOR = "e2eMusicBedSyncStatus"
E2E_PROFILE_JOURNEY_VARIABLES: tuple[tuple[str, str], ...] = (
    ("iphone", "JOURNEY_SRC"),
    ("ipados", "JOURNEY_SRC"),
    ("tvos", "JOURNEY_SRC"),
    ("iphone-create", "CREATE_READINESS_JOURNEY_SRC"),
    ("ipados-create", "CREATE_READINESS_JOURNEY_SRC"),
    ("tvos-create", "CREATE_READINESS_JOURNEY_SRC"),
    ("ipados-music-bed-sync", "MUSIC_BED_SYNC_JOURNEY_SRC"),
    ("tvos-music-bed-sync", "MUSIC_BED_SYNC_JOURNEY_SRC"),
)


def _extract_block(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise ValueError(f"Could not find block for {signature}")


def load_runner_contract(runner_path: Path = DEFAULT_RUNNER) -> dict[str, set[str]]:
    source = runner_path.read_text(encoding="utf-8")
    step_block = _extract_block(source, "struct JourneyStep: Decodable")
    execute_block = _extract_block(source, "private func execute(_ step: JourneyStep)")
    platform_block = _extract_block(source, "enum E2EPlatform: String")
    remote_block = _extract_block(source, "private func remoteButton(named name: String)")

    step_keys = set(re.findall(r"\b(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:", step_block))
    actions = set(re.findall(r'case\s+"([^"]+)"\s*:', execute_block))
    platforms = set(re.findall(r"\bcase\s+([A-Za-z_][A-Za-z0-9_]*)\b", platform_block))
    remote_buttons: set[str] = set()
    for case_line in re.findall(r'case\s+([^:\n]+):', remote_block):
        remote_buttons.update(re.findall(r'"([^"]+)"', case_line))
    return {
        "step_keys": step_keys,
        "actions": actions,
        "platforms": platforms,
        "remote_buttons": remote_buttons,
    }


def _is_blank(value: Any) -> bool:
    return isinstance(value, str) and not value.strip()


def _validate_step(
    *,
    path: Path,
    index: int,
    step: Any,
    contract: dict[str, set[str]],
) -> list[str]:
    location = f"{path}:{index + 1}"
    errors: list[str] = []
    if not isinstance(step, dict):
        return [f"{location} step must be an object"]

    unknown_keys = set(step) - contract["step_keys"]
    if unknown_keys:
        errors.append(f"{location} has unknown step keys: {', '.join(sorted(unknown_keys))}")

    action = step.get("action")
    if not isinstance(action, str) or not action.strip():
        errors.append(f"{location} action is required")
        return errors
    if action not in contract["actions"]:
        errors.append(f"{location} action {action!r} is not handled by JourneyRunner")

    for key in STEP_REQUIRED_KEYS.get(action, set()):
        if key not in step or _is_blank(step.get(key)):
            errors.append(f"{location} action {action!r} requires {key}")

    platforms = step.get("platforms")
    if platforms is not None:
        if not isinstance(platforms, list) or not platforms:
            errors.append(f"{location} platforms must be a non-empty list when present")
        else:
            for platform in platforms:
                if platform not in contract["platforms"]:
                    errors.append(f"{location} platform {platform!r} is not supported")

    if action == "press_remote_button":
        raw_button = str(step.get("button") or step.get("text") or "select").strip().lower()
        if raw_button not in contract["remote_buttons"]:
            errors.append(f"{location} remote button {raw_button!r} is not supported")

    if action == "press_keyboard_key":
        raw_key = str(step.get("key") or step.get("text") or "").strip().lower()
        supported_keys = {
            "space",
            "spacebar",
            "left",
            "leftarrow",
            "left_arrow",
            "right",
            "rightarrow",
            "right_arrow",
            "return",
            "enter",
            "returnorenter",
            "return_or_enter",
        }
        if raw_key not in supported_keys:
            errors.append(f"{location} keyboard key {raw_key!r} is not supported")

    for key in NON_NEGATIVE_INT_KEYS:
        if key in step:
            value = step[key]
            if not isinstance(value, int) or value < 0:
                errors.append(f"{location} {key} must be a non-negative integer")

    for key in NUMERIC_KEYS:
        if key in step and not isinstance(step[key], (int, float)):
            errors.append(f"{location} {key} must be numeric")

    if action == "assert_value_key_at_least":
        key = step.get("key")
        text = step.get("text")
        has_key = isinstance(key, str) and bool(key.strip())
        has_text = isinstance(text, str) and bool(text.strip())
        if not has_key and not has_text:
            errors.append(f"{location} action {action!r} requires key or text")

    return errors


def _validate_platforms(*, location: str, platforms: Any, supported: set[str]) -> list[str]:
    if platforms is None:
        return []
    if not isinstance(platforms, list) or not platforms:
        return [f"{location} platforms must be a non-empty list when present"]
    errors: list[str] = []
    for platform in platforms:
        if platform not in supported:
            errors.append(f"{location} platform {platform!r} is not supported")
    return errors


def _step_matches(step: Any, **expected: object) -> bool:
    if not isinstance(step, dict):
        return False
    return all(step.get(key) == value for key, value in expected.items())


def _has_step(steps: list[Any], **expected: object) -> bool:
    return any(_step_matches(step, **expected) for step in steps)


def _has_status_text(steps: list[Any], text: str) -> bool:
    return _has_step(
        steps,
        action="assert_value_contains",
        selector=MUSIC_BED_STATUS_SELECTOR,
        text=text,
    )


def _find_step_index(steps: list[Any], **expected: object) -> int | None:
    for index, step in enumerate(steps):
        if _step_matches(step, **expected):
            return index
    return None


def _validate_following_status_sequence(
    *,
    path: Path,
    steps: list[Any],
    anchor: dict[str, object],
    expected_texts: list[str],
) -> list[str]:
    errors: list[str] = []
    anchor_index = _find_step_index(steps, **anchor)
    anchor_label = anchor.get("screenshot") or anchor.get("selector") or anchor.get("action")
    if anchor_index is None:
        return [f"{path} music_bed_sync requires step {anchor_label!r}"]
    for offset, text in enumerate(expected_texts, start=1):
        candidate_index = anchor_index + offset
        if candidate_index >= len(steps) or not _step_matches(
            steps[candidate_index],
            action="assert_value_contains",
            selector=MUSIC_BED_STATUS_SELECTOR,
            text=text,
        ):
            errors.append(
                f"{path} music_bed_sync requires {text!r} immediately after {anchor_label!r}"
            )
    return errors


def _validate_following_step_sequence(
    *,
    path: Path,
    steps: list[Any],
    anchor: dict[str, object],
    expected_steps: list[dict[str, object]],
) -> list[str]:
    errors: list[str] = []
    anchor_index = _find_step_index(steps, **anchor)
    anchor_label = anchor.get("screenshot") or anchor.get("selector") or anchor.get("action")
    if anchor_index is None:
        return [f"{path} music_bed_sync requires step {anchor_label!r}"]
    for offset, expected in enumerate(expected_steps, start=1):
        candidate_index = anchor_index + offset
        if candidate_index >= len(steps) or not _step_matches(steps[candidate_index], **expected):
            expected_label = (
                expected.get("screenshot")
                or expected.get("text")
                or expected.get("key")
                or expected.get("action")
            )
            errors.append(
                f"{path} music_bed_sync requires {expected_label!r} immediately after {anchor_label!r}"
            )
    return errors


def _validate_pause_hold_status_sequence(
    *,
    path: Path,
    steps: list[Any],
    anchor_screenshot: str,
    wait_ms: int,
) -> list[str]:
    errors: list[str] = []
    anchor_index = _find_step_index(
        steps,
        action="assert_value_contains",
        selector=MUSIC_BED_STATUS_SELECTOR,
        text="reader=paused",
        screenshot=anchor_screenshot,
    )
    if anchor_index is None:
        return [f"{path} music_bed_sync requires pause assertion {anchor_screenshot!r}"]

    wait_index: int | None = None
    for index in range(anchor_index + 1, len(steps)):
        if _step_matches(steps[index], action="wait", ms=wait_ms):
            wait_index = index
            break
    if wait_index is None:
        return [
            f"{path} music_bed_sync requires {wait_ms}ms pause-hold wait after {anchor_screenshot!r}"
        ]

    expected_texts = [
        "reader=paused",
        "music=paused",
        "guard=true",
        "surface=reader",
        "fullscreen=blocked",
    ]
    for offset, text in enumerate(expected_texts, start=1):
        candidate_index = wait_index + offset
        if candidate_index >= len(steps) or not _step_matches(
            steps[candidate_index],
            action="assert_value_contains",
            selector=MUSIC_BED_STATUS_SELECTOR,
            text=text,
        ):
            errors.append(
                f"{path} music_bed_sync requires pause-hold {text!r} after {anchor_screenshot!r}"
            )
    return errors


def _validate_music_bed_sync_contract(path: Path, payload: dict[str, Any]) -> list[str]:
    if payload.get("id") != "music_bed_sync":
        return []
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return []

    errors: list[str] = []
    required_steps = [
        {
            "action": "assert_visible",
            "selector": "e2eMusicBedPauseButton",
        },
        {
            "action": "play_first_item",
            "screenshot": "music_bed_ipad_player_opened",
            "unless_visible": "e2eMusicBedPlayButton",
            "platforms": ["iPad"],
        },
        {
            "action": "tap",
            "selector": "e2eMusicBedPlayButton",
            "screenshot": "music_bed_ipad_music_play_tapped",
        },
        {
            "action": "tap",
            "selector": "e2eMusicBedAutoResumeButton",
        },
        {
            "action": "tap",
            "selector": "e2eReaderTransitionButton",
            "screenshot": "music_bed_ipad_sentence_transition_pressed",
        },
        {
            "action": "tap",
            "selector": "e2eReaderTransitionResumeButton",
            "screenshot": "music_bed_ipad_sentence_transition_resume_pressed",
        },
        {
            "action": "tap",
            "selector": "e2eBubblePronunciationResumeButton",
            "screenshot": "music_bed_ipad_bubble_pronunciation_resume_setup",
        },
        {
            "action": "press_keyboard_key",
            "key": "right",
            "platforms": ["iPad"],
            "screenshot": "music_bed_ipad_bubble_right_word_pressed",
        },
        {
            "action": "press_keyboard_key",
            "key": "left",
            "platforms": ["iPad"],
            "screenshot": "music_bed_ipad_bubble_left_word_pressed",
        },
        {
            "action": "press_keyboard_key",
            "key": "enter",
            "platforms": ["iPad"],
            "screenshot": "music_bed_ipad_bubble_lookup_return_pressed",
        },
        {
            "action": "press_keyboard_key",
            "key": "space",
            "selector": "e2eKeyboardSpaceCommandButton",
            "screenshot": "music_bed_ipad_bubble_space_resume_pressed",
        },
        {
            "action": "assert_value_key_at_least",
            "selector": MUSIC_BED_STATUS_SELECTOR,
            "key": "transitionPauses",
            "min_value": 1,
        },
        {
            "action": "assert_value_key_at_least",
            "selector": MUSIC_BED_STATUS_SELECTOR,
            "key": "autoResumeAlreadyPlaying",
            "min_value": 1,
            "screenshot": "music_bed_ipad_auto_resume_settled",
        },
        {
            "action": "press_keyboard_key",
            "key": "space",
            "selector": "e2eKeyboardSpaceCommandButton",
            "screenshot": "music_bed_ipad_space_pause_pressed",
            "platforms": ["iPad"],
        },
        {
            "action": "press_keyboard_key",
            "key": "space",
            "selector": "e2eKeyboardSpaceCommandButton",
            "screenshot": "music_bed_ipad_space_resume_pressed",
            "platforms": ["iPad"],
        },
        {
            "action": "press_remote_button",
            "button": "playPause",
            "screenshot": "music_bed_remote_pause_pressed",
        },
        {
            "action": "press_remote_button",
            "button": "playPause",
            "screenshot": "music_bed_guarded_remote_play_pressed",
        },
        {
            "action": "press_remote_button",
            "button": "playPause",
            "count": 2,
            "interval_ms": 150,
            "screenshot": "music_bed_remote_double_pause_pressed",
        },
    ]
    for required in required_steps:
        if not _has_step(steps, **required):
            errors.append(f"{path} music_bed_sync requires step {required!r}")

    for text in [
        "reader=paused",
        "reader=playing",
        "music=paused",
        "music=playing",
        "guard=true",
        "guard=false",
        "surface=reader",
        "fullscreen=blocked",
        "sessionStable=true",
        "sessionLabel=mixing",
        "requested=true",
        "readerPause=false",
        "manual=false",
        "phase=sentenceTransition",
        "phase=sentenceTransitionResume",
        "bubbleWordNavDirection=1",
        "bubbleWordNavDirection=-1",
        "bubbleLookupHadBubble=true",
    ]:
        if not _has_status_text(steps, text):
            errors.append(
                f"{path} music_bed_sync requires {MUSIC_BED_STATUS_SELECTOR} assertion {text!r}"
            )

    for command_count in range(0, 4):
        text = f"readerTransportCommands={command_count}"
        if not _has_status_text(steps, text):
            errors.append(
                f"{path} music_bed_sync requires {MUSIC_BED_STATUS_SELECTOR} assertion {text!r}"
            )

    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "assert_value_key_at_least",
                "selector": MUSIC_BED_STATUS_SELECTOR,
                "key": "autoResumeAlreadyPlaying",
                "min_value": 1,
                "screenshot": "music_bed_ipad_auto_resume_settled",
            },
            expected_texts=[
                "music=playing",
                "surface=reader",
                "sessionStable=true",
                "sessionLabel=mixing",
            ],
        )
    )

    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_remote_button",
                "button": "playPause",
                "screenshot": "music_bed_remote_pause_pressed",
            },
            expected_texts=[
                "readerTransportCommands=1",
                "lastAction=pause",
                "reader=paused",
                "music=paused",
                "guard=true",
                "surface=reader",
                "fullscreen=blocked",
            ],
        )
    )
    errors.extend(
        _validate_pause_hold_status_sequence(
            path=path,
            steps=steps,
            anchor_screenshot="music_bed_remote_pause_observed",
            wait_ms=1500,
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_remote_button",
                "button": "playPause",
                "screenshot": "music_bed_guarded_remote_play_pressed",
            },
            expected_texts=[
                "readerTransportCommands=1",
                "lastAction=pause",
                "reader=paused",
                "music=paused",
                "guard=true",
            ],
        )
    )
    errors.extend(
        _validate_following_step_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_keyboard_key",
                "key": "right",
                "platforms": ["iPad"],
                "screenshot": "music_bed_ipad_bubble_right_word_pressed",
            },
            expected_steps=[
                {
                    "action": "assert_value_key_at_least",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "key": "bubbleWordNav",
                    "min_value": 1,
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "bubbleWordNavDirection=1",
                },
            ],
        )
    )
    errors.extend(
        _validate_following_step_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_keyboard_key",
                "key": "left",
                "platforms": ["iPad"],
                "screenshot": "music_bed_ipad_bubble_left_word_pressed",
            },
            expected_steps=[
                {
                    "action": "assert_value_key_at_least",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "key": "bubbleWordNav",
                    "min_value": 2,
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "bubbleWordNavDirection=-1",
                },
            ],
        )
    )
    errors.extend(
        _validate_following_step_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_keyboard_key",
                "key": "enter",
                "platforms": ["iPad"],
                "screenshot": "music_bed_ipad_bubble_lookup_return_pressed",
            },
            expected_steps=[
                {
                    "action": "assert_value_key_at_least",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "key": "bubbleLookup",
                    "min_value": 1,
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "bubbleLookupHadBubble=true",
                },
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_keyboard_key",
                "key": "space",
                "selector": "e2eKeyboardSpaceCommandButton",
                "screenshot": "music_bed_ipad_space_pause_pressed",
                "platforms": ["iPad"],
            },
            expected_texts=[
                "readerTransportCommands=1",
                "lastAction=pause",
                "reader=paused",
                "music=paused",
                "readerPause=true",
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_keyboard_key",
                "key": "space",
                "selector": "e2eKeyboardSpaceCommandButton",
                "screenshot": "music_bed_ipad_space_resume_pressed",
                "platforms": ["iPad"],
            },
            expected_texts=[
                "readerTransportCommands=2",
                "lastAction=play",
                "reader=playing",
                "music=playing",
                "readerPause=false",
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_remote_button",
                "button": "playPause",
                "screenshot": "music_bed_remote_play_pressed",
            },
            expected_texts=[
                "readerTransportCommands=2",
                "lastAction=play",
                "reader=playing",
                "music=playing",
                "surface=reader",
                "guard=false",
                "fullscreen=blocked",
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_remote_button",
                "button": "playPause",
                "count": 2,
                "interval_ms": 150,
                "screenshot": "music_bed_remote_double_pause_pressed",
            },
            expected_texts=[
                "readerTransportCommands=3",
                "lastAction=pause",
                "reader=paused",
                "music=paused",
                "guard=true",
                "fullscreen=blocked",
            ],
        )
    )
    errors.extend(
        _validate_following_step_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "assert_value_contains",
                "selector": MUSIC_BED_STATUS_SELECTOR,
                "text": "reader=paused",
                "platforms": ["tvOS"],
                "timeout": 10,
                "screenshot": "music_bed_remote_double_pause_observed",
            },
            expected_steps=[
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "music=paused",
                    "platforms": ["tvOS"],
                    "timeout": 10,
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "guard=true",
                    "platforms": ["tvOS"],
                    "timeout": 10,
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "fullscreen=blocked",
                    "platforms": ["tvOS"],
                    "timeout": 10,
                },
                {
                    "action": "go_back",
                    "platforms": ["tvOS"],
                    "screenshot": "music_bed_paused_returned_to_menu",
                },
                {
                    "action": "assert_visible",
                    "selector": "libraryShellView",
                    "platforms": ["tvOS"],
                    "timeout": 10,
                },
                {
                    "action": "press_remote_button",
                    "button": "playPause",
                    "platforms": ["tvOS"],
                    "screenshot": "music_bed_shell_play_pause_resume_pressed",
                },
                {
                    "action": "assert_visible",
                    "selector": "e2eMusicBedPauseButton",
                    "platforms": ["tvOS"],
                    "timeout": 15,
                    "screenshot": "music_bed_shell_play_pause_player_reopened",
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "reader=playing",
                    "platforms": ["tvOS"],
                    "timeout": 15,
                    "screenshot": "music_bed_shell_play_pause_resume_observed",
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "music=playing",
                    "platforms": ["tvOS"],
                    "timeout": 10,
                },
                {
                    "action": "assert_value_contains",
                    "selector": MUSIC_BED_STATUS_SELECTOR,
                    "text": "surface=reader",
                    "platforms": ["tvOS"],
                    "timeout": 10,
                },
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "tap",
                "selector": "e2eMusicBedPlayButton",
                "screenshot": "music_bed_ipad_music_play_tapped",
            },
            expected_texts=[
                "music=playing",
                "surface=reader",
                "sessionStable=true",
                "sessionLabel=mixing",
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "tap",
                "selector": "e2eReaderTransitionButton",
                "screenshot": "music_bed_ipad_sentence_transition_pressed",
            },
            expected_texts=[
                "requested=true",
                "reader=paused",
                "music=playing",
                "readerPause=false",
                "manual=false",
                "phase=sentenceTransition",
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "tap",
                "selector": "e2eReaderTransitionResumeButton",
                "screenshot": "music_bed_ipad_sentence_transition_resume_pressed",
            },
            expected_texts=[
                "reader=playing",
                "music=playing",
                "phase=sentenceTransitionResume",
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "tap",
                "selector": "e2eBubblePronunciationResumeButton",
                "screenshot": "music_bed_ipad_bubble_pronunciation_resume_setup",
            },
            expected_texts=[
                "reader=paused",
                "music=paused",
                "readerPause=true",
            ],
        )
    )
    errors.extend(
        _validate_following_status_sequence(
            path=path,
            steps=steps,
            anchor={
                "action": "press_keyboard_key",
                "key": "space",
                "selector": "e2eKeyboardSpaceCommandButton",
                "screenshot": "music_bed_ipad_bubble_space_resume_pressed",
            },
            expected_texts=[
                "lastAction=play",
                "reader=playing",
                "music=playing",
            ],
        )
    )
    return errors


def validate_journey(path: Path, contract: dict[str, set[str]] | None = None) -> list[str]:
    contract = contract or load_runner_contract()
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path} is not valid JSON: {exc}"]

    if not isinstance(payload, dict):
        return [f"{path} must contain a JSON object"]

    unknown_top_level = set(payload) - TOP_LEVEL_KEYS
    if unknown_top_level:
        errors.append(f"{path} has unknown top-level keys: {', '.join(sorted(unknown_top_level))}")

    for key in ("id", "name", "description"):
        if key not in payload or _is_blank(payload.get(key)):
            errors.append(f"{path} {key} is required")
    errors.extend(
        _validate_platforms(
            location=str(path),
            platforms=payload.get("platforms"),
            supported=contract["platforms"],
        )
    )

    steps = payload.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(f"{path} steps must be a non-empty list")
        return errors

    for index, step in enumerate(steps):
        errors.extend(_validate_step(path=path, index=index, step=step, contract=contract))
    errors.extend(_validate_music_bed_sync_contract(path, payload))
    return errors


def validate_journey_dir(journey_dir: Path = DEFAULT_JOURNEY_DIR) -> list[str]:
    contract = load_runner_contract()
    errors: list[str] = []
    for path in sorted(journey_dir.glob("*.json")):
        errors.extend(validate_journey(path, contract))
    if not list(journey_dir.glob("*.json")):
        errors.append(f"{journey_dir} contains no journey JSON files")
    if journey_dir.resolve() == DEFAULT_JOURNEY_DIR.resolve():
        errors.extend(validate_makefile_profile_journey_scopes())
    return errors


def _extract_make_variable(makefile_source: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}\s*[?:]?=\s*(.+)$", makefile_source, re.MULTILINE)
    if match is None:
        return None
    return match.group(1).strip()


def _resolve_make_journey_path(makefile_source: str, variable_name: str) -> Path | None:
    raw_value = _extract_make_variable(makefile_source, variable_name)
    if raw_value is None:
        return None
    variable_reference = re.fullmatch(r"\$\(([A-Za-z0-9_]+)\)", raw_value)
    if variable_reference:
        return _resolve_make_journey_path(makefile_source, variable_reference.group(1))
    return (ROOT / raw_value).resolve()


def _profile_target_is_registered(makefile_source: str, profile: str) -> bool:
    if profile in {"iphone", "ipados", "tvos"}:
        target = {"iphone": "test-e2e-iphone", "ipados": "test-e2e-ipad", "tvos": "test-e2e-tvos"}[profile]
        return f"{target}: E2E_PROFILE = {profile}" in makefile_source
    return f"E2E_PROFILE={profile}" in makefile_source


def validate_profile_journey_scope(profile: str, journey_path: Path) -> list[str]:
    platform = platform_for_profile(profile)
    if platform is None:
        return []
    try:
        platforms = load_journey_platforms(journey_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"profile {profile!r} journey {journey_path} cannot be read: {exc}"]
    if not platforms:
        return []
    if platform.lower() in {candidate.lower() for candidate in platforms}:
        return []
    return [
        f"profile {profile!r} resolves to {platform}, but journey {journey_path} "
        f"is scoped to {', '.join(platforms)}"
    ]


def validate_makefile_profile_journey_scopes(
    makefile_path: Path = DEFAULT_MAKEFILE,
) -> list[str]:
    try:
        makefile_source = makefile_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{makefile_path} cannot be read: {exc}"]

    errors: list[str] = []
    for profile, journey_variable in E2E_PROFILE_JOURNEY_VARIABLES:
        if not _profile_target_is_registered(makefile_source, profile):
            errors.append(f"{makefile_path} does not register Apple E2E profile {profile!r}")
            continue
        journey_path = _resolve_make_journey_path(makefile_source, journey_variable)
        if journey_path is None:
            errors.append(f"{makefile_path} does not define {journey_variable}")
            continue
        errors.extend(validate_profile_journey_scope(profile, journey_path))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journey-dir", default=str(DEFAULT_JOURNEY_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_journey_dir(Path(args.journey_dir))
    if errors:
        print("Apple E2E journey validation failed:")
        for error in errors:
            print(f"- {error}")
        return 2
    print("Apple E2E journey validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
