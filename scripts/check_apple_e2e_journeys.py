#!/usr/bin/env python3
"""Validate Apple JSON E2E journeys against the Swift journey runner contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOURNEY_DIR = ROOT / "tests/e2e/journeys"
DEFAULT_RUNNER = (
    ROOT / "ios/InteractiveReader/InteractiveReaderUITests/JourneyRunner.swift"
)

TOP_LEVEL_KEYS = {"id", "name", "description", "steps"}
STEP_REQUIRED_KEYS: dict[str, set[str]] = {
    "assert_frame": {"selector"},
    "assert_non_empty_value": {"selector"},
    "assert_value_contains": {"selector", "text"},
    "assert_visible": {"selector"},
    "enter_text": {"selector"},
    "select_option": {"selector", "text"},
    "tap": {"selector"},
}
NON_NEGATIVE_INT_KEYS = {"count", "interval_ms", "ms", "timeout"}


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

    for key in NON_NEGATIVE_INT_KEYS:
        if key in step:
            value = step[key]
            if not isinstance(value, int) or value < 0:
                errors.append(f"{location} {key} must be a non-negative integer")

    for key in ("min_width", "min_height", "max_width", "max_height", "min_aspect_ratio", "max_aspect_ratio"):
        if key in step and not isinstance(step[key], (int, float)):
            errors.append(f"{location} {key} must be numeric")

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

    steps = payload.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(f"{path} steps must be a non-empty list")
        return errors

    for index, step in enumerate(steps):
        errors.extend(_validate_step(path=path, index=index, step=step, contract=contract))
    return errors


def validate_journey_dir(journey_dir: Path = DEFAULT_JOURNEY_DIR) -> list[str]:
    contract = load_runner_contract()
    errors: list[str] = []
    for path in sorted(journey_dir.glob("*.json")):
        errors.extend(validate_journey(path, contract))
    if not list(journey_dir.glob("*.json")):
        errors.append(f"{journey_dir} contains no journey JSON files")
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
