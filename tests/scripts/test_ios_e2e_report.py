from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ios_e2e_report.py"
SPEC = importlib.util.spec_from_file_location("ios_e2e_report", SCRIPT_PATH)
assert SPEC is not None
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def _test_data(result: str = "Passed") -> dict:
    return {
        "testNodes": [
            {
                "nodeType": "Test Suite",
                "name": "JourneyTests",
                "children": [
                    {
                        "nodeType": "Test Case",
                        "name": "testJourney",
                        "nodeIdentifier": "JourneyTests/testJourney",
                        "result": result,
                        "durationInSeconds": 1.25,
                    }
                ],
            }
        ]
    }


def test_summarize_test_results_counts_skipped_cases() -> None:
    data = {
        "testNodes": [
            {
                "nodeType": "Test Suite",
                "children": [
                    {"nodeType": "Test Case", "result": "Passed"},
                    {"nodeType": "Test Case", "result": "Failed"},
                    {"nodeType": "Test Case", "result": "Skipped"},
                ],
            }
        ]
    }

    assert module.summarize_test_results(data) == {
        "total": 3,
        "passed": 1,
        "failed": 1,
        "skipped": 1,
    }


def test_main_fails_on_skipped_xcresult_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    xcresult = tmp_path / "ipad-e2e.xcresult"
    xcresult.mkdir()
    output = tmp_path / "report.md"

    monkeypatch.setattr(module, "get_test_results", lambda _path: _test_data("Skipped"))
    monkeypatch.setattr(module, "export_attachments", lambda _path, _out: [])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ios_e2e_report.py",
            "--xcresult",
            str(xcresult),
            "--output",
            str(output),
            "--fail-on-skipped",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert exc.value.code == 2
    assert "1 skipped test(s) found" in capsys.readouterr().err
    assert output.exists()


def test_main_allows_skipped_xcresult_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xcresult = tmp_path / "ipad-e2e.xcresult"
    xcresult.mkdir()
    output = tmp_path / "report.md"

    monkeypatch.setattr(module, "get_test_results", lambda _path: _test_data("Skipped"))
    monkeypatch.setattr(module, "export_attachments", lambda _path, _out: [])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ios_e2e_report.py",
            "--xcresult",
            str(xcresult),
            "--output",
            str(output),
        ],
    )

    module.main()

    assert output.exists()
