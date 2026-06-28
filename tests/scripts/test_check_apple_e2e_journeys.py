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
                "platforms": ["iPhone", "iPad"],
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
    remove_ipad_unless_visible: bool = False,
    remove_ipad_auto_resume: bool = False,
    remove_ipad_transition_probe: bool = False,
    remove_ipad_space_probe: bool = False,
    remove_ipad_bubble_probe: bool = False,
    remove_ipad_bubble_keyboard_probe: bool = False,
    remove_tvos_short_pause_hold: bool = False,
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
    if remove_tvos_short_pause_hold:
        payload["steps"] = [
            step
            for step in payload["steps"]
            if not (
                step.get("action") == "wait"
                and step.get("ms") == 100
                and step.get("platforms") == ["tvOS"]
            )
        ]
    if remove_ipad_unless_visible:
        for step in payload["steps"]:
            if step.get("screenshot") == "music_bed_ipad_player_opened":
                step.pop("unless_visible", None)
                break
    if remove_ipad_auto_resume:
        payload["steps"] = [
            step
            for step in payload["steps"]
            if step.get("selector") != "e2eMusicBedAutoResumeButton"
            and step.get("screenshot") != "music_bed_ipad_auto_resume_settled"
        ]
    if remove_ipad_transition_probe:
        payload["steps"] = [
            step
            for step in payload["steps"]
            if step.get("selector") not in {
                "e2eReaderTransitionButton",
                "e2eReaderTransitionResumeButton",
            }
            and step.get("screenshot") not in {
                "music_bed_ipad_sentence_transition_stable",
                "music_bed_ipad_sentence_transition_pressed",
                "music_bed_ipad_sentence_transition_resume_pressed",
            }
        ]
    if remove_ipad_space_probe:
        payload["steps"] = [
            step
            for step in payload["steps"]
            if step.get("action") != "press_keyboard_key"
            and step.get("screenshot") not in {
                "music_bed_ipad_space_pause_observed",
                "music_bed_ipad_space_resume_observed",
            }
        ]
    if remove_ipad_bubble_probe:
        payload["steps"] = [
            step
            for step in payload["steps"]
            if step.get("selector")
            not in {
                "e2eBubblePronunciationResumeButton",
            }
            and step.get("screenshot")
            not in {
                "music_bed_ipad_bubble_pronunciation_resume_setup",
                "music_bed_ipad_bubble_space_resume_pressed",
                "music_bed_ipad_bubble_space_resume_observed",
            }
        ]
    if remove_ipad_bubble_keyboard_probe:
        payload["steps"] = [
            step
            for step in payload["steps"]
            if step.get("screenshot")
            not in {
                "music_bed_ipad_bubble_right_word_pressed",
                "music_bed_ipad_bubble_left_word_pressed",
                "music_bed_ipad_bubble_lookup_return_pressed",
            }
            and step.get("key") not in {"bubbleWordNav", "bubbleLookup"}
            and step.get("text")
            not in {
                "bubbleWordNavDirection=1",
                "bubbleWordNavDirection=-1",
                "bubbleLookupHadBubble=true",
            }
        ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_all_repo_apple_journeys_match_swift_runner_contract() -> None:
    assert module.validate_journey_dir(module.DEFAULT_JOURNEY_DIR) == []


def test_makefile_profile_journey_scopes_match_top_level_platforms() -> None:
    assert module.validate_makefile_profile_journey_scopes() == []


def test_profile_journey_scope_rejects_mismatched_platform(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    journey.write_text(
        json.dumps(
            {
                "id": "music_bed_sync",
                "name": "Music Bed",
                "description": "Music bed",
                "platforms": ["iPad", "tvOS"],
                "steps": [{"action": "login"}],
            }
        ),
        encoding="utf-8",
    )

    errors = module.validate_profile_journey_scope("iphone", journey)

    assert errors == [
        f"profile 'iphone' resolves to iPhone, but journey {journey} is scoped to iPad, tvOS"
    ]


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


def test_validator_rejects_unsupported_keyboard_key(tmp_path: Path) -> None:
    journey = tmp_path / "bad_keyboard.json"
    _write_journey(journey, [{"action": "press_keyboard_key", "key": "tab"}])

    errors = module.validate_journey(journey)

    assert any("keyboard key 'tab' is not supported" in error for error in errors)


def test_validator_allows_raw_keyboard_navigation_keys(tmp_path: Path) -> None:
    journey = tmp_path / "keyboard_navigation.json"
    _write_journey(
        journey,
        [
            {
                "action": "press_keyboard_key",
                "key": "right",
            },
            {
                "action": "press_keyboard_key",
                "key": "left",
            },
            {
                "action": "press_keyboard_key",
                "key": "return",
            },
            {
                "action": "press_keyboard_key",
                "key": "enter",
            },
        ],
    )

    assert module.validate_journey(journey) == []


def test_validator_rejects_missing_action_required_fields(tmp_path: Path) -> None:
    journey = tmp_path / "missing.json"
    _write_journey(
        journey,
        [
            {"action": "assert_value_contains", "selector": "status"},
            {"action": "assert_value_key_at_least", "selector": "status"},
            {"action": "tap"},
        ],
    )

    errors = module.validate_journey(journey)

    assert any("action 'assert_value_contains' requires text" in error for error in errors)
    assert any("action 'assert_value_key_at_least' requires min_value" in error for error in errors)
    assert any("action 'assert_value_key_at_least' requires key or text" in error for error in errors)
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


def test_validator_accepts_supported_top_level_platforms(tmp_path: Path) -> None:
    journey = tmp_path / "platforms.json"
    _write_journey(journey, [{"action": "login"}])

    assert module.validate_journey(journey) == []


def test_validator_rejects_unknown_top_level_platform(tmp_path: Path) -> None:
    journey = tmp_path / "bad_platform.json"
    payload = {
        "id": "sample",
        "name": "Sample",
        "description": "Sample journey",
        "platforms": ["watchOS"],
        "steps": [{"action": "login"}],
    }
    journey.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.validate_journey(journey)

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
    _write_music_bed_journey(journey, remove_text="readerTransportCommands=3")

    errors = module.validate_journey(journey)

    assert any("requires e2eMusicBedSyncStatus assertion 'readerTransportCommands=3'" in error for error in errors)


def test_music_bed_validator_requires_ipad_session_stability_branch(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_screenshot="music_bed_ipad_music_play_tapped")

    errors = module.validate_journey(journey)

    assert any("music_bed_ipad_music_play_tapped" in error for error in errors)


def test_music_bed_validator_requires_ipad_restored_player_guard(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_ipad_unless_visible=True)

    errors = module.validate_journey(journey)

    assert any("music_bed_ipad_player_opened" in error for error in errors)


def test_music_bed_validator_requires_ipad_auto_resume_probe(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_ipad_auto_resume=True)

    errors = module.validate_journey(journey)

    assert any("e2eMusicBedAutoResumeButton" in error for error in errors)
    assert any("music_bed_ipad_auto_resume_settled" in error for error in errors)


def test_music_bed_validator_requires_ipad_sentence_transition_probe(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_ipad_transition_probe=True)

    errors = module.validate_journey(journey)

    assert any("e2eReaderTransitionButton" in error for error in errors)
    assert any("music_bed_ipad_sentence_transition_pressed" in error for error in errors)
    assert any("e2eReaderTransitionResumeButton" in error for error in errors)
    assert any("music_bed_ipad_sentence_transition_resume_pressed" in error for error in errors)


def test_music_bed_validator_requires_ipad_space_pause_resume_probe(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_ipad_space_probe=True)

    errors = module.validate_journey(journey)

    assert any("music_bed_ipad_space_pause_pressed" in error for error in errors)
    assert any("music_bed_ipad_space_resume_pressed" in error for error in errors)
    assert any("requires step 'music_bed_ipad_space_pause_pressed'" in error for error in errors)


def test_music_bed_validator_requires_ipad_bubble_pronunciation_resume_probe(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_ipad_bubble_probe=True)

    errors = module.validate_journey(journey)

    assert any("e2eBubblePronunciationResumeButton" in error for error in errors)
    assert any("music_bed_ipad_bubble_pronunciation_resume_setup" in error for error in errors)
    assert any("music_bed_ipad_bubble_space_resume_pressed" in error for error in errors)
    assert any("requires step 'music_bed_ipad_bubble_pronunciation_resume_setup'" in error for error in errors)
    assert any("requires step 'music_bed_ipad_bubble_space_resume_pressed'" in error for error in errors)


def test_music_bed_validator_requires_ipad_bubble_keyboard_lookup_probe(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_ipad_bubble_keyboard_probe=True)

    errors = module.validate_journey(journey)

    assert any("music_bed_ipad_bubble_right_word_pressed" in error for error in errors)
    assert any("music_bed_ipad_bubble_left_word_pressed" in error for error in errors)
    assert any("music_bed_ipad_bubble_lookup_return_pressed" in error for error in errors)
    assert any("bubbleWordNavDirection=1" in error for error in errors)
    assert any("bubbleWordNavDirection=-1" in error for error in errors)
    assert any("bubbleLookupHadBubble=true" in error for error in errors)


def test_music_bed_validator_requires_guarded_remote_play_sequence(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_screenshot="music_bed_guarded_remote_play_pressed")

    errors = module.validate_journey(journey)

    assert any("music_bed_guarded_remote_play_pressed" in error for error in errors)


def test_music_bed_validator_requires_post_hold_remote_resume(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_screenshot="music_bed_remote_play_pressed")

    errors = module.validate_journey(journey)

    assert any("music_bed_remote_play_pressed" in error for error in errors)


def test_music_bed_validator_requires_short_pause_hold_before_guarded_press(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_tvos_short_pause_hold=True)

    errors = module.validate_journey(journey)

    assert any(
        "requires 100ms pause-hold wait after 'music_bed_remote_pause_observed'" in error
        for error in errors
    )


def test_music_bed_validator_requires_shell_play_pause_resume(tmp_path: Path) -> None:
    journey = tmp_path / "music_bed_sync.json"
    _write_music_bed_journey(journey, remove_screenshot="music_bed_shell_play_pause_resume_pressed")

    errors = module.validate_journey(journey)

    assert any("music_bed_shell_play_pause_resume_pressed" in error for error in errors)
