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


def _write_music_bed_journey(
    path: Path,
    *,
    remove_text: str | None = None,
    remove_screenshot: str | None = None,
    mutate_double_press: bool = False,
) -> None:
    payload = json.loads((module.DEFAULT_JOURNEY_DIR / "music_bed_sync.json").read_text(encoding="utf-8"))
    steps = payload["steps"]
    if remove_text is not None:
        payload["steps"] = [
            step
            for step in steps
            if not (
                step.get("action") == "assert_value_contains"
                and step.get("selector") == "e2eMusicBedSyncStatus"
                and step.get("text") == remove_text
            )
        ]
    if remove_screenshot is not None:
        payload["steps"] = [
            step for step in payload["steps"] if step.get("screenshot") != remove_screenshot
        ]
    if mutate_double_press:
        for step in steps:
            if step.get("screenshot") == "music_bed_remote_double_pause_pressed":
                step["count"] = 1
                break
    path.write_text(json.dumps(payload), encoding="utf-8")


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


def test_music_bed_validator_requires_fullscreen_suppression_assertions(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_text="fullscreen=blocked")

    errors = module.validate_journey(journey)

    assert any("requires e2eMusicBedSyncStatus assertion 'fullscreen=blocked'" in error for error in errors)


def test_music_bed_validator_requires_guard_pause_assertions(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_text="guard=true")

    errors = module.validate_journey(journey)

    assert any("requires e2eMusicBedSyncStatus assertion 'guard=true'" in error for error in errors)


def test_music_bed_validator_requires_double_remote_press(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, mutate_double_press=True)

    errors = module.validate_journey(journey)

    assert any("music_bed_remote_double_pause_pressed" in error for error in errors)


def test_music_bed_validator_requires_transport_command_sequence(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_text="readerTransportCommands=5")

    errors = module.validate_journey(journey)

    assert any("requires e2eMusicBedSyncStatus assertion 'readerTransportCommands=5'" in error for error in errors)


def test_music_bed_validator_requires_observed_pause_sequence(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_screenshot="music_bed_observed_pause_pressed")

    errors = module.validate_journey(journey)

    assert any("e2eObservedMusicPauseButton" in error for error in errors)


def test_music_bed_validator_requires_immediate_observed_pause_phase(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_text="phase=observedPauseImmediate")

    errors = module.validate_journey(journey)

    assert any("phase=observedPauseImmediate" in error for error in errors)


def test_music_bed_validator_requires_delayed_pause_hold_assertions(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_screenshot="music_bed_remote_pause_hold_observed")

    errors = module.validate_journey(journey)

    assert any(
        "requires pause-hold 'reader=paused' after 'music_bed_remote_pause_observed'" in error
        for error in errors
    )


def test_music_bed_validator_requires_long_pause_hold_assertions(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_screenshot="music_bed_remote_pause_long_hold_observed")

    errors = module.validate_journey(journey)

    assert any(
        "requires pause-hold 'reader=paused' after 'music_bed_remote_pause_observed'" in error
        for error in errors
    )
