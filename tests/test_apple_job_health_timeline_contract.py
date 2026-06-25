from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOB_STATUS_HELPERS = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Utilities"
    / "PipelineJobStatus+Helpers.swift"
)
JOB_ROW_PRESENTATION = (
    ROOT
    / "ios"
    / "InteractiveReader"
    / "InteractiveReader"
    / "Features"
    / "Jobs"
    / "JobRowView+Presentation.swift"
)
PARITY_PLAN = ROOT / "docs" / "plans" / "cross-surface-parity-and-optimization.md"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_apple_jobs_expose_latest_stage_elapsed_and_eta_health_label() -> None:
    source = _source(JOB_STATUS_HELPERS)

    health_label = re.search(
        r"var healthTimelineLabel: String\? \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )
    display_stage = re.search(
        r"var displayStageLabel: String\? \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )

    assert health_label
    assert display_stage
    assert "guard isActiveForDisplay, let event = latestEvent else { return nil }" in health_label.group("body")
    assert "event.displayStageLabel" in health_label.group("body")
    assert 'parts.append("elapsed \\(elapsed)")' in health_label.group("body")
    assert 'parts.append("ETA \\(etaLabel)")' in health_label.group("body")
    assert "formatRuntimeDuration(event.snapshot.elapsed)" in health_label.group("body")
    assert "formatRuntimeDuration(eta)" in health_label.group("body")
    assert 'replacingOccurrences(of: "_", with: " ")' in display_stage.group("body")
    assert 'let acronyms: Set<String> = ["api", "ass", "epub", "html", "llm", "nas", "pdf", "tts"]' in source


def test_apple_job_rows_append_health_label_to_progress() -> None:
    source = _source(JOB_ROW_PRESENTATION)

    progress_label = re.search(
        r"var progressLabel: String\? \{(?P<body>.*?)\n    \}",
        source,
        re.DOTALL,
    )

    assert progress_label
    body = progress_label.group("body")
    assert "job.healthTimelineLabel" in body
    assert '"Progress: preparing · \\(healthTimelineLabel)"' in body
    assert 'let healthSuffix = job.healthTimelineLabel.map { " · \\($0)" } ?? ""' in body
    assert '"Progress \\(snapshot.completed)/\\(total) · \\(percent)%\\(healthSuffix)"' in body
    assert '"Progress \\(snapshot.completed)\\(healthSuffix)"' in body


def test_parity_plan_mentions_apple_job_health_rows() -> None:
    source = _source(PARITY_PLAN)

    assert "Job health timeline: show backend stage durations and slow phases in Web and iPad. Status:" in source
    assert "Apple Jobs rows now surface the latest backend stage with elapsed runtime" in source
    assert "Web job details now show the same compact active-job" in source
