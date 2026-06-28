#!/usr/bin/env python3
"""Validate Web JSON E2E journeys against the Playwright journey runner."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOURNEY_DIR = ROOT / "tests/e2e/journeys"
DEFAULT_RUNNER = ROOT / "tests/e2e/journey_runner.py"

TOP_LEVEL_KEYS = {"id", "name", "description", "platforms", "steps"}
WEB_PLATFORMS = {"web", "browser"}
SUPPORTED_PLATFORMS = {"web", "browser", "iphone", "ipad", "tvos"}
STEP_REQUIRED_KEYS: dict[str, set[str]] = {
    "assert_visible": {"selector"},
    "enter_text": {"selector"},
    "navigate_tab": {"tab"},
    "select_filter": {"filter"},
    "tap": {"selector"},
}
NON_NEGATIVE_INT_KEYS = {"ms", "timeout"}


def load_runner_actions(runner_path: Path = DEFAULT_RUNNER) -> set[str]:
    source = runner_path.read_text(encoding="utf-8")
    return set(re.findall(r"def _do_([A-Za-z_][A-Za-z0-9_]*)\(self, step: dict\)", source))


def _is_blank(value: Any) -> bool:
    return isinstance(value, str) and not value.strip()


def _normalize_platforms(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [str(candidate).strip().lower() for candidate in value]


def _platform_errors(location: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not value:
        return [f"{location} platforms must be a non-empty list when present"]
    errors: list[str] = []
    for platform in _normalize_platforms(value):
        if platform not in SUPPORTED_PLATFORMS:
            errors.append(f"{location} platform {platform!r} is not supported")
    return errors


def _runs_on_web(step: dict[str, Any], journey_platforms: list[str]) -> bool:
    if journey_platforms and not any(platform in WEB_PLATFORMS for platform in journey_platforms):
        return False
    step_platforms = _normalize_platforms(step.get("platforms"))
    if step_platforms:
        return any(platform in WEB_PLATFORMS for platform in step_platforms)
    if journey_platforms:
        return any(platform in WEB_PLATFORMS for platform in journey_platforms)
    return True


def _validate_step(
    *,
    path: Path,
    index: int,
    step: Any,
    runner_actions: set[str],
    journey_platforms: list[str],
) -> list[str]:
    location = f"{path}:{index + 1}"
    errors: list[str] = []
    if not isinstance(step, dict):
        return [f"{location} step must be an object"]

    errors.extend(_platform_errors(location, step.get("platforms")))

    action = step.get("action")
    if not isinstance(action, str) or not action.strip():
        errors.append(f"{location} action is required")
        return errors

    for key in NON_NEGATIVE_INT_KEYS:
        if key in step:
            value = step[key]
            if not isinstance(value, int) or value < 0:
                errors.append(f"{location} {key} must be a non-negative integer")

    if not _runs_on_web(step, journey_platforms):
        return errors

    if action not in runner_actions:
        errors.append(
            f"{location} action {action!r} runs on Web but is not handled by WebJourneyRunner"
        )

    for key in STEP_REQUIRED_KEYS.get(action, set()):
        if key not in step or _is_blank(step.get(key)):
            errors.append(f"{location} Web action {action!r} requires {key}")

    return errors


def validate_journey(path: Path, runner_actions: set[str] | None = None) -> list[str]:
    runner_actions = runner_actions or load_runner_actions()
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

    errors.extend(_platform_errors(str(path), payload.get("platforms")))
    journey_platforms = _normalize_platforms(payload.get("platforms"))

    steps = payload.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(f"{path} steps must be a non-empty list")
        return errors

    for index, step in enumerate(steps):
        errors.extend(
            _validate_step(
                path=path,
                index=index,
                step=step,
                runner_actions=runner_actions,
                journey_platforms=journey_platforms,
            )
        )

    return errors


def validate_journey_dir(journey_dir: Path = DEFAULT_JOURNEY_DIR) -> list[str]:
    runner_actions = load_runner_actions()
    paths = sorted(journey_dir.glob("*.json"))
    if not paths:
        return [f"{journey_dir} contains no journey JSON files"]
    errors: list[str] = []
    for path in paths:
        errors.extend(validate_journey(path, runner_actions))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journey-dir", default=str(DEFAULT_JOURNEY_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_journey_dir(Path(args.journey_dir))
    if errors:
        print("Web E2E journey validation failed:")
        for error in errors:
            print(f"- {error}")
        return 2
    print("Web E2E journey validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
