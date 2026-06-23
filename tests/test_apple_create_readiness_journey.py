from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_READINESS_JOURNEY = ROOT / "tests" / "e2e" / "journeys" / "create_readiness.json"
JOURNEY_RUNNER = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReaderUITests"
    / "JourneyRunner.swift"
)


def test_create_readiness_journey_checks_runtime_create_contract() -> None:
    journey = json.loads(CREATE_READINESS_JOURNEY.read_text(encoding="utf-8"))
    steps = journey["steps"]

    settings_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionSettingsButton"
    )
    create_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("selector") == "browseSectionCreateButton"
    )
    runtime_steps = steps[settings_index:create_index]

    assert any(step.get("selector") == "settingsCreateContractRow" for step in runtime_steps)
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/books/options",
        "timeout": 20,
    } in runtime_steps
    assert {
        "action": "assert_value_contains",
        "selector": "settingsCreateContractRow",
        "text": "/api/books/jobs",
        "timeout": 20,
    } in runtime_steps


def test_journey_runner_supports_value_contains_assertion() -> None:
    source = JOURNEY_RUNNER.read_text(encoding="utf-8")

    assert 'case "assert_value_contains":' in source
    assert "private func doAssertValueContains(_ step: JourneyStep)" in source
    assert "localizedCaseInsensitiveContains(expectedText)" in source
