from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_web_e2e_journeys.py"
SPEC = importlib.util.spec_from_file_location("check_web_e2e_journeys", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _write_journey(
    path: Path,
    steps: list[dict[str, object]],
    *,
    platforms: list[str] | None = None,
) -> None:
    payload: dict[str, object] = {
        "id": "sample",
        "name": "Sample",
        "description": "Sample journey",
        "steps": steps,
    }
    if platforms is not None:
        payload["platforms"] = platforms
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_all_repo_web_journeys_match_runner_contract() -> None:
    assert module.validate_journey_dir(module.DEFAULT_JOURNEY_DIR) == []


def test_validator_rejects_web_runnable_unknown_action(tmp_path: Path) -> None:
    journey = tmp_path / "bad.json"
    _write_journey(journey, [{"action": "assert_value_contains", "selector": "#status"}])

    errors = module.validate_journey(journey)

    assert any(
        "action 'assert_value_contains' runs on Web but is not handled by WebJourneyRunner"
        in error
        for error in errors
    )


def test_validator_allows_apple_only_unknown_action(tmp_path: Path) -> None:
    journey = tmp_path / "apple_only.json"
    _write_journey(
        journey,
        [{"action": "assert_value_contains", "selector": "nativeStatus"}],
        platforms=["iPhone", "iPad", "tvOS"],
    )

    assert module.validate_journey(journey) == []


def test_top_level_apple_scope_keeps_web_steps_out_of_web_runner(tmp_path: Path) -> None:
    journey = tmp_path / "apple_only_with_web_step.json"
    _write_journey(
        journey,
        [
            {
                "action": "assert_value_contains",
                "selector": "nativeStatus",
                "platforms": ["web"],
            }
        ],
        platforms=["iPhone", "iPad", "tvOS"],
    )

    assert module.validate_journey(journey) == []


def test_validator_rejects_bad_top_level_platform(tmp_path: Path) -> None:
    journey = tmp_path / "bad_platform.json"
    _write_journey(journey, [{"action": "login"}], platforms=["watchOS"])

    errors = module.validate_journey(journey)

    assert any("platform 'watchos' is not supported" in error for error in errors)


def test_validator_requires_web_action_fields(tmp_path: Path) -> None:
    journey = tmp_path / "missing.json"
    _write_journey(
        journey,
        [
            {"action": "navigate_tab"},
            {"action": "tap"},
        ],
        platforms=["web"],
    )

    errors = module.validate_journey(journey)

    assert any("Web action 'navigate_tab' requires tab" in error for error in errors)
    assert any("Web action 'tap' requires selector" in error for error in errors)
