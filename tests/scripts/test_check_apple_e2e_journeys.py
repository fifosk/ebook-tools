from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_apple_e2e_journeys.py"
SPEC = importlib.util.spec_from_file_location("check_apple_e2e_journeys", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _write_journey(path: Path, steps: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "id": "sample",
                "name": "Sample",
                "description": "Sample journey",
                "steps": steps,
            }
        ),
        encoding="utf-8",
    )


def test_all_repo_apple_journeys_match_swift_runner_contract() -> None:
    assert module.validate_journey_dir(module.DEFAULT_JOURNEY_DIR) == []


def test_validator_rejects_unknown_action(tmp_path: Path) -> None:
    journey = tmp_path / "bad.json"
    _write_journey(journey, [{"action": "dance"}])

    errors = module.validate_journey(journey)

    assert any("action 'dance' is not handled by JourneyRunner" in error for error in errors)


def test_validator_rejects_unsupported_remote_button(tmp_path: Path) -> None:
    journey = tmp_path / "bad_remote.json"
    _write_journey(journey, [{"action": "press_remote_button", "button": "rewind"}])

    errors = module.validate_journey(journey)

    assert any("remote button 'rewind' is not supported" in error for error in errors)


def test_validator_rejects_missing_action_required_fields(tmp_path: Path) -> None:
    journey = tmp_path / "missing.json"
    _write_journey(
        journey,
        [
            {"action": "assert_value_contains", "selector": "status"},
            {"action": "tap"},
        ],
    )

    errors = module.validate_journey(journey)

    assert any("action 'assert_value_contains' requires text" in error for error in errors)
    assert any("action 'tap' requires selector" in error for error in errors)


def test_validator_rejects_unknown_step_keys_and_platforms(tmp_path: Path) -> None:
    journey = tmp_path / "unknowns.json"
    _write_journey(
        journey,
        [
            {
                "action": "wait",
                "ms": 100,
                "platforms": ["watchOS"],
                "mystery": True,
            }
        ],
    )

    errors = module.validate_journey(journey)

    assert any("unknown step keys: mystery" in error for error in errors)
    assert any("platform 'watchOS' is not supported" in error for error in errors)
