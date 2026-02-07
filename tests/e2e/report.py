"""E2E Markdown report generator.

Pytest plugin that collects test outcomes and Playwright screenshots from
``test-results/`` and produces a GitHub-flavored Markdown report.

Usage:
    pytest -m e2e --e2e-report          # → test-results/e2e-report.md
    pytest -m e2e --e2e-report=my.md    # custom path

Screenshots are copied into ``test-results/screenshots/`` alongside the report
so that relative image links render on GitHub.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# CLI option
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("e2e", "Browser E2E test options")
    group.addoption(
        "--e2e-report",
        nargs="?",
        const="test-results/e2e-report.md",
        default=None,
        metavar="PATH",
        help=(
            "Generate a Markdown E2E report with screenshots. "
            "Defaults to test-results/e2e-report.md when flag used without a value."
        ),
    )
    group.addoption(
        "--e2e-report-title",
        default="E2E Test Report",
        help="Title for the generated Markdown report (default: 'E2E Test Report').",
    )


# ---------------------------------------------------------------------------
# Result collector
# ---------------------------------------------------------------------------

class _ReportCollector:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None


_collector = _ReportCollector()


def pytest_sessionstart(session: pytest.Session) -> None:
    if session.config.getoption("--e2e-report", default=None):
        _collector.start_time = datetime.now(timezone.utc)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Any:
    outcome = yield
    report = outcome.get_result()

    # Only capture the "call" phase (not setup/teardown)
    if report.when != "call":
        return

    if not item.config.getoption("--e2e-report", default=None):
        return

    # Only record tests with the e2e marker
    if not any(m.name == "e2e" for m in item.iter_markers()):
        return

    _collector.results.append({
        "nodeid": report.nodeid,
        "outcome": report.outcome,
        "duration": round(report.duration, 2),
        "longrepr": str(report.longrepr) if report.longrepr else None,
    })


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    report_path = session.config.getoption("--e2e-report", default=None)
    if not report_path or not _collector.results:
        return

    _collector.end_time = datetime.now(timezone.utc)

    output_dir = Path(session.config.getoption("--output", default="test-results"))
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    # Screenshots go into a sibling directory next to the report
    screenshot_dir = report_file.parent / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    title = session.config.getoption("--e2e-report-title", default="E2E Test Report")
    md_content = _build_markdown(output_dir, screenshot_dir, report_file.parent, title)
    report_file.write_text(md_content, encoding="utf-8")

    # Use terminalwriter for colored output
    tw = session.config.get_terminal_writer()
    tw.sep("-", "E2E report")
    tw.line(f"Report saved to: {report_file.resolve()}", green=True)


# ---------------------------------------------------------------------------
# Screenshot discovery
# ---------------------------------------------------------------------------

def _find_screenshot(output_dir: Path, nodeid: str) -> Path | None:
    """Find the Playwright screenshot for a given test nodeid.

    pytest-playwright slugifies the nodeid into a directory name under
    output_dir.  We replicate that logic here.
    """
    slug = _slugify_nodeid(nodeid)
    candidates = [
        output_dir / slug / "test-finished-1.png",
        output_dir / slug / "test-failed-1.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: search for any PNG in a directory that starts with a prefix
    prefix = slug[:60]
    if not output_dir.exists():
        return None
    for d in output_dir.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            for png in sorted(d.glob("*.png")):
                return png
    return None


def _slugify_nodeid(nodeid: str) -> str:
    """Replicate pytest-playwright's node-id -> directory-name slugification."""
    slug = nodeid.replace("::", "-").replace("/", "-").replace(".", "-")
    slug = re.sub(r"[^a-zA-Z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-").lower()
    return slug


# ---------------------------------------------------------------------------
# Markdown builder
# ---------------------------------------------------------------------------

_STATUS_EMOJI = {
    "passed": "PASSED",
    "failed": "FAILED",
    "skipped": "SKIPPED",
}


def _build_markdown(
    output_dir: Path,
    screenshot_dir: Path,
    report_parent: Path,
    title: str = "E2E Test Report",
) -> str:
    passed = sum(1 for r in _collector.results if r["outcome"] == "passed")
    failed = sum(1 for r in _collector.results if r["outcome"] == "failed")
    skipped = sum(1 for r in _collector.results if r["outcome"] == "skipped")
    total = len(_collector.results)
    duration = sum(r["duration"] for r in _collector.results)

    start_str = (
        _collector.start_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        if _collector.start_time
        else "—"
    )
    overall_status = "PASSED" if failed == 0 else "FAILED"

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> **{start_str}**")
    lines.append("")

    # Summary table
    lines.append("| Result | Tests | Passed | Failed | Skipped | Duration |")
    lines.append("|--------|-------|--------|--------|---------|----------|")
    lines.append(
        f"| **{overall_status}** | {total} | {passed} | {failed} | {skipped} | {duration:.1f}s |"
    )
    lines.append("")

    # Individual tests
    lines.append("## Test Results")
    lines.append("")

    for r in _collector.results:
        status = _STATUS_EMOJI.get(r["outcome"], r["outcome"].upper())
        short_name = r["nodeid"].split("::")[-1]
        parts = r["nodeid"].split("::")
        class_name = parts[-2] if len(parts) >= 3 else ""

        header = f"### `{status}` {short_name}"
        if class_name:
            header += f" ({class_name})"
        header += f" — {r['duration']}s"
        lines.append(header)
        lines.append("")

        # Error details
        if r["longrepr"]:
            lines.append("<details>")
            lines.append("<summary>Error details</summary>")
            lines.append("")
            lines.append("```")
            lines.append(r["longrepr"])
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        # Screenshot — copy to screenshot_dir, link with relative path
        img_path = _find_screenshot(output_dir, r["nodeid"])
        if img_path:
            slug = _slugify_nodeid(r["nodeid"])
            dest = screenshot_dir / f"{slug}.png"
            shutil.copy2(img_path, dest)
            rel = dest.relative_to(report_parent)
            lines.append(f"![{short_name}]({rel})")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Generated by ebook-tools E2E test suite*")
    lines.append("")

    return "\n".join(lines)
