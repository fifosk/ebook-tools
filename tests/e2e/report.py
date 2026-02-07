"""E2E HTML report generator.

Pytest plugin that collects test outcomes and Playwright screenshots from
``test-results/`` and produces a standalone HTML report with embedded images.

Usage:
    pytest -m e2e --e2e-report          # → test-results/e2e-report.html
    pytest -m e2e --e2e-report=my.html  # custom path

The HTML is fully self-contained (base64-encoded images) so it can be shared
or archived as a single file.
"""

from __future__ import annotations

import base64
import html
import re
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
        const="test-results/e2e-report.html",
        default=None,
        metavar="PATH",
        help=(
            "Generate an HTML E2E report with embedded screenshots. "
            "Defaults to test-results/e2e-report.html when flag used without a value."
        ),
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

    html_content = _build_html(output_dir)
    report_file.write_text(html_content, encoding="utf-8")

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
    for d in output_dir.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            for png in sorted(d.glob("*.png")):
                return png
    return None


def _slugify_nodeid(nodeid: str) -> str:
    """Replicate pytest-playwright's node-id → directory-name slugification."""
    slug = nodeid.replace("::", "-").replace("/", "-").replace(".", "-")
    slug = re.sub(r"[^a-zA-Z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-").lower()
    return slug


def _embed_image(path: Path) -> str:
    """Return a base64 data-URI for a PNG file."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

_STATUS_STYLES = {
    "passed": ("#10b981", "#065f46", "#d1fae5"),
    "failed": ("#ef4444", "#991b1b", "#fee2e2"),
    "skipped": ("#f59e0b", "#92400e", "#fef3c7"),
}


def _build_html(output_dir: Path) -> str:
    passed = sum(1 for r in _collector.results if r["outcome"] == "passed")
    failed = sum(1 for r in _collector.results if r["outcome"] == "failed")
    skipped = sum(1 for r in _collector.results if r["outcome"] == "skipped")
    total = len(_collector.results)
    duration = sum(r["duration"] for r in _collector.results)

    start_str = _collector.start_time.strftime("%Y-%m-%d %H:%M:%S UTC") if _collector.start_time else "—"
    overall_status = "PASSED" if failed == 0 else "FAILED"
    overall_color = "#10b981" if failed == 0 else "#ef4444"

    test_rows = []
    for r in _collector.results:
        color, dark, bg = _STATUS_STYLES.get(r["outcome"], ("#888", "#444", "#eee"))
        badge = f'<span class="badge" style="background:{bg};color:{dark}">{r["outcome"].upper()}</span>'

        # Short test name from nodeid
        short_name = r["nodeid"].split("::")[-1]
        # Class name if present
        parts = r["nodeid"].split("::")
        class_name = parts[-2] if len(parts) >= 3 else ""

        screenshot_html = ""
        img_path = _find_screenshot(output_dir, r["nodeid"])
        if img_path:
            data_uri = _embed_image(img_path)
            screenshot_html = f'<img src="{data_uri}" alt="Screenshot for {html.escape(short_name)}" class="screenshot" loading="lazy">'

        error_html = ""
        if r["longrepr"]:
            error_html = f'<pre class="error">{html.escape(r["longrepr"])}</pre>'

        test_rows.append(f"""
        <div class="test-card {r['outcome']}">
            <div class="test-header">
                {badge}
                <div class="test-info">
                    <span class="test-name">{html.escape(short_name)}</span>
                    {"<span class='test-class'>" + html.escape(class_name) + "</span>" if class_name else ""}
                </div>
                <span class="test-duration">{r['duration']}s</span>
            </div>
            {error_html}
            {screenshot_html}
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>E2E Test Report — {start_str}</title>
<style>
  :root {{ --bg: #0f172a; --card: #1e293b; --border: #334155; --text: #e2e8f0; --muted: #94a3b8; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); padding: 2rem; line-height: 1.6; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; font-weight: 600; margin-bottom: 0.25rem; }}
  .subtitle {{ color: var(--muted); font-size: 0.875rem; margin-bottom: 1.5rem; }}
  .summary {{ display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }}
  .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
           padding: 1rem 1.25rem; min-width: 120px; }}
  .stat-value {{ font-size: 1.5rem; font-weight: 700; }}
  .stat-label {{ color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  .test-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
               padding: 1rem 1.25rem; margin-bottom: 1rem; }}
  .test-card.failed {{ border-left: 3px solid #ef4444; }}
  .test-card.passed {{ border-left: 3px solid #10b981; }}
  .test-card.skipped {{ border-left: 3px solid #f59e0b; }}
  .test-header {{ display: flex; align-items: center; gap: 0.75rem; }}
  .badge {{ font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 4px;
            text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; }}
  .test-info {{ flex: 1; }}
  .test-name {{ font-weight: 600; font-size: 0.95rem; }}
  .test-class {{ display: block; color: var(--muted); font-size: 0.8rem; }}
  .test-duration {{ color: var(--muted); font-size: 0.8rem; white-space: nowrap; }}
  .screenshot {{ max-width: 100%; border-radius: 6px; margin-top: 0.75rem; border: 1px solid var(--border);
                 cursor: pointer; transition: transform 0.2s; }}
  .screenshot:hover {{ transform: scale(1.01); }}
  .error {{ background: #1a0000; color: #fca5a5; padding: 0.75rem; border-radius: 6px; margin-top: 0.75rem;
            font-size: 0.8rem; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border);
           color: var(--muted); font-size: 0.75rem; text-align: center; }}
  /* Lightbox */
  .lightbox {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.9); z-index: 1000;
               align-items: center; justify-content: center; cursor: zoom-out; }}
  .lightbox.active {{ display: flex; }}
  .lightbox img {{ max-width: 95vw; max-height: 95vh; border-radius: 8px; }}
</style>
</head>
<body>
<div class="container">
  <h1>E2E Test Report</h1>
  <div class="subtitle">{start_str}</div>
  <div class="summary">
    <div class="stat">
      <div class="stat-value" style="color:{overall_color}">{overall_status}</div>
      <div class="stat-label">Result</div>
    </div>
    <div class="stat">
      <div class="stat-value">{total}</div>
      <div class="stat-label">Tests</div>
    </div>
    <div class="stat">
      <div class="stat-value" style="color:#10b981">{passed}</div>
      <div class="stat-label">Passed</div>
    </div>
    {"<div class='stat'><div class='stat-value' style='color:#ef4444'>" + str(failed) + "</div><div class='stat-label'>Failed</div></div>" if failed else ""}
    {"<div class='stat'><div class='stat-value' style='color:#f59e0b'>" + str(skipped) + "</div><div class='stat-label'>Skipped</div></div>" if skipped else ""}
    <div class="stat">
      <div class="stat-value">{duration:.1f}s</div>
      <div class="stat-label">Duration</div>
    </div>
  </div>
  {"".join(test_rows)}
</div>
<div class="lightbox" id="lightbox" onclick="this.classList.remove('active')">
  <img id="lightbox-img" src="" alt="Enlarged screenshot">
</div>
<footer>Generated by ebook-tools E2E test suite</footer>
<script>
  document.querySelectorAll('.screenshot').forEach(img => {{
    img.addEventListener('click', () => {{
      document.getElementById('lightbox-img').src = img.src;
      document.getElementById('lightbox').classList.add('active');
    }});
  }});
</script>
</body>
</html>"""
