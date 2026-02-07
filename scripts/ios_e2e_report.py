#!/usr/bin/env python3
"""
Generate a Markdown E2E report from an Xcode .xcresult bundle.

Extracts test results and screenshots using ``xcresulttool``, then produces
a report in the same format as the Playwright ``tests/e2e/report.py``.

Usage:
    python scripts/ios_e2e_report.py \\
        --xcresult test-results/ios-e2e.xcresult \\
        --output   test-results/ios-e2e-report.md
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

XCRESULTTOOL = "/Applications/Xcode.app/Contents/Developer/usr/bin/xcresulttool"


# ---------------------------------------------------------------------------
# xcresulttool wrappers
# ---------------------------------------------------------------------------

def _run_xcresulttool(*args: str) -> str:
    """Run xcresulttool and return stdout."""
    cmd = [XCRESULTTOOL, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"xcresulttool error: {result.stderr}", file=sys.stderr)
    return result.stdout


def get_test_results(xcresult: Path) -> dict:
    """Parse the test-results JSON from the xcresult bundle."""
    raw = _run_xcresulttool("get", "test-results", "tests", "--path", str(xcresult))
    if not raw.strip():
        return {}
    return json.loads(raw)


def export_attachments(xcresult: Path, output_dir: Path) -> list[dict]:
    """Export all attachments and return the manifest entries."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _run_xcresulttool(
        "export", "attachments",
        "--path", str(xcresult),
        "--output-path", str(output_dir),
    )
    manifest = output_dir / "manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text())
    return []


# ---------------------------------------------------------------------------
# Test-node tree flattening
# ---------------------------------------------------------------------------

def _flatten_test_nodes(nodes: list[dict], depth: int = 0) -> list[dict]:
    """Walk the test-node tree and collect Test Case leaf nodes."""
    results: list[dict] = []
    for node in nodes:
        node_type = node.get("nodeType", "")
        if node_type == "Test Case":
            results.append(node)
        children = node.get("children", [])
        if children:
            results.extend(_flatten_test_nodes(children, depth + 1))
    return results


def _find_suite_name(nodes: list[dict], target_id: str) -> str:
    """Walk tree to find the Test Suite parent of a given test case."""
    for node in nodes:
        node_type = node.get("nodeType", "")
        children = node.get("children", [])
        if node_type == "Test Suite":
            for child in children:
                if child.get("nodeIdentifier") == target_id:
                    return node.get("name", "")
        result = _find_suite_name(children, target_id)
        if result:
            return result
    return ""


# ---------------------------------------------------------------------------
# Screenshot matching
# ---------------------------------------------------------------------------

def _build_attachment_map(
    manifest: list[dict],
) -> dict[str, list[str]]:
    """Map testIdentifier → list of exported file names."""
    result: dict[str, list[str]] = {}
    for entry in manifest:
        test_id = entry.get("testIdentifier", "")
        attachments = entry.get("attachments", [])
        # attachments can be a single dict or a list
        if isinstance(attachments, dict):
            attachments = [attachments]
        files = []
        for att in attachments:
            fname = att.get("exportedFileName", "")
            if fname:
                files.append(fname)
        if files:
            result[test_id] = files
    return result


def _slugify(name: str) -> str:
    """Convert a test identifier to a filesystem-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return slug


# ---------------------------------------------------------------------------
# Markdown builder
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    "Passed": "PASSED",
    "Failed": "FAILED",
    "Skipped": "SKIPPED",
    "Expected Failure": "XFAIL",
}


def build_markdown(
    test_data: dict,
    manifest: list[dict],
    attachments_dir: Path,
    screenshot_dir: Path,
    report_parent: Path,
) -> str:
    """Generate the Markdown report string."""
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    all_nodes = test_data.get("testNodes", [])
    test_cases = _flatten_test_nodes(all_nodes)
    attachment_map = _build_attachment_map(manifest)

    # Device info
    devices = test_data.get("devices", [])
    device_str = ""
    if devices:
        d = devices[0]
        device_str = f"{d.get('deviceName', '')} ({d.get('platform', 'iOS')} {d.get('osVersion', '')})"

    # Counts
    passed = sum(1 for t in test_cases if t.get("result") == "Passed")
    failed = sum(1 for t in test_cases if t.get("result") == "Failed")
    skipped = sum(1 for t in test_cases if t.get("result") == "Skipped")
    total = len(test_cases)
    duration = sum(t.get("durationInSeconds", 0) for t in test_cases)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    overall = "PASSED" if failed == 0 else "FAILED"

    lines: list[str] = []
    lines.append("# iOS E2E Test Report")
    lines.append("")
    lines.append(f"> **{now_str}**" + (f" — {device_str}" if device_str else ""))
    lines.append("")

    # Summary table
    lines.append("| Result | Tests | Passed | Failed | Skipped | Duration |")
    lines.append("|--------|-------|--------|--------|---------|----------|")
    lines.append(
        f"| **{overall}** | {total} | {passed} | {failed} | {skipped} | {duration:.1f}s |"
    )
    lines.append("")

    # Individual tests
    lines.append("## Test Results")
    lines.append("")

    for tc in test_cases:
        name = tc.get("name", "unknown")
        result = tc.get("result", "unknown")
        dur = tc.get("durationInSeconds", 0)
        status = _STATUS_MAP.get(result, result.upper())
        node_id = tc.get("nodeIdentifier", "")

        # Find parent suite name
        suite = _find_suite_name(all_nodes, node_id)

        header = f"### `{status}` {name}"
        if suite:
            header += f" ({suite})"
        header += f" — {dur:.2f}s"
        lines.append(header)
        lines.append("")

        # Error details from children
        failure_msgs = []
        for child in tc.get("children", []):
            if child.get("nodeType") == "Failure Message":
                failure_msgs.append(child.get("name", ""))
        if failure_msgs:
            lines.append("<details>")
            lines.append("<summary>Error details</summary>")
            lines.append("")
            lines.append("```")
            lines.append("\n".join(failure_msgs))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        # Screenshots — find from attachment map
        att_files = attachment_map.get(node_id, [])
        for att_file in att_files:
            src = attachments_dir / att_file
            if src.exists() and src.suffix.lower() == ".png":
                dest_name = f"ios-{_slugify(node_id)}-{_slugify(att_file)}.png"
                dest = screenshot_dir / dest_name
                shutil.copy2(src, dest)
                rel = dest.relative_to(report_parent)
                lines.append(f"![{name}]({rel})")
                lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Generated by ebook-tools iOS E2E test suite*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Markdown E2E report from an .xcresult bundle."
    )
    parser.add_argument(
        "--xcresult", type=Path, required=True,
        help="Path to the .xcresult bundle",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("test-results/ios-e2e-report.md"),
        help="Output Markdown report path",
    )
    args = parser.parse_args()

    if not args.xcresult.exists():
        print(f"ERROR: {args.xcresult} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Reading: {args.xcresult}")

    # 1. Get test results
    test_data = get_test_results(args.xcresult)
    if not test_data:
        print("No test results found in xcresult bundle.", file=sys.stderr)
        sys.exit(1)

    # 2. Export attachments
    attachments_dir = args.xcresult.parent / "ios-e2e-attachments"
    manifest = export_attachments(args.xcresult, attachments_dir)

    # 3. Build report
    report_path = args.output
    report_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir = report_path.parent / "screenshots"

    md = build_markdown(
        test_data, manifest, attachments_dir, screenshot_dir, report_path.parent
    )
    report_path.write_text(md, encoding="utf-8")

    print(f"Report: {report_path.resolve()}")

    # Count
    test_cases = _flatten_test_nodes(test_data.get("testNodes", []))
    passed = sum(1 for t in test_cases if t.get("result") == "Passed")
    failed = sum(1 for t in test_cases if t.get("result") == "Failed")
    print(f"Tests:  {len(test_cases)} total, {passed} passed, {failed} failed")


if __name__ == "__main__":
    main()
