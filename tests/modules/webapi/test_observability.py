"""Observability E2E tests: metrics exporter → Prometheus exposition → dashboard coverage.

Verifies the full pipeline from metric definition to Grafana dashboard consumption:
  Layer 1: Every custom ebook_tools_* metric is present in /metrics with correct type
  Layer 2: Labelled metrics have expected label names
  Layer 3: Every PromQL expr in dashboard JSONs references an existing metric
  Layer 4: HTTP auto-instrumentation generates metrics; /metrics excluded
  Layer 5: Auth counter increments on failed login
  Layer 6: Dashboard JSON files are structurally valid

Run with:  pytest -m observability -v
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from modules.webapi.application import create_app

pytestmark = pytest.mark.observability

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DASHBOARD_DIR = Path("monitoring/grafana/dashboards")


@pytest.fixture(scope="module")
def metrics_response():
    """GET /metrics from a TestClient, return the raw Response."""
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/metrics")
    return resp


@pytest.fixture(scope="module")
def metrics_text(metrics_response):
    """Raw Prometheus text exposition body."""
    assert metrics_response.status_code == 200
    assert "text/plain" in metrics_response.headers.get("content-type", "")
    return metrics_response.text


@pytest.fixture(scope="module")
def metric_families(metrics_text):
    """Parse Prometheus text into ``{name: MetricFamily}`` dict."""
    return {f.name: f for f in text_string_to_metric_families(metrics_text)}


# ---------------------------------------------------------------------------
# Layer 1 — Metric presence & type
# ---------------------------------------------------------------------------

_EXPECTED_METRICS = [
    # (metric name as defined in metrics.py, prometheus type string)
    ("ebook_tools_up", "gauge"),
    ("ebook_tools_health_status", "gauge"),
    ("ebook_tools_jobs_total", "gauge"),
    ("ebook_tools_jobs_active", "gauge"),
    ("ebook_tools_jobs_queue_depth", "gauge"),
    ("ebook_tools_job_duration_seconds", "histogram"),
    ("ebook_tools_jobs_backpressure_rejections_total", "counter"),
    ("ebook_tools_jobs_backpressure_delays_total", "counter"),
    ("ebook_tools_library_items_total", "gauge"),
    ("ebook_tools_users_total", "gauge"),
    ("ebook_tools_sessions_active", "gauge"),
    ("ebook_tools_auth_attempts_total", "counter"),
    ("ebook_tools_pipeline_stage_duration_seconds", "histogram"),
    ("ebook_tools_worker_pool_utilization", "gauge"),
    ("ebook_tools_errors_total", "counter"),
    ("ebook_tools_job_failures_total", "counter"),
    ("ebook_tools_generated_playtime_seconds", "gauge"),
    ("ebook_tools_listened_playtime_seconds", "gauge"),
    ("ebook_tools_playback_sessions_active", "gauge"),
]


@pytest.mark.parametrize(
    "name,expected_type",
    _EXPECTED_METRICS,
    ids=[m[0] for m in _EXPECTED_METRICS],
)
def test_metric_present_and_typed(metric_families, name, expected_type):
    """Every custom ebook_tools_* metric exists in /metrics with correct type."""
    # prometheus_client parser strips the _total suffix for counter families
    lookup = name
    if expected_type == "counter":
        lookup = re.sub(r"_total$", "", name)
    assert lookup in metric_families, (
        f"Metric {name!r} not found in /metrics. "
        f"Available: {sorted(k for k in metric_families if k.startswith('ebook_tools'))}"
    )
    assert metric_families[lookup].type == expected_type, (
        f"Metric {name!r} has type {metric_families[lookup].type!r}, expected {expected_type!r}"
    )


# ---------------------------------------------------------------------------
# Layer 2 — Label cardinality
# ---------------------------------------------------------------------------

_EXPECTED_LABELS = [
    ("ebook_tools_jobs_total", {"status"}),
    ("ebook_tools_users_total", {"role"}),
    ("ebook_tools_library_items_total", {"item_type"}),
    ("ebook_tools_auth_attempts", {"method", "result"}),
    ("ebook_tools_pipeline_stage_duration_seconds", {"stage"}),
    ("ebook_tools_generated_playtime_seconds", {"language", "job_type", "track_kind"}),
    ("ebook_tools_listened_playtime_seconds", {"language", "track_kind"}),
]


@pytest.mark.parametrize(
    "name,expected_labels",
    _EXPECTED_LABELS,
    ids=[m[0] for m in _EXPECTED_LABELS],
)
def test_metric_labels(metric_families, name, expected_labels):
    """Labelled metrics expose the expected label names."""
    assert name in metric_families, f"Metric {name!r} not found"
    family = metric_families[name]
    if not family.samples:
        pytest.skip(f"No samples yet for {name} (gauge not collected)")
    for sample in family.samples:
        assert expected_labels.issubset(set(sample.labels.keys())), (
            f"Sample {sample.name} labels {set(sample.labels.keys())} "
            f"missing {expected_labels - set(sample.labels.keys())}"
        )


# ---------------------------------------------------------------------------
# Layer 3 — Dashboard PromQL coverage
# ---------------------------------------------------------------------------

# Metrics served by postgres-exporter or its custom queries (not in /metrics).
KNOWN_EXTERNAL_METRICS = {
    # Built-in Prometheus metrics
    "up",
    # Built-in postgres-exporter metrics
    "pg_up",
    "pg_stat_activity_count",
    "pg_settings_max_connections",
    "pg_stat_database_blks_hit",
    "pg_stat_database_blks_read",
    "pg_stat_database_xact_commit",
    "pg_stat_database_xact_rollback",
    "pg_stat_database_temp_bytes",
    "pg_total_relation_size_bytes",
    "pg_stat_user_tables_n_dead_tup",
    "pg_database_size_bytes",
    # Custom postgres-exporter queries (monitoring/postgres-exporter/queries.yaml)
    # Note: postgres_exporter appends the column name as suffix, so the
    # queries.yaml "count" column becomes _count in Prometheus.
    "ebook_tools_active_sessions",
    "ebook_tools_active_sessions_count",
    "ebook_tools_library_items",
    "ebook_tools_bookmarks",
    "ebook_tools_bookmarks_count",
    "ebook_tools_resume_positions",
    "ebook_tools_resume_positions_count",
    "ebook_tools_users",
    # Media analytics (monitoring/postgres-exporter/queries.yaml)
    "ebook_tools_generated_playtime",
    "ebook_tools_generated_playtime_total_seconds",
    "ebook_tools_generated_playtime_total_sentences",
    "ebook_tools_generated_playtime_job_count",
    "ebook_tools_listened_playtime",
    "ebook_tools_listened_playtime_total_seconds",
    "ebook_tools_listened_playtime_session_count",
    "ebook_tools_playback_active",
    "ebook_tools_playback_active_count",
}

# PromQL function names and keywords that aren't metric names.
_PROMQL_KEYWORDS = frozenset({
    "sum", "rate", "histogram_quantile", "avg", "min", "max", "count",
    "increase", "irate", "delta", "idelta", "abs", "ceil", "floor",
    "round", "clamp_min", "clamp_max", "sort", "sort_desc", "topk",
    "bottomk", "time", "vector", "scalar", "label_replace",
    "label_join", "changes", "resets", "deriv", "predict_linear",
    # PromQL aggregation keywords and operators
    "by", "without", "on", "ignoring", "group_left", "group_right", "or", "and", "unless",
    # Common label names appearing in filter expressions
    "le", "datname", "relname", "status", "state", "handler", "item_type",
    "method", "result", "stage", "error_type", "endpoint", "job_type",
    "language", "track_kind",
    "ebook_tools", "job", "deployment",
})


def _extract_metric_names_from_expr(expr: str) -> set[str]:
    """Extract likely metric names from a PromQL expression."""
    # Strip quoted strings first (removes table names in relname=~"..." filters)
    stripped = re.sub(r'"[^"]*"', "", expr)
    # Match sequences of lowercase alphanumerics and underscores starting with a letter
    tokens = set(re.findall(r"\b([a-z][a-z0-9_]+)\b", stripped))
    return tokens - _PROMQL_KEYWORDS


def test_dashboard_metrics_covered(metric_families):
    """Every metric referenced in dashboard PromQL exists in the backend
    /metrics output or is a known external (postgres-exporter) metric."""
    assert DASHBOARD_DIR.is_dir(), f"Dashboard dir not found: {DASHBOARD_DIR}"

    missing: list[str] = []
    for json_file in sorted(DASHBOARD_DIR.glob("*.json")):
        dashboard = json.loads(json_file.read_text())
        for panel in dashboard.get("panels", []):
            for target in panel.get("targets", []):
                expr = target.get("expr", "")
                if not expr:
                    continue
                for name in _extract_metric_names_from_expr(expr):
                    # Strip histogram/counter suffixes for family lookup
                    base = re.sub(r"_(bucket|count|sum|total|created)$", "", name)
                    if (
                        name not in metric_families
                        and base not in metric_families
                        and name not in KNOWN_EXTERNAL_METRICS
                        and base not in KNOWN_EXTERNAL_METRICS
                    ):
                        missing.append(
                            f"  {json_file.name}: {name} "
                            f"(from: {expr[:80]}{'…' if len(expr) > 80 else ''})"
                        )

    assert not missing, (
        f"Dashboard metrics not found in /metrics or KNOWN_EXTERNAL_METRICS:\n"
        + "\n".join(missing)
    )


# ---------------------------------------------------------------------------
# Layer 4 — HTTP auto-instrumentation
# ---------------------------------------------------------------------------


def test_http_request_metrics_after_traffic():
    """After hitting API endpoints, http_request_duration_seconds appears."""
    app = create_app()
    with TestClient(app) as client:
        # Generate traffic on non-excluded endpoints
        # (/_health and /metrics are excluded from instrumentation)
        client.get(
            "/api/pipelines/defaults",
            headers={"X-User-Id": "tester", "X-User-Role": "admin"},
        )
        resp = client.get("/metrics")

    families = {f.name: f for f in text_string_to_metric_families(resp.text)}
    # The instrumentator produces http_request_duration_seconds (no ebook_tools_ prefix).
    # Also check for http_requests_total which is the counter.
    has_duration = "http_request_duration_seconds" in families
    has_total = "http_requests" in families
    assert has_duration or has_total, (
        "No HTTP instrumentation metrics found after traffic. "
        f"Available HTTP metrics: {sorted(k for k in families if 'http' in k)}"
    )


def test_metrics_endpoint_excluded_from_instrumentation():
    """The /metrics endpoint itself should not appear in http_request_* handler labels."""
    app = create_app()
    with TestClient(app) as client:
        # Only hit /metrics (should be excluded from instrumentation)
        client.get("/metrics")
        resp = client.get("/metrics")

    families = {f.name: f for f in text_string_to_metric_families(resp.text)}
    if "http_request_duration_seconds" in families:
        handlers = {
            s.labels.get("handler", "")
            for s in families["http_request_duration_seconds"].samples
        }
        assert "/metrics" not in handlers, (
            "/metrics should be excluded from HTTP instrumentation"
        )


# ---------------------------------------------------------------------------
# Layer 5 — Auth counter instrumentation
# ---------------------------------------------------------------------------


def test_auth_failure_increments_counter():
    """A failed login attempt increments ebook_tools_auth_attempts_total."""
    app = create_app()
    with TestClient(app) as client:
        client.post(
            "/api/auth/login",
            json={"username": "nonexistent_user", "password": "wrong_password"},
        )
        resp = client.get("/metrics")

    families = {f.name: f for f in text_string_to_metric_families(resp.text)}
    auth = families.get("ebook_tools_auth_attempts")
    assert auth is not None, "ebook_tools_auth_attempts metric not found"

    failure_samples = [
        s
        for s in auth.samples
        if s.labels.get("result") == "failure" and s.name.endswith("_total")
    ]
    assert failure_samples, "No failure samples found in auth_attempts"
    assert any(s.value >= 1.0 for s in failure_samples), (
        f"Expected auth failure count >= 1, got: "
        f"{[(s.labels, s.value) for s in failure_samples]}"
    )


# ---------------------------------------------------------------------------
# Layer 6 — Dashboard JSON structure
# ---------------------------------------------------------------------------


def test_dashboard_json_structure():
    """All dashboard JSON files are well-formed with required Grafana fields."""
    assert DASHBOARD_DIR.is_dir(), f"Dashboard dir not found: {DASHBOARD_DIR}"

    dashboards = sorted(DASHBOARD_DIR.glob("*.json"))
    assert len(dashboards) >= 4, (
        f"Expected at least 4 dashboard files, found {len(dashboards)}"
    )

    for json_file in dashboards:
        dashboard = json.loads(json_file.read_text())
        fname = json_file.name

        # Top-level required fields
        assert "uid" in dashboard, f"{fname} missing 'uid'"
        assert "title" in dashboard, f"{fname} missing 'title'"
        assert "panels" in dashboard, f"{fname} missing 'panels'"
        assert isinstance(dashboard["panels"], list), f"{fname} 'panels' is not a list"

        for panel in dashboard["panels"]:
            assert "title" in panel, f"{fname} panel missing 'title'"

            # Row-type panels are just collapsible section headers
            if panel.get("type") == "row":
                continue

            # Every non-row panel should have targets with expr
            targets = panel.get("targets", [])
            assert targets, (
                f"{fname} panel '{panel['title']}' has no targets"
            )
            for t in targets:
                assert "expr" in t, (
                    f"{fname} panel '{panel['title']}' target missing 'expr'"
                )

            # Validate datasource uid points to our provisioned datasource
            ds = panel.get("datasource", {})
            if isinstance(ds, dict) and ds.get("uid"):
                assert ds["uid"] == "prometheus", (
                    f"{fname} panel '{panel['title']}' references datasource "
                    f"uid '{ds['uid']}' instead of 'prometheus'"
                )
